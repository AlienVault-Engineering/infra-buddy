import json
import os
import tempfile

from infra_buddy.aws import s3
from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.aws.s3 import S3Buddy
from infra_buddy.commandline import cli
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy.template.template import NamedLocalTemplate
from infra_buddy.utility import helper_functions
from testcase_parent import ParentTestCase


class ParameterLoadTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(ParameterLoadTestCase, cls).setUpClass()

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
            self.assertEqual(deploy.defaults['TASK_SOFT_MEMORY'], '0.5GB', 'Did not transform memory')
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
        for to_transform, expected in cpu_transforms.iteritems():
            self.assertEqual(helper_functions.transform_fargate_cpu(ctx,to_transform), expected,
                             'Did not transform correctly')
        memory_transforms = {
            128: '0.5GB',
            12: '0.5GB',
            257: '0.5GB',
            1023: '1GB',
            1024: '1GB',
            '1GB': '1GB',
            2000: '2GB',
            10000: '10GB',
        }
        for to_transform, expected in memory_transforms.iteritems():
            self.assertEqual(helper_functions.transform_fargate_memory(ctx,to_transform), expected,
                             'Did not transform correctly')

        valid_configurations = [
            [256,'0.5GB'],
            [2048,'5GB'],
            [1024,'2GB'],
        ]
        invalid_configuration = [
            [256,'5GB'],
            [4096,'5GB']
        ]
        for config in valid_configurations:
            helper_functions._validate_fargate_resource_allocation(config[0],config[1],{})
        for config in invalid_configuration:
            try:
                helper_functions._validate_fargate_resource_allocation(config[0],config[1],{})
                self.fail("Failed to detect invalid fargate configuration - {} CPU {} Memory".format(config[0],config[1]))
            except:
                pass


