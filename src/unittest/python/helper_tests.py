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


class MockCloudformationBuddy:

    def __init__(self) -> None:
        super().__init__()
        self.stack_name = ""
        self.existing = {}
        self.exports = {}
        self.exists = True

    def get_existing_parameter_value(self, param):
        return self.existing.get(param, None)

    def get_export_value(self, param):
        return self.exports.get(param, None)

    def does_stack_exist(self):
        return self.exists

class mock_cog:

    def describe_user_pool_domain(self, Domain):
        return {'DomainDescription': {'UserPoolId': 'us-west-1_guLxFEpSC', 'AWSAccountId': '604633931330',
                                      'Domain': 'unit-test-auth.nudgesecurity.io',
                                      'S3Bucket': 'aws-cognito-prod-sfo-assets',
                                      'CloudFrontDistribution': 'd8je8xsnt59o8.cloudfront.net',
                                      'Version': '20211119144006', 'Status': 'CREATING', 'CustomDomainConfig': {
                'CertificateArn': 'arn:aws:acm:us-east-1:604633931330:certificate/a143d89e-77d8-44a7-81f4-845386630814'}},
                'ResponseMetadata': {'RequestId': '66af226b-03a3-4595-b828-58bc11256656', 'HTTPStatusCode': 200,
                                     'HTTPHeaders': {'date': 'Fri, 19 Nov 2021 14:50:29 GMT',
                                                     'content-type': 'application/x-amz-json-1.1',
                                                     'content-length': '401', 'connection': 'keep-alive',
                                                     'x-amzn-requestid': '66af226b-03a3-4595-b828-58bc11256656'},
                                     'RetryAttempts': 0}}


class HelperTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(HelperTestCase, cls).setUpClass()

    def test_rule_sorting(self):
        rules = [
            {'Priority': 21},
            {'Priority': u"default"},
            {'Priority': 1},
            {'Priority': 4},
            {'Priority': 2},
            {'Priority': 89}
        ]
        self.assertEqual(helper_functions._get_max_priority(rules), 89, "Failed to id max")

    def test_helper_funcs(self):
        ctx = DeployContext.create_deploy_context(application="dev-{}".format(self.run_random_word), role="cluster",
                                                  environment="unit-test",
                                                  defaults=self.default_config)
        cloudformation = CloudFormationBuddy(ctx)
        try:
            template_dir = ParentTestCase._get_resource_path("parameter_load_tests/helper_func")
            deploy = CloudFormationDeploy(ctx.stack_name, NamedLocalTemplate(template_dir), ctx)
            deploy.do_deploy(dry_run=False)
            rp = helper_functions.calculate_rule_priority(ctx, ctx.stack_name)
            self.assertEqual(rp, "10", "Failed to detect existing rule priority")
            rp = helper_functions.calculate_rule_priority(ctx, "foo-bar")
            self.assertEqual(rp, "31", "Failed to calculate rule priority")
            name = helper_functions.load_balancer_name(ctx)
            print("Name: " + name)
            self.assertEqual(name.count('/'), 2, "Failed to trim")
            self.assertEqual(name.count(':'), 0, "Failed to trim")
            self.assertTrue(name.startswith('app'), "Failed to trim")
        finally:
            self.clean(cloudformation=cloudformation)

    def test_cognito_funcs(self):
        dev__format = "dev-{}".format(self.run_random_word)
        ctx = DeployContext.create_deploy_context(application="nudge-frontend", role="cognito",
                                                  environment="unit-test",
                                                  defaults=self.default_config)
        get_cache = helper_functions._get_cognito_client
        cf_cache = helper_functions._get_cf_buddy
        try:
            mock_cf = MockCloudformationBuddy()
            helper_functions._get_cognito_client = lambda x: mock_cog()
            helper_functions._get_cf_buddy = lambda x: mock_cf
            mock_cf.exists = False
            rp = helper_functions.custom_domain_alias_target(ctx)
            self.assertEqual( rp , "")
            mock_cf.exists = True
            mock_cf.existing = {'CustomDomain':'false'}
            rp = helper_functions.custom_domain_alias_target(ctx)
            self.assertEqual( rp , "")
            mock_cf.existing = {'CustomDomain':'true','AliasTarget':'foobar'}
            rp = helper_functions.custom_domain_alias_target(ctx)
            self.assertEqual( rp , "foobar")
            mock_cf.existing = {'CustomDomain':'true','AliasTarget':''}
            mock_cf.exports = {'OAuth-Domain':'foo.bar.com'}
            rp = helper_functions.custom_domain_alias_target(ctx)
            self.assertEqual( rp , "d8je8xsnt59o8.cloudfront.net")
        finally:
            helper_functions._get_cognito_client = get_cache
            helper_functions._get_cf_buddy = cf_cache
