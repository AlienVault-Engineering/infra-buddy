import os
import unittest

import boto3

from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.utility import print_utility

DIRNAME = os.path.dirname(os.path.abspath(__file__))
RESOURCE_DIR = os.path.abspath(os.path.join(DIRNAME, '../resources/'))


class ParentTestCase(unittest.TestCase):
    def tearDown(self):
        pass

    def assertEqual(self, first, second, msg=None):
        msg = "{msg} - actual: {first} expected: {second}".format(msg=msg, first=first, second=second)
        super(ParentTestCase, self).assertEqual(first, second, msg)

    @classmethod
    def setUpClass(cls):
        super(ParentTestCase, cls).setUpClass()
        cls.resource_directory = RESOURCE_DIR
        config = 'default_config.json'
        cls.default_config = ParentTestCase._get_resource_path(config)
        cls.test_deploy_ctx = DeployContext.create_deploy_context(application="foo", role="bar", environment="unit-test",
                                            defaults=cls.default_config)
        print_utility.configure(True)

    @classmethod
    def _get_resource_path(cls, config):
        return os.path.join(RESOURCE_DIR, config)

    def clean(self, cloudformation):
        if cloudformation.stack_id is not None or cloudformation.does_stack_exist():
            print_utility.info("Starting stack cleanup - {}".format(cloudformation.stack_id))
            cloudformation.client.delete_stack(StackName=cloudformation.stack_name)
            waiter = cloudformation.client.get_waiter('stack_delete_complete')
            waiter.wait( StackName=cloudformation.stack_id)
            print_utility.info("Finishing stack cleanup - {}".format(cloudformation.stack_id))
        elif cloudformation.existing_change_set_id is not None:
            cloudformation.delete_change_set()

    def clean_s3(self, s3_buddy):
        if self._bucket_exists(s3_buddy):
            s3_buddy.cf_bucket.objects.all().delete()
            s3_buddy.cf_bucket.delete()

    def _bucket_exists(self, s3_buddy):
        try:
            boto3.client('s3', region_name=s3_buddy.deploy_ctx.region).head_bucket(s3_buddy.deploy_ctx.cf_bucket_name)
            return True
        except:
            return False

    @classmethod
    def clean_dir(cls, director):
        try:
            for file in os.listdir(director):
                os.remove(file)
            os.removedirs(director)
        except Exception as e:
            print 'Error cleaning up '+ e.message
