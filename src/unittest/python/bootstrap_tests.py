import tempfile

import boto3
import pydash
# noinspection PyUnresolvedReferences
from infra_buddy_too.commandline import cli
from infra_buddy_too.commands.bootstrap import command as bcommand
from testcase_parent import ParentTestCase
import unittest


class BootStrapTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(BootStrapTestCase, cls).setUpClass()

    def test_boostrap(self):
        environments = ['ci', 'prod']
        gen_keys = ["{env}-{app}".format(env=env,app=self.test_deploy_ctx.application) for env in environments]
        tempdir = tempfile.mkdtemp()
        bcommand.do_command(deploy_ctx=self.test_deploy_ctx, environments=environments,destination=tempdir)
        client = boto3.client('ec2',  region_name=self.test_deploy_ctx.region)
        try:
            res = client.describe_key_pairs()
            known = pydash.pluck(res['KeyPairs'], 'KeyName')
            for key in gen_keys:
                self.assertTrue(key in known,"Did not generate key - {}".format(key))
        finally:
            for gen_key in gen_keys:
                client.delete_key_pair(KeyName=gen_key)
            self.clean_dir(tempdir)


if __name__ == '__main__':
    unittest.main()