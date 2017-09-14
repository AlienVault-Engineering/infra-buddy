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
    # type: (object, str, str, str, str, str, bool) -> None
    """
    CLI for managing the infrastructure for deploying micro-services in AWS.
    """
    print_utility.configure(verbose)
    if artifact_directory:
        if application or role:
            raise click.UsageError("When specifying --artifact-directory do not provide --application or --role")
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
# noinspection PyUnresolvedReferences
from infra_buddy.commands.deploy_service import command
# noinspection PyUnresolvedReferences
from infra_buddy.commands.validate_template import command
# noinspection PyUnresolvedReferences
from infra_buddy.commands.generate_artifact_manifest import command
# noinspection PyUnresolvedReferences
from infra_buddy.commands.generate_service_definition import command
# noinspection PyUnresolvedReferences
from infra_buddy.commands.bootstrap import command
# noinspection PyUnresolvedReferences
from infra_buddy.commands.introspect import command
