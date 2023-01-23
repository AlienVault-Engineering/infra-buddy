import json

import click

from click.testing import CliRunner
from infra_buddy_too.commandline import cli
from testcase_parent import ParentTestCase


@cli.command(name='test-command')
@click.pass_obj
def test_method(deploy_ctx):
    click.echo(deploy_ctx.stack_name)

@cli.command(name='env-echo')
@click.pass_obj
def env_echo(deploy_ctx):
    click.echo(deploy_ctx['TEST'])


class CommandlineTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(CommandlineTestCase, cls).setUpClass()

    def test_context_creation(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['--application', 'foo', '--role', 'bar', '--environment', 'unit-test',
                                     '--configuration-defaults', self.default_config_path, 'test-command'])
        self.assertEqual(result.output.strip(), 'unit-test-foo-bar', "Invocation for simple cli usage failed")

    def test_defaults_load(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("defaults.json", 'w') as fp:
                json.dump({"TEST":"blazes"}, fp)
            result = runner.invoke(cli, ['--application', 'foo', '--role', 'bar', '--environment', 'unit-test', 'env-echo'])
        self.assertTrue('blazes' in result.output.strip() , "Invocation for default loading of defaults.json")

    def test_artifact_context_creation(self):
        artifact_directory = self._get_resource_path('artifact_directory_tests/artifact_service_definition')
        runner = CliRunner()
        result = runner.invoke(cli, ['--artifact-directory', artifact_directory, '--environment', 'unit-test',
                                     '--configuration-defaults', self.default_config_path, 'test-command'])
        self.assertEqual(result.output.strip(), 'unit-test-foo-bar', "Invocation for simple cli usage failed")

    def test_error_case(self):
        artifact_directory = self._get_resource_path('artifact_directory_tests/artifact_service_definition')
        runner = CliRunner()
        result = runner.invoke(cli,
                               ['--application', 'foo', '--artifact-directory', artifact_directory, '--environment',
                                'unit-test',
                                '--configuration-defaults', self.default_config_path, 'test-command'])
        self.assertEqual(result.exit_code, 2, "Failed to fail")

    def test_template_validate(self):
        runner = CliRunner()
        result = runner.invoke(cli,[ 'validate-template' , "--service-type","cluster"])
        self.assertEqual(result.exit_code, 0, "Failed ")
        self.assertTrue("SUCCESS" in result.output, "Did not validate ")
