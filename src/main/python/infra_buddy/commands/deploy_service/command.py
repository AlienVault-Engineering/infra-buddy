import click

from infra_buddy.commandline import cli


@cli.command(name='deploy-service')
@click.pass_obj
def deploy_cloudformation(deploy_ctx):
    do_command(deploy_ctx)




def do_command(deploy_ctx):
    pass