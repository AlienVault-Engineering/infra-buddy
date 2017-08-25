import os
import tempfile

from infra_buddy.commandline import cli
from infra_buddy.commands.validate_template import command   as vcommand
from infra_buddy.context.deploy import Deploy
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.context.template import LocalTemplate, NamedLocalTemplate
from infra_buddy.context.template_manager import TemplateManager
from infra_buddy.utility import helper_functions
from testcase_parent import ParentTestCase


class BuilInTemplateTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(BuilInTemplateTestCase, cls).setUpClass()

    def test_validate_built_in_templates(self):
        template_manager = TemplateManager()
        for key,value in template_manager.deploy_templates.iteritems():
            try:
                vcommand.do_command(self.test_deploy_ctx,service_type=key)
            except:
                print "Errors in {}".format(key)
