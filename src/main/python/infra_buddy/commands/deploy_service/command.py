import click
import time

import datetime

from infra_buddy.commandline import cli
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.utility import print_utility

current_milli_time = lambda: int(round(time.time() * 1000))


@cli.command(name='deploy-service', short_help="Deploy and/or update a service as defined by a service definition "
                                               "and an optional artifact definition.  Operation is idempotent.")
@click.option("--dry-run", is_flag=True, help="Prints the execution plan and displays the evaluated "
                                              "parameter values for the deployment.")
@click.pass_obj
def deploy_cloudformation(deploy_ctx, dry_run):
    # type: (DeployContext,bool) -> None
    do_command(deploy_ctx, dry_run)

def do_command(deploy_ctx, dry_run):
    # type: (DeployContext,bool) -> None
    plan = deploy_ctx.get_execution_plan()
    for deploy in plan:
        start = current_milli_time()
        print_utility.progress("Starting Deployment: {}".format(str(deploy)))
        deploy.do_deploy(dry_run)
        print_utility.progress("Finished Deployment in {} ".format(
            print_utility.print_time_delta(datetime.timedelta(milliseconds=(current_milli_time() - start)))))
