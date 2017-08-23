import os
import tempfile

from infra_buddy.aws import s3
from infra_buddy.aws.s3 import S3Buddy
from testcase_parent import ParentTestCase


class S3TestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(S3TestCase, cls).setUpClass()

    def test_bucket_configuration(self):
        s3_buddy = S3Buddy(self.test_deploy_ctx)
        try:
            self.assertEqual(s3_buddy.s3_bucket_deploy_directory, self.test_deploy_ctx.cf_deploy_resource_path,
                             "Did not init correct path")
            self.assertEqual(s3_buddy.cf_bucket.name, self.test_deploy_ctx.cf_bucket_name,
                             "Did not init correct bucket")
            self.assertEqual(s3_buddy.url_base,
                             "https://s3-us-west-1.amazonaws.com/unit-test-foo-cloudformation-deploy-resources",
                             "Did not init correct url")
        finally:
            self.clean_s3(s3_buddy)
        
    def test_file_operations(self):
        s3_buddy = S3Buddy(self.test_deploy_ctx)
        try:
            changeset = ParentTestCase._get_resource_path("cloudformation/sample_changeset.json")
            s3_buddy.upload(changeset)
            with open(changeset,'r') as cs:
                change_set_string = cs.read()
                self.assertEqual(s3_buddy.get_file_as_string('sample_changeset.json'),change_set_string,"Failed to get file as string")
        finally:
            self.clean_s3(s3_buddy)

    def test_zip_download(self):
        s3_buddy = S3Buddy(self.test_deploy_ctx)
        compress = ParentTestCase._get_resource_path("test_compress.json.zip")
        s3_buddy.upload(compress)
        s3_url = "s3://{bucket}/{key}".format(bucket=self.test_deploy_ctx.cf_bucket_name,
                                                   key=s3_buddy._get_upload_bucket_key_name(file=None,
                                                                                            file_name="test_compress.json.zip"))
        temp_dir = tempfile.mkdtemp()
        test_file = os.path.join(temp_dir, "test_compress.json")
        try:
            s3.download_zip_from_s3_url(s3_url,temp_dir)
            self.assertTrue(os.path.exists(test_file), "Failed to decompress file")
        finally:
            self.clean_dir(temp_dir)
            self.clean_s3(s3_buddy)
