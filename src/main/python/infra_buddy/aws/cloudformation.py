import json
from collections import defaultdict
from pprint import pformat

import boto3
import botocore
import pydash as pydash
from botocore.exceptions import WaiterError

from infra_buddy.utility import print_utility
from infra_buddy.utility.exception import NOOPException
from infra_buddy.utility.waitfor import waitfor


def _load_file_to_json(parameter_file):
    with open(parameter_file, 'r') as source:
        return json.load(source)


class CloudFormationBuddy(object):
    def __init__(self, deploy_ctx):
        super(CloudFormationBuddy, self).__init__()
        self.exports = {}
        self.resources = []
        self.deploy_ctx = deploy_ctx
        self.client = boto3.client('cloudformation', region_name=self.deploy_ctx.region)
        self.existing_change_set_id = None
        self.stack_id = None
        self.change_set_description = None
        self.stack_description = None
        self.stack_name = self.deploy_ctx.stack_name

    def does_stack_exist(self):
        return self._describe_stack()

    def _describe_stack(self):
        try:
            stacks = self.client.describe_stacks(StackName=self.stack_name)['Stacks']
            if len(stacks) >= 1:
                print_utility.info("Stack Description - {}".format(pformat(stacks)))
                self.stack_description = stacks[0]
                self.stack_id = self.stack_description['StackId']
                return True
        except (botocore.exceptions.ValidationError, botocore.exceptions.ClientError) as err:
            pass
        return False

    def get_stack_status(self, refresh=False):
        if not self.stack_description or refresh:  self._describe_stack()
        return self.stack_description['StackStatus'] if self.stack_description else "UNAVAILABLE"

    def delete_change_set(self):
        self._validate_changeset_operation_ready('delete_change_set')
        if self.get_change_set_execution_status(refresh=True) == 'EXECUTE_FAILED':
            print_utility.info(
                "Skipping Delete ChangeSet - ChangeSetID: {} Execution Status Failed".format(
                    self.existing_change_set_id))
            return
        response = self.client.delete_change_set(ChangeSetName=self.existing_change_set_id)
        print_utility.info(
            "Deleted ChangeSet - ChangeSetID: {} Response: {}".format(self.existing_change_set_id, response))

    def create_change_set(self, template_file_url, parameter_file):
        resp = self.client.create_change_set(
            StackName=self.stack_name,
            TemplateURL=template_file_url,
            Parameters=_load_file_to_json(parameter_file),
            Capabilities=[
                'CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'
            ],
            ChangeSetName=self.deploy_ctx.change_set_name
        )
        self.existing_change_set_id = resp['Id']
        self.stack_id = resp['StackId']
        print_utility.info("Created ChangeSet:\nChangeSetID: {}\nStackID: {}\n{}".format(resp['Id'],
                                                                                        resp['StackId'],
                                                                                        pformat(resp,indent=1)))
        waiter = self.client.get_waiter('change_set_create_complete')
        try:
            waiter.wait(ChangeSetName=self.deploy_ctx.change_set_name, StackName=self.stack_id)
        except WaiterError as we:
            self.change_set_description = we.last_response
            noop = self._is_noop_changeset()
            print_utility.info("ChangeSet Failed to Create - {}".format(self.change_set_description['StatusReason']))
            if not noop:
                self.log_changeset_status()
                self._clean_change_set_and_exit()

    def _is_noop_changeset(self):
        message = self.change_set_description.get('StatusReason', '')
        return "No updates are to be performed." in message or \
               "The submitted information didn't contain changes." in message

    def get_change_set_status(self, refresh=False):
        self._validate_changeset_operation_ready('get_change_set_status')
        self.describe_change_set(refresh=refresh)
        return self.change_set_description['Status']

    def describe_change_set(self,refresh=False):
        self._validate_changeset_operation_ready('describe_change_set')
        if not self.change_set_description or refresh:
            self.change_set_description = self.client.describe_change_set(ChangeSetName=self.existing_change_set_id)

    def get_change_set_execution_status(self, refresh=False):
        self._validate_changeset_operation_ready('get_change_set_execution_status')
        self.describe_change_set(refresh=refresh)
        return self.change_set_description['ExecutionStatus']

    def execute_change_set(self):
        self._validate_changeset_operation_ready('execute changeset')
        action = 'update-stack'
        self._start_update_event(action)
        self.client.execute_change_set(ChangeSetName=self.existing_change_set_id)
        waiter = self.client.get_waiter('stack_update_complete')
        try:
            waiter.wait(StackName=self.stack_id)
            success = True
        except WaiterError as we:
            success = False
        self._finish_update_event(action, success)
        if not success:
            self._clean_change_set_and_exit(failed=True,failure_stage='execute')

    def _validate_changeset_operation_ready(self, operation):
        if not self.existing_change_set_id:
            raise Exception("Attempted to {} before create was called".format(operation))

    def should_execute_change_set(self):
        self._validate_changeset_operation_ready('should_execute_change_set')
        self.describe_change_set()
        if self._is_noop_changeset():
            return False
        changes_ = self.change_set_description['Changes']
        if len(changes_) == 2:
            if pydash.get(changes_[0], 'ResourceChange.ResourceType') == "AWS::ECS::Service":
                if pydash.get(changes_[1], 'ResourceChange.ResourceType') == "AWS::ECS::TaskDefinition":
                    if self.deploy_ctx.should_skip_ecs_trivial_update():
                        print_utility.info(
                            "WARN: Skipping changeset update because no computed changes except to service & task "
                            "rerun with SKIP_ECS=True to force")
                        return False
        return True

    def should_create_change_set(self):
        exists = self.does_stack_exist()
        if exists:
            if self.get_stack_status() == 'ROLLBACK_COMPLETE':
                print_utility.error("Can not update stack in state 'ROLLBACK_COMPLETE' -"
                                    " delete stack to recreate.",
                                    raise_exception=True)
        return exists

    def create_stack(self, template_file_url, parameter_file):
        action = 'create-stack'
        self._start_update_event(action)
        print_utility.info("Template URL: " + template_file_url)
        resp = self.client.create_stack(
            StackName=self.stack_name,
            TemplateURL=template_file_url,
            Parameters=_load_file_to_json(parameter_file),
            Capabilities=[
                'CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM'
            ],
            Tags=[
                {
                    'Key': 'Environment',
                    'Value': self.deploy_ctx.environment
                },
                {
                    'Key': 'Application',
                    'Value': self.deploy_ctx.application
                },
                {
                    'Key': 'Role',
                    'Value': self.deploy_ctx.role
                }
            ]
        )
        self.stack_id = resp['StackId']
        waiter = self.client.get_waiter('stack_create_complete')
        try:
            waiter.wait(StackName=self.stack_id)
            success = True
        except WaiterError as we:
            self.stack_description = we.last_response
            success = False
        self._finish_update_event(action, success)
        print_utility.info("Created Stack -  StackID: {}".format(resp['StackId']))
        if not success:
            raise Exception("Cloudformation stack failed to create")

    def log_stack_status(self, print_stack_events=False):
        print_utility.banner_warn("Stack Details: {}".format(self.stack_id), pformat(self.stack_description,indent=2))
        if print_stack_events:
            self._print_stack_events()

    def log_changeset_status(self, warn=True):
        if warn:
            print_utility.banner_warn("ChangeSet Details: {}".format(self.existing_change_set_id),
                                  pformat(self.change_set_description))
        else:
            print_utility.info("ChangeSet Details: {}".format(self.existing_change_set_id))
            print_utility.info_banner(pformat(self.change_set_description))

    def _clean_change_set_and_exit(self, failed=False, failure_stage='create'):
        self.delete_change_set()
        if failed:
            raise Exception("FAILED: Could not {} changeset".format(failure_stage))

    def _start_update_event(self, action):
        self.deploy_ctx.notify_event(
            title="{action} stack {stack_name} started".format(action=action, stack_name=self.deploy_ctx.stack_name),
            type="success")

    def _finish_update_event(self, action, success):
        msg = "{action} stack {stack_name} {status}".format(action=action,
                                                            stack_name=self.deploy_ctx.stack_name,
                                                            status='completed' if success else 'failed')
        print_utility.progress(msg)
        if success:
            self.deploy_ctx.notify_event(title=msg,
                                         type="success")
        else:
            self.deploy_ctx.notify_event(title=msg,
                                         type="error")
            self.log_stack_status(print_stack_events=True)

    def get_export_value(self, param=None, fully_qualified_param_name=None):
        if not fully_qualified_param_name:
            fully_qualified_param_name = "{stack_name}-{param}".format(stack_name=self.stack_name, param=param)
        if len(self.exports) == 0: self._load_export_values()
        val = self.exports.get(fully_qualified_param_name, None)
        if val is None:
            print_utility.warn("Could not locate export value - {}".format(fully_qualified_param_name))
        return val

    def _load_export_values(self):
        export_results = self.client.list_exports()
        export_list = export_results['Exports']
        while export_list is not None:
            for export in export_list:
                self.exports[export['Name']] = export['Value']
            next_ = export_results.get('NextToken', None)
            if next_:
                export_results = self.client.list_exports(NextToken=next_)
                export_list = export_results.get('Exports', None)
            else:
                export_list = None

    def get_existing_parameter_value(self, param_val):
        self._describe_stack()
        for param in self.stack_description.get('Parameters', []):
            if param['ParameterKey'] == param_val:
                return param['ParameterValue']
        print_utility.error("Could not locate parameter value: {}".format(param_val))
        return None

    def get_resource_list(self):
        if len(self.resources) == 0:
            self.resources = self.load_stack_resources(self.stack_name)
        return self.resources

    def load_stack_resources(self, to_inspect):
        ret = []
        res = self.client.list_stack_resources(StackName=to_inspect)
        res_resources_list = res['StackResourceSummaries']
        while res_resources_list is not None:
            ret.extend(res_resources_list)
            next_ = res.get('NextToken', None)
            if next_:
                res = self.client.list_stack_resources(StackName=to_inspect, NextToken=next_)
                res_resources_list = res['StackResourceSummaries']
            else:
                res_resources_list = None
        return ret

    def list_stacks(self, filter=None):
        ret = []
        res = self.client.list_stacks(StackStatusFilter=['UPDATE_COMPLETE', 'CREATE_COMPLETE'])
        res_stack_list = res['StackSummaries']
        while res_stack_list is not None:
            ret.extend(res_stack_list)
            next_ = res.get('NextToken', None)
            if next_:
                res = self.client.list_stacks(StackStatusFilter=['UPDATE_COMPLETE', 'CREATE_COMPLETE'], NextToken=next_)
                res_stack_list = res['StackSummaries']
            else:
                res_stack_list = None
        pluck = pydash.pluck(ret, "StackName")
        return [stack for stack in pluck if filter and stack.startswith(filter)]

    def load_resources_for_stack_list(self, stacks):
        resources = defaultdict(list)
        for stack in stacks:
            resources[stack] = self.load_stack_resources(stack)
        return resources

    def _print_stack_events(self):
        events = []
        res = self.client.describe_stack_events(StackName=self.stack_name)
        res_list = res['StackEvents']
        while res_list is not None:
            events.extend(res_list)
            next_ = res.get('NextToken', None)
            if next_:
                res = self.client.describe_stack_events(StackName=self.stack_name, NextToken=next_)
                res_list = res['StackEvents']
            else:
                res_list = None
        for ev in events:
            if "ResourceStatusReason" in ev:
                template = "{Timestamp}\t{ResourceStatus}\t{ResourceType}\t{LogicalResourceId}\t{ResourceStatusReason}"
            else:
                template = "{Timestamp}\t{ResourceStatus}\t{ResourceType}\t{LogicalResourceId}"
            print_utility.warn(template.format(**ev))
