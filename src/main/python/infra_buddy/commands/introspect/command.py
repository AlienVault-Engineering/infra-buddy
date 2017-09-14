import os
from collections import defaultdict

import boto3
import click
from infra_buddy.aws.cloudformation import CloudFormationBuddy

from infra_buddy.commandline import cli
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy.template.template import NamedLocalTemplate
from infra_buddy.utility import print_utility


@cli.command(name='introspect', short_help="Search infra-buddy managed services for a resource.")
@click.option("--type-filter", help="Constrain search to a AWS resource type.")
@click.pass_obj
def deploy_cloudformation(deploy_ctx,type_filter):
    # type: (DeployContext,str) -> None
    do_command(deploy_ctx,type_filter)


def do_command(deploy_ctx,type_filter):
    # type: (DeployContext,str) -> None
    cf_buddy = CloudFormationBuddy(deploy_ctx=deploy_ctx)
    stacks = cf_buddy.list_stacks(deploy_ctx.stack_name)
    resources = cf_buddy.load_resources_for_stack_list(stacks)
    for stack_name, resources in resources.iteritems():
        print_utility.banner("Stack: {}".format(stack_name))
        for resource in resources:
            if not type_filter or type_filter in resource['ResourceType']:
                print_utility.info_banner("\tName: {}".format(resource['LogicalResourceId']))
                print_utility.info_banner("\tType: {}".format(resource['ResourceType']))

        
        




