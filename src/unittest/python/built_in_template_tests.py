from infra_buddy.commandline import cli
from infra_buddy.commands.validate_template import command as vcommand
from infra_buddy.template.template_manager import TemplateManager

from testcase_parent import ParentTestCase

class BuiltInTemplateTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_validate_built_in_templates(self):
        template_manager = TemplateManager()
        for key, value in template_manager.deploy_templates.items():
            try:
                vcommand.do_command(self.test_deploy_ctx,service_type=key)
            except:
                print("Errors in {}".format(key))

