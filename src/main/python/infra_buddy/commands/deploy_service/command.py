import click

from infra_buddy.commandline import cli
from infra_buddy.context.deploy_ctx import DeployContext


@cli.command(name='deploy-service')
@click.pass_obj
def deploy_cloudformation(deploy_ctx):
    # type: (DeployContext) -> None
    do_command(deploy_ctx)


def do_command(deploy_ctx):
    # type: (DeployContext) -> None
    pass
