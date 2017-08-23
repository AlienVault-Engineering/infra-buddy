import click

from infra_buddy.commandline import cli
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.commands.deploy_cloudformation import command as deploy_cf


@cli.command(name='deploy-service')
@click.pass_obj
def deploy_cloudformation(deploy_ctx):
    # type: (DeployContext) -> None
    do_command(deploy_ctx)


def do_command(deploy_ctx):
    # type: (DeployContext) -> None
    plan = deploy_ctx.get_execution_plan()
    for deploy in plan:
        deploy_ctx.push_deploy_ctx(deploy)
        deploy_cf.do_command(deploy_ctx,
                             template=deploy.template_file,
                             parameter_file=deploy.parameter_file,
                             config_templates=deploy.config_directory)
        deploy_ctx.pop_deploy_ctx()
