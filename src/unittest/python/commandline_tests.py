import click

from click.testing import CliRunner
from infra_buddy.commandline import cli
from testcase_parent import ParentTestCase


@cli.command(name='test-command')
@click.pass_obj
def test_method(deploy_ctx):
    click.echo(deploy_ctx.stack_name)


class CommandlineTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(CommandlineTestCase, cls).setUpClass()

    def test_context_creation(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['--application', 'foo', '--role', 'bar', '--environment', 'dev',
                                     '--configuration-defaults', self.default_config, 'test-command'])
        self.assertEqual(result.output.strip(), 'dev-foo-bar', "Invocation for simple cli usage failed")

    def test_artifact_context_creation(self):
        artifact_directory = self._get_resource_path('artifact_directory_tests/artifact_service_definition')
        runner = CliRunner()
        result = runner.invoke(cli, ['--artifact-directory', artifact_directory, '--environment', 'dev',
                                     '--configuration-defaults', self.default_config, 'test-command'])
        self.assertEqual(result.output.strip(), 'dev-foo-bar', "Invocation for simple cli usage failed")

    def test_error_case(self):
        artifact_directory = self._get_resource_path('artifact_directory_tests/artifact_service_definition')
        runner = CliRunner()
        result = runner.invoke(cli,
                               ['--application', 'foo', '--artifact-directory', artifact_directory, '--environment',
                                'dev',
                                '--configuration-defaults', self.default_config, 'test-command'])
        self.assertEqual(result.exit_code, 2, "Failed to fail")
