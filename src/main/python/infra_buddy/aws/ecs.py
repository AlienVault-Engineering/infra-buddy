import logging

import boto3
import pydash
from botocore.exceptions import WaiterError

from infra_buddy.aws.cloudwatch_logs import CloudwatchLogsBuddy
from infra_buddy.utility import print_utility

from infra_buddy.aws.cloudformation import CloudFormationBuddy


class ECSBuddy(object):
    def __init__(self, deploy_ctx, run_task: bool = False):
        super(ECSBuddy, self).__init__()
        self.deploy_ctx = deploy_ctx
        self.client = boto3.client('ecs', region_name=self.deploy_ctx.region)
        self.cf = CloudFormationBuddy(deploy_ctx)
        self.cw_buddy = CloudwatchLogsBuddy(self.deploy_ctx)
        self.cluster = self.cf.wait_for_export(
            fully_qualified_param_name=f"{self.deploy_ctx.cluster_stack_name}-ECSCluster")
        self.run_task = run_task
        if run_task:
            self.networkConfiguration = self._build_network_configuration()
        else:
            self.ecs_service = self.cf.wait_for_export(
                fully_qualified_param_name=f"{self.deploy_ctx.stack_name}-ECSService")
        self.ecs_task_family = self.cf.wait_for_export(
            fully_qualified_param_name=f"{self.deploy_ctx.stack_name}-ECSTaskFamily")
        self.ecs_task_execution_role = self.cf.wait_for_export(
            fully_qualified_param_name=f"{self.deploy_ctx.stack_name}-ECSTaskExecutionRole")
        self.ecs_task_role = self.cf.wait_for_export(
            fully_qualified_param_name=f"{self.deploy_ctx.stack_name}-ECSTaskRole")
        self.using_fargate = self.cf.wait_for_export(
            fully_qualified_param_name=f"{self.deploy_ctx.stack_name}-Fargate")
        self.task_definition_description = None
        self.new_image = None

    def set_container_image(self, location, tag):
        self.new_image = f"{location}:{tag}"

    def requires_update(self):
        if not self.new_image:
            print_utility.warn("Checking for ECS update without registering new image ")
            return False
        if not self.ecs_task_family:
            if self.run_task:
                print_utility.warn("No ECS Task family found - "
                                   "assuming first deploy of stack but continuing to run task")
            else:
                print_utility.warn("No ECS Task family found - assuming first deploy of stack and skipping ECS update")
                return False
        self._describe_task_definition()
        existing = pydash.get(self.task_definition_description, "containerDefinitions[0].image")
        print_utility.info(f"ECS task existing image - {existing}")
        print_utility.info(f"ECS task desired image - {self.new_image}")
        return self.run_task or existing != self.new_image

    def perform_update(self):
        self._describe_task_definition(refresh=True)
        new_task_def = {
            'family': self.task_definition_description['family'],
            'containerDefinitions': self.task_definition_description['containerDefinitions'],
            'volumes': self.task_definition_description['volumes']
        }
        if 'networkMode' in self.task_definition_description:
            new_task_def['networkMode'] = self.task_definition_description['networkMode']
        new_task_def['containerDefinitions'][0]['image'] = self.new_image

        ctx_memory = self.deploy_ctx.get('TASK_MEMORY')
        if ctx_memory:
            new_task_def['containerDefinitions'][0]['memory'] = ctx_memory

        if 'TASK_SOFT_MEMORY' in self.deploy_ctx and self.deploy_ctx['TASK_SOFT_MEMORY']:
            new_task_def['containerDefinitions'][0]['memoryReservation'] = self.deploy_ctx['TASK_SOFT_MEMORY']

        ctx_cpu = self.deploy_ctx.get('TASK_CPU')
        if ctx_cpu:
            new_task_def['containerDefinitions'][0]['cpu'] = ctx_cpu

        # set at the task level for fargate definitions
        if self.using_fargate:
            first_container = new_task_def['containerDefinitions'][0]
            new_task_def['requiresCompatibilities'] = ['FARGATE']
            new_cpu = ctx_cpu or first_container.get('cpu')
            if new_cpu:
                new_task_def['cpu'] = str(new_cpu)  # not sure if this is right but AWS says it should be str

            new_memory = ctx_memory or first_container.get('memoryReservation')
            if new_memory:
                new_task_def['memory'] = str(new_memory)  # not sure if this is right but AWS says it should be str

        if self.ecs_task_execution_role:
            new_task_def['executionRoleArn'] = self.ecs_task_execution_role
        if self.ecs_task_role:
            new_task_def['taskRoleArn'] = self.ecs_task_role

        for k, v in self.deploy_ctx.items():
            print_utility.info(f'[deploy_ctx] {k} = {repr(v)}')

        for k, v in new_task_def.items():
            print_utility.info(f'[new_task_def] {k} = {repr(v)}')

        updated_task_definition = self.client.register_task_definition(**new_task_def)['taskDefinition']
        new_task_def_arn = updated_task_definition['taskDefinitionArn']

        if self.run_task:
            return self.exec_run_task(new_task_def_arn)
        else:
            return self.update_service(new_task_def_arn)

    def update_service(self, new_task_def_arn):
        self.deploy_ctx.notify_event(
            title=f"Update of ecs service {self.ecs_service} started",
            type="success")
        self.client.update_service(
            cluster=self.cluster,
            service=self.ecs_service,
            taskDefinition=new_task_def_arn)
        waiter = self.client.get_waiter('services_stable')
        success = True
        try:
            waiter.wait(
                cluster=self.cluster,
                services=[self.ecs_service]
            )
            description = self.describe_service()
            running_task_def_arn = pydash.get(description,"deployments.0.taskDefinition",None)
            print_utility.info(f"Currently running task {running_task_def_arn} - {description}")
            if running_task_def_arn != new_task_def_arn:
                success = False
        except WaiterError as e:
            success = False
            print_utility.error(f"Error waiting for service to stabilize - {e}", raise_exception=True)
        finally:
            self.deploy_ctx.notify_event(
                title=f"Update of ecs service {self.ecs_service} completed: {'Success' if success else 'Failed'}",
                type="success" if success else "error")
            return success

    def _describe_task_definition(self, refresh=False):
        if self.task_definition_description and not refresh:
            return
        self.task_definition_description = self.client.describe_task_definition(taskDefinition=
                                                                                self.ecs_task_family)['taskDefinition']

    def describe_service(self):
        return self.client.describe_service(cluster=self.cluster,services=self.ecs_service)["services"][0]

    def exec_run_task(self, new_task_def_arn):
        self.deploy_ctx.notify_event(
            title=f"Running one time ecs task with image: {self.new_image}",
            type="success")
        ret = self.client.run_task(cluster=self.cluster,
                                   launchType='FARGATE' if self.using_fargate else 'EC2',
                                   taskDefinition=new_task_def_arn,
                                   networkConfiguration=self.networkConfiguration)
        success = True

        if self.deploy_ctx.wait_for_run_task_finish():
            waiter_name = 'tasks_stopped'
        else:
            waiter_name = 'tasks_running'
        try:
            waiter = self.client.get_waiter(waiter_name=waiter_name)
            arn_ = ret['tasks'][0]['taskArn']
            print_utility.warn(f"Running task with ARN: {arn_}")
            if self.deploy_ctx.wait_for_run_task_finish():
                # increase the number of retries
                waiter.config.max_attempts = self.deploy_ctx.get_task_max_retry()
            waiter.wait(cluster=self.cluster, tasks=[arn_])
            description = self.client.describe_tasks(tasks=[arn_],cluster=self.cluster)
            if self.deploy_ctx.wait_for_run_task_finish():
                exit_code_ = pydash.get(description,"tasks.0.containers.0.exitCode",0)
                print_utility.info(f"Retrieved exit code from container: {exit_code_} - {description}")
                if exit_code_>0:
                    success = False

        except WaiterError as e:
            success = False
            print_utility.error(f"Error waiting for task to {'finish' if self.deploy_ctx.wait_for_run_task_finish() else 'start'} - {e}", raise_exception=True)
        finally:
            self.cw_buddy.print_latest()
            self.deploy_ctx.notify_event(
                title=f"Task running with started: {'Success' if success else 'Failed'}: Image - {self.new_image} ",
                type="success" if success else "error")
            return success

    def _build_network_configuration(self):
        # {'awsvpcConfiguration': {'subnets': ['subnet-030d5ae3a5aed3c30', 'subnet-0058692e292b68211', 'subnet-02ca3729edae57a6a'],
        # 'securityGroups': ['sg-087a1bbf3463e7614'], 'assignPublicIp': 'DISABLED'}}
        subnets = []
        for sub in ['A', 'B', 'C']:
            subnet = self.cf.wait_for_export(fully_qualified_param_name=f"{self.deploy_ctx.vpc_stack_name}-Subnet{sub}Priv")
            subnets.append(subnet)
        sec_group = self.cf.wait_for_export(fully_qualified_param_name=f"{self.deploy_ctx.stack_name}-FargateSecurityGroup")
        return {
            'awsvpcConfiguration': {'subnets': subnets, 'securityGroups': [sec_group], 'assignPublicIp': 'DISABLED'}}

    def what_is_your_plan(self):
        if self.run_task:
            return f"ECS Deploy running task using image {self.new_image}"
        else:
            return f"ECS Deploy updating service {self.ecs_service} to use image {self.new_image}"
