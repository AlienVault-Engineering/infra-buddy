import json
import os

from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.context.deploy_ctx import REGION
from testcase_parent import ParentTestCase

DIRNAME = os.path.dirname(os.path.abspath(__file__))


class DeployContextTestCase(ParentTestCase):
    def tearDown(self):
        pass


    @classmethod
    def setUpClass(cls):
        super(DeployContextTestCase, cls).setUpClass()

    def test_string_render(self):
        deploy_ctx = self.test_deploy_ctx
        self.assertEqual(deploy_ctx.cf_bucket_name, "dev-foo-cloudformation-deploy-resources",
                         "Failed to generate CloudFormation bucket")
        self.assertEqual(deploy_ctx.cluster_stack_name, "dev-foo-cluster", "Failed to generate clustername")
        self.assertEqual(deploy_ctx.application, "foo", "Failed to generate application")
        self.assertEqual(deploy_ctx.role, "bar", "Failed to generate role")
        self.assertEqual(deploy_ctx.environment, "dev", "Failed to generate environment")
        self.assertEqual(deploy_ctx.region, "us-west-1", "Failed to generate region")
        self.assertEqual(deploy_ctx.key_name, "dev-foo", "Failed to generate keyname")
        self.assertEqual(deploy_ctx.generate_modification_resource_stack_name("snaf"), "dev-foo-bar-snaf-resources",
                         "Failed to generate generate_modification_resource_stack_name")
        self.assertEqual(deploy_ctx.generate_modification_stack_name("snaf"), "dev-foo-bar-snaf",
                         "Failed to generate generate_modification_stack_name")
        self.assertEqual(deploy_ctx.vpcapp, "foo", "Failed to generate generate_short_app_name")
        self.assertEqual(deploy_ctx.stack_name, "dev-foo-bar", "Failed to generate generate_stack_name")
        self.assertEqual(deploy_ctx.resource_stack_name, "dev-foo-bar-resources",
                         "Failed to generate generate_resource_stack_name")
        self.assertEqual(deploy_ctx.vpc_stack_name, "dev-foo-vpc", "Failed to generate generate_stack_name")
        deploy_ctx = DeployContext(application="foo-bar", role="baz", environment="dev", defaults=self.default_config)
        self.assertEqual(deploy_ctx.vpcapp, "foo", "Failed to generate generate_short_app_name")

    def test_default_configure(self):
        try:
            no_default_ctx = DeployContext(application="foo", role="bar", environment="dev", defaults=None)
            self.fail("Failed to generate error")
        except:
            pass
        default_ctx = self.test_deploy_ctx
        region = default_ctx.get_region()
        self.assertEqual(region, "us-west-1", "Failed to load from defaults")
        def_region = "us-west-1"
        os.environ.setdefault(REGION, def_region)
        try:
            no_default_ctx = DeployContext(application="foo", role="bar", environment="dev", defaults=None)
            region = no_default_ctx.get_region()
            self.assertEqual(region, def_region, "Failed to leverage environment variable")
        finally:
            del os.environ[REGION]

    def test_template_render(self):
        deploy_ctx = self.test_deploy_ctx
        render_file_test = os.path.join(DIRNAME, '../resources/test_render_file.json')
        template = deploy_ctx.render_template(render_file_test)
        expected = {
            "EnvName": "${EnvName}",
            "Environment": "dev",
            "VPCStack": "dev-foo-vpc",
            "ClusterStack": "dev-foo-cluster",
            "DesiredCapacity": "\${DESIRED_CAPACITY}"
        }
        with open(template, 'r') as source:
            load = json.load(source)
            for val in load:
                self.assertEqual(val["ParameterValue"], expected[val["ParameterKey"]], "Did not render template as "
                                                                                       "expected")
