import click
from infra_buddy.utility import print_utility

from infra_buddy.aws.ecs import ECSBuddy
from infra_buddy.commandline import cli
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.commands.deploy_cloudformation import command as deploy_cf


@cli.command(name='deploy-service')
@click.option("--validate", is_flag=True, help="Prints the execution plan and displays the evaluated "
                                               "parameter values for the deployment.")
@click.option("--ecs-deploy", is_flag=True, help="Run an update of the ECS service outside the cloudformation update. "
                                                 "(Necessary if the only update is the container image)")
@click.pass_obj
def deploy_cloudformation(deploy_ctx,validate,ecs_deploy):
    # type: (DeployContext,bool) -> None
    do_command(deploy_ctx,validate,ecs_deploy)


def do_command(deploy_ctx, validate, ecs_deploy):
    # type: (DeployContext,bool) -> None
    plan = deploy_ctx.get_execution_plan()
    if validate:
        deploy_ctx.print_self()
    for deploy in plan:
        deploy_ctx.push_deploy_ctx(deploy)
        if validate:
            deploy.validate(deploy_ctx)
        else:
            deploy_cf.do_command(deploy_ctx, deploy)
        deploy_ctx.pop_deploy_ctx()
    if ecs_deploy:
        ecs_buddy = ECSBuddy(deploy_ctx)
        if ecs_buddy.requires_update():
            ecs_buddy.perform_update()
        else:
            print_utility.info("ECS using passed image - {}".format(deploy_ctx["IMAGE"]))