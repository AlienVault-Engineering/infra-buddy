import click

# [ --application <otxb>] [ --role <>] [ --environment <>]
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.utility import print_utility


@click.group()
@click.option("--artifact-directory",
              envvar='ARTIFACT_DIRECTORY',
              type=click.Path(exists=True),
              help='A directory where a service definition (service.json) and supporting files can be found.')
@click.option("--application", envvar='APPLICATION', help='The application name.')
@click.option("--role", envvar='ROLE', help='The role name')
@click.option("--environment", envvar='ENVIRONMENT', help='The environment the deployment should target.')
@click.option("--configuration-defaults", envvar='CONFIG_DEFAULTS', type=click.Path(exists=True),
              help='A json file with a dictionary of the default values')
@click.option("--verbose", is_flag=True, help='Print verbose status messages')
@click.pass_context
def cli(ctx, artifact_directory, application, role, environment, configuration_defaults, verbose):
    # type: (str, str, str, str, str, str, bool) -> None
    """

    :param ctx: click context
    :param artifact_directory: Path to directory containing deploy artifacts
    :param role: Role for service
    :param environment: Environment to deploy
    :param verbose: Print informational messages
    :param application: Application for service
    """
    print_utility.configure(verbose)
    if artifact_directory:
        if application or role:
            click.UsageError("When specifying --artifact-directory do not provide --application or --role")
        ctx.obj = DeployContext.create_deploy_context_artifact(artifact_directory=artifact_directory,
                                                               environment=environment,
                                                               defaults=configuration_defaults)
    else:
        ctx.obj = DeployContext.create_deploy_context(application=application,
                                                      role=role,
                                                      environment=environment,
                                                      defaults=configuration_defaults)


# noinspection PyUnresolvedReferences
from infra_buddy.commands.deploy_cloudformation import command
