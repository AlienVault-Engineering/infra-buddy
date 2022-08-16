import json
import os
import tempfile

from infra_buddy_too.aws import s3
from infra_buddy_too.aws.cloudformation import CloudFormationBuddy
from infra_buddy_too.aws.cloudwatch_logs import CloudwatchLogsBuddy
from infra_buddy_too.aws.s3 import S3Buddy
from infra_buddy_too.commandline import cli
from infra_buddy_too.context.deploy_ctx import DeployContext
from infra_buddy_too.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy_too.template.template import NamedLocalTemplate
from infra_buddy_too.utility import helper_functions
from testcase_parent import ParentTestCase




class CloudwatchLogsTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(CloudwatchLogsTestCase, cls).setUpClass()


    def test_print_latest(self):
        ctx = DeployContext.create_deploy_context(application="nudge-frontend".format(self.run_random_word), role="database-maintenance",
                                                  environment="ci",
                                                  defaults=self.default_config)
        ctx['REGION'] = "us-east-1"
        cw = CloudwatchLogsBuddy(ctx)
        try:
            cw.print_latest()
        finally:
            pass
