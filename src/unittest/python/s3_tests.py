import os
import tempfile

from infra_buddy.context.deploy_ctx import DeployContext

from infra_buddy.aws import s3
from infra_buddy.aws.s3 import S3Buddy, CloudFormationDeployS3Buddy
from infra_buddy.deploy.s3_deploy import S3Deploy
from testcase_parent import ParentTestCase


class TestCloudFormationBuddy(object):

    def __init__(self, deploy_ctx):
        super(TestCloudFormationBuddy, self).__init__()
        self.ctx = deploy_ctx


    def get_export_value(self,param):
        return "{bucket_name}/{root_path}".format(root_path=self.ctx.cf_deploy_resource_path,
                                                  bucket_name=self.ctx.cf_bucket_name)


class S3TestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(S3TestCase, cls).setUpClass()

    def test_bucket_configuration(self):
        self._validate_s3(self.test_deploy_ctx)

    def test_bucket_configuration_us_east_1(self):
        test_deploy_ctx = DeployContext.create_deploy_context(application="foo", role="bar-{}".format(self.run_random_word), environment="unit-test",
                                            defaults=self.east_config)
        self._validate_s3(test_deploy_ctx)

    def _validate_s3(self, deploy_ctx):
        s3_buddy = CloudFormationDeployS3Buddy(deploy_ctx)
        try:
            self.assertEqual(s3_buddy.key_root_path, self.test_deploy_ctx.cf_deploy_resource_path,
                             "Did not init correct path")
            self.assertEqual(s3_buddy.bucket.name, self.test_deploy_ctx.cf_bucket_name,
                             "Did not init correct bucket")
            if deploy_ctx.region == 'us-east-1':
                base = 's3'
            else:
                base ="s3-{}".format(deploy_ctx.region)
            self.assertEqual(s3_buddy.url_base,
                             "https://{}.amazonaws.com/unit-test-foo-cloudformation-deploy-resources".format(
                                 base),
                             "Did not init correct url")
        finally:
            self.clean_s3(s3_buddy)

    def test_file_operations(self):

        s3_buddy = CloudFormationDeployS3Buddy(self.test_deploy_ctx)
        try:
            changeset = ParentTestCase._get_resource_path("cloudformation/sample_changeset.json")
            s3_buddy.upload(changeset)
            with open(changeset,'r') as cs:
                change_set_string = cs.read()
                self.assertEqual(s3_buddy.get_file_as_string('sample_changeset.json'),change_set_string,"Failed to get file as string")
            self.assertEqual(s3_buddy._get_s3_object('sample_changeset.json')['ContentType'],'application/json',"Did not persist correct content type")
        finally:
            self.clean_s3(s3_buddy)

    def test_zip_download(self):
        s3_buddy = CloudFormationDeployS3Buddy(self.test_deploy_ctx)
        compress = ParentTestCase._get_resource_path("s3_tests/test_compress.json.zip")
        s3_buddy.upload(compress)
        s3_url = "s3://{bucket}/{key}".format(bucket=self.test_deploy_ctx.cf_bucket_name,
                                              key=s3_buddy._get_upload_bucket_key_name(file=None,
                                                                                       key_name="test_compress.json.zip"))
        temp_dir = tempfile.mkdtemp()
        test_file = os.path.join(temp_dir, "test_compress.json")
        try:
            s3.download_zip_from_s3_url(s3_url,temp_dir)
            self.assertTrue(os.path.exists(test_file), "Failed to decompress file")
        finally:
            self.clean_dir(temp_dir)
            self.clean_s3(s3_buddy)

    def test_s3_deploy(self):
        s3_buddy = CloudFormationDeployS3Buddy(self.test_deploy_ctx)
        try:
            compress = ParentTestCase._get_resource_path("s3_tests/test_compress.json.zip")
            s3_buddy.upload(compress)
            s3_url = "{bucket}/{key}".format(bucket=self.test_deploy_ctx.cf_bucket_name,
                                                  key=s3_buddy._get_upload_bucket_key_name(file=None,
                                                                                                   key_name="test_compress.json.zip"))
            # s3 deploy appends zip to it
            s3d = S3Deploy(artifact_id="test_compress.json",location=s3_url[:s3_url.rfind("/")],ctx=self.test_deploy_ctx)
            s3d.cloud_formation_buddy = TestCloudFormationBuddy(self.test_deploy_ctx)
            s3d.do_deploy()
            self.assertEqual(s3_buddy.get_file_as_string('test_compress.json'),"test-compress","Failed to get file as string")
        finally:
            self.clean_s3(s3_buddy)

