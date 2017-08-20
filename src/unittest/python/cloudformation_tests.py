import json
import random
import string

from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.aws.s3 import S3Buddy
from infra_buddy.commands.deploy_cloudformation import command
from infra_buddy.utility.exception import NOOPException
from testcase_parent import ParentTestCase


class CloudFormationTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(CloudFormationTestCase, cls).setUpClass()

    def test_cloudformation_create_and_update(self):
        cloudformation = CloudFormationBuddy(self.test_deploy_ctx)
        s3 = S3Buddy(self.test_deploy_ctx)
        try:
            template = ParentTestCase._get_resource_path("cloudformation/aws-resources.template")
            parameter_file = ParentTestCase._get_resource_path("cloudformation/aws-resources.parameters.json")
            self.test_deploy_ctx['RANDOM'] = ''.join(random.choice(string.lowercase) for i in range(5))
            parameter_file_rendered = self.test_deploy_ctx.render_template(parameter_file)
            template_file_url = s3.upload(file=template)
            self.assertFalse(cloudformation.does_stack_exist(), "Failed to identify reality")
            cloudformation.create_stack(template_file_url=template_file_url,
                                        parameter_file=parameter_file_rendered)
            self.assertTrue(cloudformation.does_stack_exist(), "Failed to identify reality")
            self.assertEqual(cloudformation.get_stack_status(), "CREATE_COMPLETE", "Failed to identify create complete")
            try:
                cloudformation.create_change_set(template_file_url=template_file_url,
                                                 parameter_file=parameter_file_rendered)
                self.fail("Failed to identify noop changeset")
            except NOOPException as noop:
                pass
            self.test_deploy_ctx['RANDOM'] = ''.join(random.choice(string.lowercase) for i in range(5))
            parameter_file_rendered = self.test_deploy_ctx.render_template(parameter_file)
            try:
                cloudformation.create_change_set(template_file_url=template_file_url,
                                                 parameter_file=parameter_file_rendered)
                self.assertEqual(cloudformation.get_change_set_status(refresh=True), "CREATE_COMPLETE",
                                 "Did not get expected cs status")
            except NOOPException as noop:
                self.fail("Failed to identify updated changeset")
            if not cloudformation.should_execute_change_set():
                self.fail("Did not want to execute changeset")
            else:
                cloudformation.execute_change_set()
            cloudformation.log_stack_status()
        finally:
            super(CloudFormationTestCase, self).clean(cloudformation)
            super(CloudFormationTestCase, self).clean_s3(s3)

    def test_cloudformation_deploy(self):
        template = ParentTestCase._get_resource_path("cloudformation/aws-resources.template")
        parameter_file = ParentTestCase._get_resource_path("cloudformation/aws-resources.parameters.json")
        config_templates = ParentTestCase._get_resource_path("cloudformation/config/")
        command.do_command(self.test_deploy_ctx, template=template, parameter_file=parameter_file,
                                      config_templates=config_templates)
        cloudformation = CloudFormationBuddy(self.test_deploy_ctx)
        s3 = S3Buddy(self.test_deploy_ctx)
        try:
            self.assertTrue(cloudformation.does_stack_exist(), "Failed to create stack")
            self.assertEqual(s3.get_file_as_string("install_template.sh"),"foo-bar","Did not render config template")
        finally:
            super(CloudFormationTestCase, self).clean(cloudformation)
            super(CloudFormationTestCase, self).clean_s3(s3)

    def test_skip_ecs_changeset(self):
        changeset = ParentTestCase._get_resource_path("cloudformation/sample_changeset.json")
        cloudformation = CloudFormationBuddy(self.test_deploy_ctx)
        with open(changeset, 'r') as cs:
            cloudformation.change_set_description = json.load(cs)
            cloudformation.existing_change_set_id = cloudformation.change_set_description['ChangeSetId']
        self.assertFalse(cloudformation.should_execute_change_set(),"Failed to skip ecs special case")

    def test_changeset_operation_ready(self):
        cloudformation = CloudFormationBuddy(self.test_deploy_ctx)
        try:
            cloudformation.describe_change_set()
            self.fail("Failed to throw error when not ready for decribe changeset")
        except:
            pass



