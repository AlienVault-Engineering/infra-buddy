import json

from click import UsageError

from infra_buddy_too.aws import cloudformation
from infra_buddy_too.aws.cloudformation import CloudFormationBuddy
from infra_buddy_too.aws.ecs import ECSBuddy
from infra_buddy_too.context import deploy_ctx
from infra_buddy_too.deploy.ecs_deploy import ECSDeploy
from testcase_parent import ParentTestCase


class FakeEcsClient(object):
    def __init__(self, testcase, task_failed=False):
        # type: (ECSUpdateTemplateTestCase) -> None
        path = testcase._get_resource_path("ecs_tests/task_def.json")
        if task_failed:
            describe_def_path = testcase._get_resource_path("ecs_tests/describe_failed_task.json")
        else:
            describe_def_path = testcase._get_resource_path("ecs_tests/describe_success_task.json")
        with open(path, 'r') as definition:
            self.test_task_definition = json.load(definition)
        with open(describe_def_path, 'r') as definition:
            self.finished_description = json.load(definition)
        service_definition_path = testcase._get_resource_path("ecs_tests/describe_service.json")
        with open(service_definition_path,'r') as service_def:
            self.service_definition = json.load(service_def)

        self.service_update = []
        self.task_run = []
        self.waiter_name = []

    def describe_service(self, cluster, services):
        return self.service_definition

    def describe_task_definition(self, taskDefinition):
        return self.test_task_definition

    def register_task_definition(self, **kwargs):
        return self.test_task_definition

    def describe_tasks(self, **kwargs):
        return self.finished_description

    def update_service(self,
                       cluster,
                       service,
                       taskDefinition):
        self.service_update.append([{"cluster": cluster, "service": service, "taskDefinition": taskDefinition}])

    def run_task(self, cluster, taskDefinition, networkConfiguration, launchType):
        self.task_run.append(
            {"cluster": cluster, "launchType": launchType, "networkConfiguration": networkConfiguration,
             "taskDefinition": taskDefinition})
        return {"tasks": [{"taskArn": taskDefinition}]}

    def get_waiter(self, waiter_name):
        self.waiter_name.append(waiter_name)
        return self

    def wait(self, cluster, services=None, tasks=None):
        return


class ECSUpdateTemplateTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(ECSUpdateTemplateTestCase, cls).setUpClass()

    def test_ecs_update(self):
        ecs = ECSBuddy(self.test_deploy_ctx)
        ecs.client = FakeEcsClient(self)
        ecs.cluster = "fake-cluster"
        ecs.ecs_service = "fake-service"
        ecs.ecs_task_family = "fake-task-family"
        ecs.set_container_image("path", "bar")
        self.assertTrue(ecs.requires_update(), "Did not recognize udpate required")
        ecs.set_container_image("271083817914.dkr.ecr.us-west-2.amazonaws.com/otx/otxb-portal-yara-listener", "1.21")
        self.assertFalse(ecs.requires_update(), "Did not recognize udpate not required")
        ecs.perform_update()

    def test_ecs_deploy(self):
        # Set this low as it gets called in the constructor of ECS Deploy
        cloudformation.MAX_ATTEMPTS = 1
        try:
            image = "271083817914.dkr.ecr.us-west-2.amazonaws.com/otx/otxb-portal-yara-listener"
            artifact_id = "1.21"
            deploy = ECSDeploy(deploy_ctx=self.test_deploy_ctx, artifact_id=artifact_id,
                               artifact_location=image)
            deploy.ecs_buddy.client = FakeEcsClient(self)
            do_deploy = deploy.do_deploy(dry_run=False)
            do_deploy = deploy.do_deploy(dry_run=True)
            self.assertIsNone(do_deploy, "Failed to dry run")
            # test to make sure we are failing when the service isn't running the expected
            self.assertFalse(do_deploy, "Failed to recognize update not required")
            deploy.artifact_location = "ci-nudge-frontend-database-maintenance-ECSTaskFamily"
            deploy.artifact_id = "1.22"
            deploy.ecs_buddy.ecs_task_family = "ci-nudge-frontend-database-maintenance-ECSTaskFamily"
            with self.assertRaises(UsageError):
                deploy.do_deploy(dry_run=False)
        finally:
            cloudformation.MAX_ATTEMPTS = 5

    def test_ecs_run_task(self):
        # Set this low as it gets called in the constructor of ECS Deploy
        cloudformation.MAX_ATTEMPTS = 1
        try:
            self.test_deploy_ctx[deploy_ctx.ECS_TASK_RUN] = "True"
            self._do_ecs_run_test('tasks_stopped')
            self.test_deploy_ctx[deploy_ctx.WAIT_FOR_ECS_TASK_RUN_FINISH] = "False"
            self._do_ecs_run_test('tasks_running')
        finally:
            cloudformation.MAX_ATTEMPTS = 5
            self.test_deploy_ctx[deploy_ctx.ECS_TASK_RUN] = "False"

    def test_ecs_run_task_fail(self):
        # Set this low as it gets called in the constructor of ECS Deploy
        cloudformation.MAX_ATTEMPTS = 1
        try:
            self.test_deploy_ctx[deploy_ctx.ECS_TASK_RUN] = "True"
            self._do_ecs_run_test('tasks_stopped', task_failed=True)
            self.fail("Did not fail ")
        except Exception as e:
            self.assertTrue(isinstance(e, UsageError))
        finally:
            cloudformation.MAX_ATTEMPTS = 5
            self.test_deploy_ctx[deploy_ctx.ECS_TASK_RUN] = "False"

    def _do_ecs_run_test(self, expected_waiter, task_failed=False):
        deploy = ECSDeploy(deploy_ctx=self.test_deploy_ctx,
                           artifact_id="1.21",
                           artifact_location="271083817914.dkr.ecr.us-west-2.amazonaws.com/otx/otxb-portal-yara-listener")
        fake_ecs_client = FakeEcsClient(self, task_failed)
        deploy.ecs_buddy.client = fake_ecs_client
        deploy.ecs_buddy.ecs_task_family = "prod-otxb-portal-yara-listener-ECSTaskFamily"
        do_deploy = deploy.do_deploy(dry_run=False)
        self.assertTrue(do_deploy, "Failed to run task on same image")
        self.assertTrue(len(fake_ecs_client.task_run) == 1, "Ran task")
        self.assertEqual(fake_ecs_client.task_run[0]['taskDefinition'],
                         "arn:aws:ecs:us-west-2:271083817914:task-definition/prod-otxb-portal-yara-listener-ECSTaskFamily:12",
                         "Did not run tasks")
        self.assertEqual(expected_waiter, fake_ecs_client.waiter_name[0], "Did not request expected waiter")
