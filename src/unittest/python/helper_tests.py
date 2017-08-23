import os
import tempfile

from infra_buddy.aws import s3
from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.aws.s3 import S3Buddy
from infra_buddy.commandline import cli
from infra_buddy.commands.deploy_cloudformation import command
from infra_buddy.context.deploy import Deploy
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.context.template import LocalTemplate
from infra_buddy.utility import helper_functions
from testcase_parent import ParentTestCase


class HelperTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(HelperTestCase, cls).setUpClass()

    def test_rule_sorting(self):
        rules = [
            {'Priority':21},
            {'Priority':"default"},
            {'Priority':1},
            {'Priority':4},
            {'Priority':2},
            {'Priority':89}
        ]
        self.assertEqual(helper_functions._get_max_priority(rules),89,"Failed to id max")

    def test_helper_funcs(self):

        ctx = DeployContext.create_deploy_context(application="dev", role="cluster", environment="unit-test",
                                                    defaults=self.default_config)
        cloudformation = CloudFormationBuddy(ctx)
        try:
            template = ParentTestCase._get_resource_path("helper_func_tests/aws-resources.template")
            parameter_file = ParentTestCase._get_resource_path("helper_func_tests/aws-resources.parameters.json")
            deploy = Deploy(ctx.stack_name, LocalTemplate(template,parameter_file),ctx)
            command.do_command(ctx, deploy)
            rp = helper_functions.calculate_rule_priority(ctx,ctx.stack_name)
            self.assertEqual(rp,"10","Failed to detect existing rule priority")
            rp = helper_functions.calculate_rule_priority(ctx,"foo-bar")
            self.assertEqual(rp,"31","Failed to calculate rule priority")
            name = helper_functions.load_balancer_name(ctx)
            print "Name: " + name
            self.assertEqual(name.count('/'),2,"Failed to trim")
            self.assertEqual(name.count(':'),0,"Failed to trim")
            self.assertTrue(name.startswith('app'),"Failed to trim")
        finally:
            self.clean(cloudformation=cloudformation)


