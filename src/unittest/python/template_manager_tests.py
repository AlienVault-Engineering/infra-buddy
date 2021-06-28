import os
import tempfile

from infra_buddy.template.template_manager import TemplateManager

from infra_buddy.aws.s3 import CloudFormationDeployS3Buddy
from infra_buddy.context.service_definition import ServiceDefinition
from infra_buddy.deploy.cloudformation_deploy import CloudFormationDeploy
from testcase_parent import ParentTestCase
# noinspection PyUnresolvedReferences
from infra_buddy.commandline import cli
from infra_buddy.commands.generate_service_definition import command as generate_command


class TemplateManagerTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(TemplateManagerTestCase, cls).setUpClass()

    def test_s3_template(self):
        s3 = CloudFormationDeployS3Buddy(self.test_deploy_ctx)
        template = ParentTestCase._get_resource_path("template_tests/test-template.zip")
        s3.upload(file=template)
        key = s3._get_upload_bucket_key_name(template, key_name=None)
        s3_url = "s3://{bucket}/{key}".format(bucket=self.test_deploy_ctx.cf_bucket_name, key=key)
        self._validate_template(self.test_deploy_ctx.template_manager, {"type": "s3", "location": s3_url})

    def _validate_template(self, manager, template_def, service_name="test-template", has_config_dir=True):
        manager._load_templates({service_name: template_def})
        template = manager.get_known_service(service_name)
        self.assertIsNotNone(template, "Failed to locate service")
        self.assertIsNotNone(template.get_template_file_path(), "Failed to locate template file")
        self.assertTrue(os.path.exists(template.get_template_file_path()), "Template does not exist in real life")
        self.assertIsNotNone(template.get_parameter_file_path(), "Failed to locate param file")
        self.assertTrue(os.path.exists(template.get_parameter_file_path()), "Param file does not exist in real life")
        if has_config_dir:
            self.assertIsNotNone(template.get_config_dir(), "Failed to locate config dir")

    def test_github_template(self):
        self._validate_template(self.test_deploy_ctx.template_manager,
                                service_name='vpc',
                                has_config_dir=False,
                                template_def={
                                    "type": "github",
                                    "owner": "AlienVault-Engineering",
                                    "repo": "infra-buddy-vpc"
                                })

    def test_github_relative_path_template(self):
        self._validate_template(self.test_deploy_ctx.template_manager,
                                service_name='vpc',
                                has_config_dir=False,
                                template_def={
                                    "type": "github",
                                    "owner": "rspitler",
                                    "repo": "cloudformation-templates",
                                    "relative-path": "vpc"
                                })

    def test_invalid_github_template(self):
        try:
            self.test_deploy_ctx.template_manager._load_templates({'vpc': {
                "type": "github",
                "owner": "AlienVault-Engineering-Fail",
                "repo": "infra-buddy-vpc"
            }})
            template = self.test_deploy_ctx.template_manager.get_known_service('vpc')
            self.fail("Did not error on bad github template")
        except:
            pass

    def test_invalid_template(self):
        template = self.test_deploy_ctx.template_manager.get_resource_service(
            ParentTestCase._get_resource_path("template_tests/invalid_template"))
        self.assertIsNone(template, "Failed to return none for invalid template")
        template = self.test_deploy_ctx.template_manager.get_resource_service(
            ParentTestCase._get_resource_path("template_tests/valid_template"))
        self.assertIsNotNone(template, "Failed to return deploy for valid template")

    def test_validate_defaults(self):
        template = self.test_deploy_ctx.template_manager.get_resource_service(
            ParentTestCase._get_resource_path("template_tests/valid_template"))
        deploy = CloudFormationDeploy(stack_name=self.test_deploy_ctx.resource_stack_name,
                                      template=template,
                                      deploy_ctx=self.test_deploy_ctx)
        self.assertEqual(deploy.defaults['app'], "foo-with-string", "Failed to render template value")
        self.assertEqual(deploy.defaults['val'], "discrete", "Failed to render template value")
        self.assertEqual(self.test_deploy_ctx.expandvars("${KEY_NAME}"), "unit-test-foo",
                         "Failed to render expected key value")
        self.test_deploy_ctx.push_deploy_ctx(deploy)
        self.assertEqual(self.test_deploy_ctx.stack_name, "unit-test-foo-bar-{}-resources".format(self.run_random_word),
                         "Failed to update stack_name")
        self.assertEqual(self.test_deploy_ctx.expandvars("${app}"), "foo-with-string",
                         "Failed to render deploy default")
        self.assertEqual(self.test_deploy_ctx.expandvars("${KEY_NAME}"), "override", "Failed to render deploy default")
        self.assertEqual(self.test_deploy_ctx.expandvars("${KEY_NAME_2}"), "foo",
                         "Failed to render deploy default template")
        self.test_deploy_ctx.pop_deploy_ctx()
        self.assertEqual(self.test_deploy_ctx.stack_name, "unit-test-foo-bar-{}".format(self.run_random_word),
                         "Failed to update stack_name after pop")
        self.assertEqual(self.test_deploy_ctx.expandvars("${KEY_NAME}"), "unit-test-foo",
                         "Failed to render expected key value after pop")

    def test_validate_service_definition_generation(self):
        tempdir = tempfile.mkdtemp()
        try:
            generated = generate_command.do_command(self.test_deploy_ctx, service_template_directory=None,
                                                    service_type="cluster", destination=tempdir)
            definition = ServiceDefinition(artifact_directory=os.path.dirname(generated), environment="dev")
            self.assertIsNotNone(definition, "Failed to load service definition")
            self.assertEqual(definition.service_type, "cluster", "Did not do a good job")
            self.assertEqual(definition.application, self.test_deploy_ctx.application,
                             "Did not do a good job --application")
            self.assertEqual(definition.role, self.test_deploy_ctx.role, "Did not do a good job --role")
            self.assertTrue(os.path.exists(os.path.join(os.path.dirname(generated), "README.md")),
                            "Did not generate readme.md")
        finally:
            self.clean_dir(tempdir)

    def test_service_mod_load(self):
        template_manager = TemplateManager()
        self.assertTrue(template_manager.get_known_template('cluster'), "Failed to locate known template")
        self.assertTrue(template_manager.get_known_service_modification("foo", 'rds-aurora'),
                        "Failed to locate wildcard service mod template")
        self.assertTrue(template_manager.get_known_service_modification("batch-service", 'autoscale'),
                        "Failed to locate multi type service mod template")
        self.assertTrue(template_manager.get_known_service_modification("ecs-service", 'autoscale'),
                        "Failed to locate multi type service mod template")
        self.assertTrue(template_manager.get_known_service_modification("api-service", 'autoscale'),
                        "Failed to locate multi type service mod template")
        self.assertTrue(template_manager.get_known_service_modification("default-api-service", 'autoscale'),
                        "Failed to locate multi type service mod template")
        self.assertTrue(template_manager.get_known_template('autoscale'),
                        "Failed to locate known template mod template")
        self.assertTrue(template_manager.get_known_template('cluster'),
                        "Failed to locate wildcard service mod template")

    def test_service_mod_defaults_load(self):
        template_manager = TemplateManager(user_default_service_modification_tempaltes={
            "secret": {
                "type": "github",
                "owner": "rspitler",
                "repo": "cloudformation-templates",
                "tag": "master/secret",
                "compatible": [
                    "*"
                ]
            }
        })
        self.assertTrue(template_manager.get_known_template('secret'), "Failed to locate default template")

    def test_remote_defaults_load(self):
        template_manager = TemplateManager()
        template_manager.load_additional_templates({"type":"github","owner":"rspitler","repo":"cloudformation-templates"})
        self.assertTrue(template_manager.get_known_template('secret'), "Failed to locate default template")

    def test_service_alias(self):
        template_manager = TemplateManager()
        template = template_manager.get_known_template('default-api-service')
        self.assertTrue(template, "Failed to locate alias template")
        self.assertTrue(template.delegate, "Failed to locate alias template delegate")
        self.assertEquals(template.lookup, 'ecs-service', "Failed to locate ecs-service template delegate")
        deploy = CloudFormationDeploy("foo", template, deploy_ctx=self.test_deploy_ctx)
        self.assertTrue(deploy.defaults['DEFAULT_LOAD_BALANCER_TARGET'], "Did not populate expect default variables")
        template = template_manager.get_known_template('api-service')
        self.assertTrue(template, "Failed to locate alias template")
        self.assertTrue(template.delegate, "Failed to locate alias template delegate")
        self.assertEquals(template.lookup, 'ecs-service', "Failed to locate ecs-service template delegate")
        deploy = CloudFormationDeploy("foo", template, deploy_ctx=self.test_deploy_ctx)
        self.assertTrue(deploy.defaults['CREATE_API'], "Did not populate expect default variables")
