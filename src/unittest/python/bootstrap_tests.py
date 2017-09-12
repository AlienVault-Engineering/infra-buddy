import boto3
import pydash
# noinspection PyUnresolvedReferences
from infra_buddy.commandline import cli
from infra_buddy.commands.bootstrap import command   as bcommand
from testcase_parent import ParentTestCase


class BootStrapTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(BootStrapTestCase, cls).setUpClass()

    def test_boostrap(self):
        environments = ['ci', 'prod']
        gen_keys = ["{env}-{app}".format(env=env,app='testapp') for env in environments]
        bcommand.do_command("testapp", environments)
        client = boto3.client('ec2')
        try:
            res = client.describe_key_pairs()
            known = pydash.pluck(res['KeyPairs'],'KeyName')
            for key in gen_keys:
                self.assertTrue(key in known,"Did not generate key - {}".format(key))
        finally:
            for gen_key in gen_keys:
                client.delete_key_pair(KeyName=gen_key)
