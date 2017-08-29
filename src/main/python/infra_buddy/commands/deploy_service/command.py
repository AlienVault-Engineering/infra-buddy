import click
from infra_buddy.utility import print_utility

from infra_buddy.aws.ecs import ECSBuddy
from infra_buddy.commandline import cli
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.commands.deploy_cloudformation import command as deploy_cf


@cli.command(name='deploy-service')
@click.option("--dry-run", is_flag=True, help="Prints the execution plan and displays the evaluated "
                                               "parameter values for the deployment.")
@click.pass_obj
def deploy_cloudformation(deploy_ctx,dry_run):
    # type: (DeployContext,bool) -> None
    do_command(deploy_ctx,dry_run)


def do_command(deploy_ctx, dry_run):
    # type: (DeployContext,bool) -> None
    plan = deploy_ctx.get_execution_plan()
    for deploy in plan:
        deploy.do_deploy(dry_run)
