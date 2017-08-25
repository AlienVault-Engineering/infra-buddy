import json

from infra_buddy.aws.ecs import ECSBuddy
from testcase_parent import ParentTestCase


class FakeEcsClient(object):
    def __init__(self, testcase):
        # type: (ECSUpdateTemplateTestCase) -> None
        path = testcase._get_resource_path("ecs_tests/task_def.json")
        with open(path,'r') as definition:
            self.test_task_definition = json.load(definition)

    def describe_task_defintion(self,taskDefinition):
        return self.test_task_definition

    def register_task_definition(self,new_task_def):
        return self.test_task_definition

    def update_service(self,
                cluster,
                service,
                taskDefinition):
        pass

    def get_waiter(self,name):
        return self

    def wait(self,cluster,services):
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
        self.test_deploy_ctx.image = "bar"
        self.assertTrue(ecs.requires_update(),"Did not recognize udpate required")
        self.test_deploy_ctx.image = "271083817914.dkr.ecr.us-west-2.amazonaws.com/otx/otxb-portal-yara-listener:1.21"
        self.assertFalse(ecs.requires_update(),"Did not recognize udpate not required")
        ecs.perform_update()
