import json
import os
import tempfile

# noinspection PyUnresolvedReferences
from infra_buddy.commandline import cli
from infra_buddy.commands.deploy_service import command as ds_command
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
        deploy_ctx = DeployContext.create_deploy_context(application="foo", role="bar", environment="unit-test",
                                                         defaults=self.default_config)
        self._validate_deploy_ctx(deploy_ctx)
        deploy_ctx = DeployContext.create_deploy_context(application="foo-bar", role="baz", environment="unit-test",
                                                         defaults=self.default_config)
        self.assertEqual(deploy_ctx.vpcapp, "foo", "Failed to generate generate_short_app_name")

    def test_s3_config_url_path(self):
        east_deploy_ctx = DeployContext.create_deploy_context(application="foo",
                                                              role="bar-{}".format(self.run_random_word),
                                                              environment="unit-test",
                                                              defaults=self.east_config)
        self.assertTrue("s3." in east_deploy_ctx.config_templates_url)
        test_deploy_ctx = DeployContext.create_deploy_context(application="foo",
                                                              role="bar-{}".format(self.run_random_word),
                                                              environment="unit-test",
                                                              defaults=self.default_config)
        self.assertTrue("s3-us-west-1." in test_deploy_ctx.config_templates_url)

    def _validate_deploy_ctx(self, deploy_ctx):
        # type: (DeployContext) -> None
        self.assertEqual(deploy_ctx.cf_bucket_name, "unit-test-foo-cloudformation-deploy-resources",
                         "Failed to generate CloudFormation bucket")
        self.assertEqual(deploy_ctx.cluster_stack_name, "unit-test-foo-cluster", "Failed to generate clustername")
        self.assertEqual(deploy_ctx.application, "foo", "Failed to generate application")
        self.assertEqual(deploy_ctx.role, "bar", "Failed to generate role")
        self.assertEqual(deploy_ctx.environment, "unit-test", "Failed to generate environment")
        self.assertEqual(deploy_ctx.region, "us-west-1", "Failed to generate region")
        self.assertEqual(deploy_ctx.key_name, "unit-test-foo", "Failed to generate keyname")
        self.assertEqual(deploy_ctx.generate_modification_resource_stack_name("snaf"),
                         "unit-test-foo-bar-snaf-resources",
                         "Failed to generate generate_modification_resource_stack_name")
        self.assertEqual(deploy_ctx.generate_modification_stack_name("snaf"), "unit-test-foo-bar-snaf",
                         "Failed to generate generate_modification_stack_name")
        self.assertEqual(deploy_ctx.vpcapp, "foo", "Failed to generate generate_short_app_name")
        self.assertEqual(deploy_ctx.stack_name, "unit-test-foo-bar", "Failed to generate generate_stack_name")
        self.assertEqual(deploy_ctx.resource_stack_name, "unit-test-foo-bar-resources",
                         "Failed to generate generate_resource_stack_name")
        self.assertEqual(deploy_ctx.vpc_stack_name, "unit-test-foo-vpc", "Failed to generate generate_stack_name")

    def test_default_configure(self):
        try:
            no_default_ctx = DeployContext.create_deploy_context(application="foo",
                                                                 role="bar",
                                                                 environment="unit-test")
            self.fail("Failed to generate error")
        except:
            pass
        default_ctx = self.test_deploy_ctx
        region = default_ctx.get_region()
        self.assertEqual(region, "us-west-1", "Failed to load from defaults")
        def_region = "us-west-1"
        os.environ.setdefault(REGION, def_region)
        try:
            no_default_ctx = DeployContext.create_deploy_context(application="foo",
                                                                 role="bar",
                                                                 environment="unit-test")
            region = no_default_ctx.get_region()
            self.assertEqual(region, def_region, "Failed to leverage environment variable")
        finally:
            del os.environ[REGION]

    def test_template_render(self):
        deploy_ctx = self.test_deploy_ctx
        render_file_test = self._get_resource_path('deploy_ctx_tests/test_render_file.json')
        mkdtemp = tempfile.mkdtemp()
        try:
            template = deploy_ctx.render_template(render_file_test, mkdtemp)
            expected = {
                "EnvName": "unit-test-foo-bar-{}".format(self.run_random_word),
                "Unknown": "${Unknown}",
                "Environment": "unit-test",
                "VPCStack": "unit-test-foo-vpc",
                "ClusterStack": "unit-test-foo-cluster",
                "DesiredCapacity": "\${DESIRED_CAPACITY}"
            }
            with open(template, 'r') as source:
                load = json.load(source)
                for val in load:
                    self.assertEqual(val["ParameterValue"], expected[val["ParameterKey"]], "Did not render template as "
                                                                                           "expected")
        finally:
            ParentTestCase.clean_dir(mkdtemp)

    def test_artifact_directory_error_handling(self):
        try:
            empty_artifact_directory = self._get_resource_path('artifact_directory_tests/empty_artifact_directory')
            err_ctx = DeployContext.create_deploy_context_artifact(artifact_directory=empty_artifact_directory,
                                                                   environment="unit-test")
            self.fail("Failed to generate error")
        except Exception as e:
            pass

    def test_artifact_directory_service_load(self):
        artifact_directory = self._get_resource_path('artifact_directory_tests/artifact_service_definition')
        deploy_ctx = DeployContext.create_deploy_context_artifact(artifact_directory=artifact_directory,
                                                                  environment="unit-test",
                                                                  defaults=self.default_config)
        self._validate_deploy_ctx(deploy_ctx)
        self.assertListEqual(deploy_ctx.get_service_modifications(), ['autoscale'],
                             "Failed to load service modifications")
        self.assertEqual(deploy_ctx.docker_registry_url, "https://docker.io/my-registry", "Failed to load registry-url")
        self.assertEqual(deploy_ctx.service_definition.service_template_definition_locations,
                         [{"type": "github", "owner": "rspitler", "repo": "cloudformation-templates"}],
                         "Failed to load remote configuration")

        self.assertEqual(deploy_ctx['API_PATH'], "bar", "Failed to load deployment parameters")
        self.assertIsNotNone(deploy_ctx.artifact_definition, "Failed to populate artifact definition")
        self.assertEqual(deploy_ctx.artifact_definition.artifact_id, "39",
                         "Failed to load artifact definition parameters")
        self.assertEqual(deploy_ctx.artifact_definition.artifact_location, "https://docker.io/my-registry/artifact",
                         "Failed to load artifact definition parameters")
        self.assertEqual(deploy_ctx.artifact_definition.artifact_type, "container",
                         "Failed to load artifact definition parameters")
        self.assertIsNotNone(deploy_ctx.service_definition, "Failed to populate service definition")

    def test_service_definition_env_params(self):
        artifact_directory = self._get_resource_path('artifact_directory_tests/artifact_service_definition')
        for env in ['unit-test', 'ci', 'prod']:
            deploy_ctx = DeployContext.create_deploy_context_artifact(artifact_directory=artifact_directory,
                                                                      environment=env,
                                                                      defaults=self.default_config)
            self.assertEqual(deploy_ctx['OVERRIDE'], "{}bar".format(env), "Failed to load {} value".format(env))
            self.assertEqual(deploy_ctx['API_PATH'], "bar", "Failed to load static value")

    def test_artifact_directory_execution_plan(self):
        artifact_directory = self._get_resource_path('artifact_directory_tests/artifact_execution_plan_test')
        deploy_ctx = DeployContext.create_deploy_context_artifact(artifact_directory=artifact_directory,
                                                                  environment="unit-test",
                                                                  defaults=self.default_config)
        plan = deploy_ctx.get_execution_plan()
        self.assertEqual(len(plan), 4, "Failed to identify all elements of execution - {}".format(plan))

    def test_deploy_validate(self):
        artifact_directory = self._get_resource_path('artifact_directory_tests/artifact_execution_plan_test')
        deploy_ctx = DeployContext.create_deploy_context_artifact(artifact_directory=artifact_directory,
                                                                  environment="unit-test",
                                                                  defaults=self.default_config)
        ds_command.do_command(deploy_ctx=deploy_ctx, dry_run=True)
