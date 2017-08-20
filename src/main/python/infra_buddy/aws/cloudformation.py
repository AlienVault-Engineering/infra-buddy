import json

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
        self.deploy_ctx = deploy_ctx
        self.client = boto3.client('cloudformation', region_name=self.deploy_ctx.region)
        self.existing_change_set_id = None
        self.stack_id = None
        self.change_set_description = None
        self.stack_description = None
        self.stack_name = self.deploy_ctx.stack_name

    def does_stack_exist(self, stack_name=None):
        return self._describe_stack(stack_name)

    def _describe_stack(self, stack_name=None):
        if not stack_name:
            stack_name = self.stack_name
        try:
            stacks = self.client.describe_stacks(StackName=stack_name)['Stacks']
            if len(stacks) >= 1:
                print_utility.info("Persisting stacks - {}".format(stacks))
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
        print_utility.info("Created ChangeSet - ChangeSetID: {} StackID: {}".format(resp['Id'], resp['StackId']))
        waiter = self.client.get_waiter('change_set_create_complete')
        try:
            waiter.wait(ChangeSetName=self.deploy_ctx.change_set_name, StackName=self.stack_id)
            # status = self.get_change_set_status(refresh=True) #waitfor(self.get_change_set_status, ['CREATE_PENDING','CREATE_IN_PROGRESS'], 10, 300, args={"refresh": True},negate=True)
        except WaiterError as we:
            self.change_set_description = we.last_response
            self.log_changeset_status()
            status_reason_ = self.change_set_description['StatusReason']
            terminal = "The submitted information didn't contain changes. Submit different information to create a change set." != status_reason_
            print_utility.info("ChangeSet Failed to Create - {}".format(status_reason_))
            self._clean_change_set_and_exit(failed=terminal)

    def get_change_set_status(self, refresh=False):
        self._validate_changeset_operation_ready('get_change_set_status')
        if not self.change_set_description or refresh: self.describe_change_set()
        return self.change_set_description['Status']

    def describe_change_set(self):
        self._validate_changeset_operation_ready('describe_change_set')
        self.change_set_description = self.client.describe_change_set(ChangeSetName=self.existing_change_set_id)

    def get_change_set_execution_status(self, refresh=False):
        self._validate_changeset_operation_ready('get_change_set_execution_status')
        if not self.change_set_description or refresh: self.describe_change_set()
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

        # final_status = self.get_stack_status()
        # for in_progress in ["UPDATE_IN_PROGRESS", "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS"]:
        #     final_status = waitfor(self.get_stack_status, in_progress, interval_seconds=10, max_attempts=300,
        #                            negate=True, args={"refresh": True})
        # success = final_status == "UPDATE_COMPLETE"
        self._finish_update_event(action, success)
        if not success:
            self._clean_change_set_and_exit(failed=True)

    def _validate_changeset_operation_ready(self, operation):
        if not self.existing_change_set_id:
            raise Exception("Attempted to {} before create was called".format(operation))

    def should_execute_change_set(self):
        self._validate_changeset_operation_ready('should_execute_change_set')
        if "AVAILABLE" != self.get_change_set_execution_status():
            waitfor(self.get_change_set_execution_status, expected_result="AVAILABLE",
                    interval_seconds=10,
                    max_attempts=10, args={"refresh": True})
        changes_ = self.change_set_description['Changes']
        if len(changes_) == 2:
            if pydash.get(changes_[0], 'ResourceChange.ResourceType') == "AWS::ECS::Service":
                if pydash.get(changes_[1], 'ResourceChange.ResourceType') == "AWS::ECS::TaskDefinition":
                    if self.deploy_ctx.should_skip_ecs_trivial_update():
                        print_utility.warn(
                            "WARN: Skipping changeset update because no computed changes except to service & task "
                            "rerun with SKIP_SKIP=True to force")
                        return False
        return True

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
            self.log_stack_status()
            success = False
        # final_status = self.get_stack_status()
        # final_status = waitfor(self.get_stack_status, "CREATE_IN_PROGRESS", interval_seconds=10, max_attempts=300,
        #                        negate=True, args={"refresh": True})
        # success = final_status == "CREATE_COMPLETE"
        self._finish_update_event(action, success)
        print_utility.info("Created Stack -  StackID: {}".format(resp['StackId']))
        if not success:
            raise Exception("Cloudformation stack failed to create")

    def log_stack_status(self):
        print_utility.banner_warn("Stack Details: {}".format(self.stack_id), str(self.stack_description))

    def log_changeset_status(self):
        print_utility.banner_warn("ChangeSet Details: {}".format(self.existing_change_set_id),
                                  str(self.change_set_description))

    def _clean_change_set_and_exit(self, failed=False):
        self.delete_change_set()
        if failed:
            raise Exception("FAILED: Could not create changeset")
        else:
            raise NOOPException("No change to execute")
        pass

    def _start_update_event(self, action):
        self.deploy_ctx.notify_event(
            title="{action} stack {stack_name} started".format(action=action, stack_name=self.deploy_ctx.stack_name),
            type="success")

    def _finish_update_event(self, action, success):
        msg = "{action} stack {stack_name} {status}".format(action=action,
                                                            stack_name=self.deploy_ctx.stack_name,
                                                            status='completed' if success else 'failed')
        if success:
            self.deploy_ctx.notify_event(title=msg,
                                         type="success")
        else:
            self.deploy_ctx.notify_event(title=msg,
                                         type="error")
            self.log_stack_status()
