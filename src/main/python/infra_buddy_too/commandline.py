import json
import os

import click

# [ --application <otxb>] [ --role <>] [ --environment <>]
from infra_buddy_too.context.deploy_ctx import DeployContext
from infra_buddy_too.utility import print_utility


@click.group()
@click.option("--artifact-directory",
              envvar='ARTIFACT_DIRECTORY',
              type=click.Path(exists=True),
              help='A directory where a service definition (service.json) and supporting files can be found.')
@click.option("--application", envvar='APPLICATION', help='The application name.')
@click.option("--role", envvar='ROLE', help='The role name')
@click.option("--environment", envvar='ENVIRONMENT', help='The environment the deployment should target.')
@click.option("--configuration-defaults", envvar='CONFIG_DEFAULTS', type=click.Path(exists=True),
              help='A json file with a dictionary of the default values, if defaults.json is in CWD it will be used.')
@click.option("--verbose", is_flag=True, help='Print verbose status messages')
@click.pass_context
def cli(ctx, artifact_directory, application, role, environment, configuration_defaults, verbose):
    # type: (object, str, str, str, str, str, bool) -> None
    """
    CLI for managing the infrastructure for deploying micro-services in AWS.
    """
    print_utility.configure(verbose)
    loaded_defaults = None
    # if a defaults.json exists in the directory and it is not overriden with an explicit parameter - use it!
    if not configuration_defaults and os.path.exists('defaults.json'):
        configuration_defaults = 'defaults.json'
    if configuration_defaults or os.path.exists('defaults.json'):
        print_utility.info("Loading default settings from path: {}".format(configuration_defaults))
        with open(configuration_defaults, 'r') as fp:
            loaded_defaults = json.load(fp)
    if artifact_directory:
        if application or role:
            raise click.UsageError("When specifying --artifact-directory do not provide --application or --role")
        ctx.obj = DeployContext.create_deploy_context_artifact(artifact_directory=artifact_directory,
                                                               environment=environment,
                                                               defaults=loaded_defaults)
    else:
        ctx.obj = DeployContext.create_deploy_context(application=application,
                                                      role=role,
                                                      environment=environment,
                                                      defaults=loaded_defaults)


# noinspection PyUnresolvedReferences
from infra_buddy_too.commands.deploy_cloudformation import command
# noinspection PyUnresolvedReferences
from infra_buddy_too.commands.deploy_service import command
# noinspection PyUnresolvedReferences
from infra_buddy_too.commands.validate_template import command
# noinspection PyUnresolvedReferences
from infra_buddy_too.commands.generate_artifact_manifest import command
# noinspection PyUnresolvedReferences
from infra_buddy_too.commands.generate_service_definition import command
# noinspection PyUnresolvedReferences
from infra_buddy_too.commands.bootstrap import command
# noinspection PyUnresolvedReferences
from infra_buddy_too.commands.introspect import command
