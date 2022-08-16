import json
import os

import boto3
import click
from click import UsageError

from infra_buddy.commandline import cli
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy.template.template import NamedLocalTemplate
from infra_buddy.utility import print_utility


@cli.command(name='bootstrap', short_help="Generate keys for a new environment to be managed by infra-buddy.")
@click.argument('environments', nargs=-1)
@click.pass_obj
def deploy_cloudformation(deploy_ctx, environments):
    # type: (DeployContext,list) -> None
    do_command(deploy_ctx, environments)


def do_command(deploy_ctx, environments, destination=None):
    # type: (DeployContext,list) -> None
    client = boto3.client('ec2', region_name=deploy_ctx.region)
    if len(environments) == 0:
        raise UsageError("Expected at least one environment (ci, prod)")
    for env in environments:
        key_name = "{env}-{application}".format(env=env, application=deploy_ctx.application)
        res = client.create_key_pair(KeyName=key_name)
        key_location = '{key_name}.pem'.format(key_name=key_name)
        if destination:
            key_location = os.path.join(destination, key_location)
        with open(key_location, 'w') as new_pem:
            new_pem.writelines(res['KeyMaterial'])
    def_obj = {
        'service-templates': {},
        'service-modification-templates': {}
    }
    defaults = "defaults.json"
    if destination:
        defaults = os.path.join(destination, defaults)
    with open(defaults, 'w') as default_file:
        json.dump(def_obj, default_file)
