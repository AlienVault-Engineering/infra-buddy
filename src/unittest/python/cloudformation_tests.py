import json
import os
import random
import shutil
import string
import tempfile
import zipfile

from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.aws.s3 import S3Buddy, CloudFormationDeployS3Buddy
# noinspection PyUnresolvedReferences
from infra_buddy import commandline
from infra_buddy.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy.template.template import LocalTemplate
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
        s3 = CloudFormationDeployS3Buddy(self.test_deploy_ctx)
        temp_dir = tempfile.mkdtemp()
        try:
            template = ParentTestCase._get_resource_path("cloudformation/aws-resources.template")
            parameter_file = ParentTestCase._get_resource_path("cloudformation/aws-resources.parameters.json")
            self.test_deploy_ctx['RANDOM'] = self.randomWord(5)
            parameter_file_rendered = self.test_deploy_ctx.render_template(parameter_file,temp_dir)
            template_file_url = s3.upload(file=template)
            self.assertFalse(cloudformation.does_stack_exist(), "Failed to identify reality")
            cloudformation.create_stack(template_file_url=template_file_url,
                                        parameter_file=parameter_file_rendered)
            self.assertTrue(cloudformation.does_stack_exist(), "Failed to identify reality")
            self.assertEqual(cloudformation.get_stack_status(), "CREATE_COMPLETE", "Failed to identify create complete")
            cloudformation.create_change_set(template_file_url=template_file_url,
                                             parameter_file=parameter_file_rendered)
            self.assertFalse(cloudformation.should_execute_change_set(),"Failed to id noop changeset")
            cloudformation.delete_change_set()
            self.test_deploy_ctx['RANDOM'] = self.randomWord(5)
            parameter_file_rendered = self.test_deploy_ctx.render_template(parameter_file,temp_dir)
            cloudformation.create_change_set(template_file_url=template_file_url,
                                             parameter_file=parameter_file_rendered)
            self.assertEqual(cloudformation.get_change_set_status(refresh=True), "CREATE_COMPLETE",
                             "Did not get expected cs status")
            self.assertTrue(cloudformation.should_execute_change_set(),"Failed to id good changeset")
            if not cloudformation.should_execute_change_set():
                self.fail("Did not want to execute changeset")
            else:
                cloudformation.execute_change_set()
            cloudformation.log_stack_status()
        finally:
            super(CloudFormationTestCase, self).clean(cloudformation)
            super(CloudFormationTestCase, self).clean_s3(s3)
            super(CloudFormationTestCase, self).clean_dir(temp_dir)

    def test_cloudformation_deploy(self):
        template = ParentTestCase._get_resource_path("cloudformation/aws-resources.template")
        parameter_file = ParentTestCase._get_resource_path("cloudformation/aws-resources.parameters.json")
        config_templates = ParentTestCase._get_resource_path("cloudformation/config/")
        deploy = CloudFormationDeploy(self.test_deploy_ctx.stack_name, LocalTemplate(template, parameter_file, config_templates), self.test_deploy_ctx)
        deploy.do_deploy(dry_run=False)
        cloudformation = CloudFormationBuddy(self.test_deploy_ctx)
        s3 = CloudFormationDeployS3Buddy(self.test_deploy_ctx)
        try:
            self.assertTrue(cloudformation.does_stack_exist(), "Failed to create stack")
            self.assertEqual(s3.get_file_as_string("install_template.sh"),"foo-bar-{}".format(self.run_random_word),"Did not render config template")
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

    def test_lambda_package(self):
        lambda_package_dir = self._get_resource_path('lambda_package_tests/lambda')
        template = ParentTestCase._get_resource_path("cloudformation/aws-resources.template")
        parameter_file = ParentTestCase._get_resource_path("cloudformation/aws-resources.parameters.json")
        config_templates = ParentTestCase._get_resource_path("cloudformation/config/")
        self.test_deploy_ctx['Strict-Transport-Security'] = "foo"
        self.test_deploy_ctx['Content-Security-Policy'] = "foo"
        self.test_deploy_ctx['X-Frame-Options'] = "foo"
        self.test_deploy_ctx['X-XSS-Protection'] = "foo"
        self.test_deploy_ctx['X-Content-Type-Options'] = "foo"
        self.test_deploy_ctx['Referrer-Policy'] = "foo"
        deploy = CloudFormationDeploy(self.test_deploy_ctx.stack_name,
                                      LocalTemplate(template, parameter_file, config_templates,lambda_package_dir),
                                      self.test_deploy_ctx)
        mkdtemp = tempfile.mkdtemp()
        try:
            template = deploy.get_lambda_packages(self.test_deploy_ctx)
            self.assertEqual(1, len(template),"Failed to return a single package")
            zip_file = template[0]
            basename = os.path.basename(zip_file)
            self.assertEqual(basename, "security-headers.zip", "Did not render the right name")
            self.assertTrue(zipfile.is_zipfile(zip_file),"Did not compress function")
            shutil.unpack_archive(zip_file,mkdtemp)
            files = os.listdir(mkdtemp)
            self.assertEqual(len(files),1,"Did not find expected files")
            code = files[0]
            self.assertEqual(code,"index.js","Did not find rendered file")
            with open(os.path.join(mkdtemp,code), 'r') as source:
                for line in source:
                    self.assertFalse("${" in line,f"Found unrendered variable in source: {line}")
            self.assertEqual(self.test_deploy_ctx.get(f"security-headers-SHA256",None),
                             "fc72ddd698ceeb3df1f4db4aaba2beb4c3989d4bbce87d6aaf5ce882490d3c24",
                             "Did not populate SHA256 of function")
        finally:
            ParentTestCase.clean_dir(mkdtemp)

    def test_changeset_operation_ready(self):
        cloudformation = CloudFormationBuddy(self.test_deploy_ctx)
        try:
            cloudformation.describe_change_set()
            self.fail("Failed to throw error when not ready for decribe changeset")
        except:
            pass



