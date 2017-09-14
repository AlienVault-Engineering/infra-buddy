import json

from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.deploy.ecs_deploy import ECSDeploy
from testcase_parent import ParentTestCase


class FakeCFClient(object):
    def __init__(self, testcase):
        # type: () -> None
        path = testcase._get_resource_path("introspect_tests/list_stack_response.json")
        with open(path, 'r') as definition:
            self.stacK_list = json.load(definition)
        path = testcase._get_resource_path("introspect_tests/stack_resource_response.json")
        with open(path, 'r') as definition:
            self.resource = json.load(definition)

    def list_stacks(self, StackStatusFilter):
        return self.stacK_list

    def list_stack_resources(self, StackName, NextToken=None):
        return self.resource


class IntrospectTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(IntrospectTestCase, cls).setUpClass()

    def test_stack_list(self):
        cf_buddy = CloudFormationBuddy(self.test_deploy_ctx)
        cf_buddy.client = FakeCFClient(self)
        stacks = cf_buddy.list_stacks("ci")
        self.assertTrue(len(stacks) == 1, "Did not filter stacks")
        stacks = cf_buddy.list_stacks("prod")
        self.assertTrue(len(stacks) == 1, "Did not filter stacks")
        resources = cf_buddy.load_resources_for_stack_list(['ci-otxb-reputation-proxy-api'])
        self.assertTrue(len(resources) == 1, "Did not load resources")
        self.assertTrue(len(resources['ci-otxb-reputation-proxy-api']) == 4, "Did not load resources for stack")
