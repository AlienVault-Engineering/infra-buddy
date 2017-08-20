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
        self.assertEqual(s3_buddy.s3_bucket_deploy_directory, self.test_deploy_ctx.cf_deploy_resource_path,
                         "Did not init correct path")
        self.assertEqual(s3_buddy.cf_bucket.name, self.test_deploy_ctx.cf_bucket_name,
                         "Did not init correct bucket")
        self.assertEqual(s3_buddy.url_base,
                         "https://s3-us-west-1.amazonaws.com/dev-foo-cloudformation-deploy-resources",
                         "Did not init correct url")
        
    def test_file_operations(self):
        s3_buddy = S3Buddy(self.test_deploy_ctx)
        changeset = ParentTestCase._get_resource_path("cloudformation/sample_changeset.json")
        s3_buddy.upload(changeset)
        with open(changeset,'r') as cs:
            change_set_string = cs.read()
            self.assertEqual(s3_buddy.get_file_as_string('sample_changeset.json'),change_set_string,"Failed to get file as string")
