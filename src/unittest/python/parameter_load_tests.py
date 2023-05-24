import json
import os
import tempfile

from infra_buddy_too.aws import s3
from infra_buddy_too.aws.cloudformation import CloudFormationBuddy
from infra_buddy_too.aws.s3 import S3Buddy
from infra_buddy_too.commandline import cli
from infra_buddy_too.context.deploy_ctx import DeployContext
from infra_buddy_too.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy_too.template.template import NamedLocalTemplate
from infra_buddy_too.utility import helper_functions
from testcase_parent import ParentTestCase


class ParameterLoadTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(ParameterLoadTestCase, cls).setUpClass()

    def test_parameter_load_transformation(self):
        os.environ.setdefault("OS_VAR","BAR")
        ctx = DeployContext.create_deploy_context(application="dev-{}".format(self.run_random_word), role="cluster",
                                                  environment="unit-test",
                                                  defaults=self.default_config)
        try:
            template_dir = ParentTestCase._get_resource_path("parameter_load_tests/param_load")
            deploy = CloudFormationDeploy(ctx.stack_name, NamedLocalTemplate(template_dir), ctx)
            self.assertEqual(deploy.defaults['OS_VAR'], "BAR", 'Did not respect defaut')
            self.assertEqual(deploy.defaults['FOO'], "unit-test-bar", 'Did not respect defaut')
        finally:
            pass

    def test_parameter_transformation(self):
        ctx = DeployContext.create_deploy_context(application="dev-{}".format(self.run_random_word), role="cluster",
                                                  environment="unit-test",
                                                  defaults=self.default_config)
        try:
            template_dir = ParentTestCase._get_resource_path("parameter_load_tests/fargate")
            deploy = CloudFormationDeploy(ctx.stack_name, NamedLocalTemplate(template_dir), ctx)
            self.assertEqual(deploy.defaults['TASK_SOFT_MEMORY'], 512, 'Did not respect defaut')
            self.assertEqual(deploy.defaults['TASK_CPU'], 64, 'Did not respect defaut')
            ctx['USE_FARGATE'] = 'true'
            deploy = CloudFormationDeploy(ctx.stack_name, NamedLocalTemplate(template_dir), ctx)
            self.assertEqual(deploy.defaults['TASK_SOFT_MEMORY'], '512', 'Did not transform memory')
            self.assertEqual(deploy.defaults['TASK_CPU'], 256, 'Did not transform cpu')
        finally:
            pass

    def test_fargate_processing(self):
        ctx = DeployContext.create_deploy_context(application="dev-{}".format(self.run_random_word), role="cluster",
                                                  environment="unit-test",
                                                  defaults=self.default_config)
        ctx['USE_FARGATE'] = 'true'
        cpu_transforms = {
            128: 256,
            12: 256,
            257: 512,
            1023: 1024,
            1024: 1024,
            2000: 2048,
            10000: 4096,
        }
        for to_transform, expected in cpu_transforms.items():
            self.assertEqual(helper_functions.transform_fargate_cpu(ctx,to_transform), expected,
                             'Did not transform correctly')
        memory_transforms = {
            128: '512',
            12: '512',
            257: '512',
            1023: '1024',
            1024: '1024',
            2000: '2048',
            10000: '10240',
        }
        for to_transform, expected in memory_transforms.items():
            self.assertEqual(helper_functions.transform_fargate_memory(ctx,to_transform), expected,
                             'Did not transform correctly')

        valid_configurations = [
            [256,'512'],
            [2048,'5120'],
            [1024,'2048'],
        ]
        invalid_configuration = [
            [256,'5120'],
            [4096,'5120']
        ]
        for config in valid_configurations:
            helper_functions._validate_fargate_resource_allocation(config[0],config[1],{})
        for config in invalid_configuration:
            try:
                helper_functions._validate_fargate_resource_allocation(config[0],config[1],{})
                self.fail("Failed to detect invalid fargate configuration - {} CPU {} Memory".format(config[0],config[1]))
            except:
                pass


