import json
import os
import random
import string
import unittest

import boto3

from infra_buddy_too.context.deploy_ctx import DeployContext
from infra_buddy_too.utility import print_utility

DIRNAME = os.path.dirname(os.path.abspath(__file__))
RESOURCE_DIR = os.path.abspath(os.path.join(DIRNAME, '../resources/'))


def load_path_as_json(path):
    with open(path) as fp:
        return json.load(fp)


class ParentTestCase(unittest.TestCase):
    def tearDown(self):
        pass

    def assertEqual(self, first, second, msg=None):
        msg = "{msg} - actual: {first} expected: {second}".format(msg=msg, first=first, second=second)
        super().assertEqual(first, second, msg)

    @classmethod
    def setUpClass(cls):
        super(ParentTestCase, cls).setUpClass()
        cls.resource_directory = RESOURCE_DIR
        cls.run_random_word = cls.randomWord(5)
        cls.default_config_path = ParentTestCase._get_resource_path('default_config.json')
        cls.default_config = load_path_as_json(ParentTestCase._get_resource_path('default_config.json'))
        cls.east_config = load_path_as_json(ParentTestCase._get_resource_path('east_config.json'))
        cls.test_deploy_ctx = DeployContext.create_deploy_context(application="foo", role="bar-{}".format(cls.run_random_word), environment="unit-test",
                                            defaults=cls.default_config)
        print_utility.configure(False)

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
    def clean_dir(cls, directory):
        try:
            for file in os.listdir(directory):
                os.remove(os.path.join(directory, file))
            os.removedirs(directory)
        except Exception as e:
            print('Error cleaning up ' + str(e))

    @classmethod
    def randomWord(cls, param):
        return ''.join(random.choice(string.ascii_lowercase) for i in range(param))
