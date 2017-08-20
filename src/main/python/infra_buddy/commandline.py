import click

# [ --application <otxb>] [ --role <>] [ --environment <>]
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.utility import print_utility


@click.group()
@click.option("--artifact-directory", envvar='ARTIFACT_DIRECTORY', help='The application name.')
@click.option("--application", envvar='APPLICATION', help='The application name.')
@click.option("--role", envvar='ROLE', help='The role name')
@click.option("--environment", envvar='ENVIRONMENT', help='The environment the deployment should target.')
@click.option("--configuration-defaults", envvar='CONFIG_DEFAULTS', type=click.Path(exists=True),
              help='A json file with a dictionary of the default values')
@click.option("--verbose", is_flag=True, help='Print verbose status messages')
@click.pass_context
def cli(ctx, application, role, environment, configuration_defaults, verbose):
    ctx.obj = DeployContext(application, role, environment, configuration_defaults)
    print_utility.configure(verbose)


# noinspection PyUnresolvedReferences
from infra_buddy.commands.deploy_cloudformation import command
