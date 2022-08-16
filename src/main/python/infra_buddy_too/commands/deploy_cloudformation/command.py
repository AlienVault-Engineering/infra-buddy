import os
import click
from infra_buddy_too.aws.cloudformation import CloudFormationBuddy
from infra_buddy_too.aws.s3 import S3Buddy
from infra_buddy_too.commandline import cli
from infra_buddy_too.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy_too.template.template import LocalTemplate


@cli.command(name='deploy-cloudformation')
@click.option('--template', envvar='TEMPLATE', type=click.Path(exists=True),
              help='The cloudformation template to deploy')
@click.option('--parameter-file', envvar='PARAMETER_FILE', type=click.Path(exists=True),
              help='The json parameter file that corresponds with the cloudformation template to deploy')
@click.option('--config-templates', envvar='CONFIG_TEMPLATES', type=click.Path(exists=True),
              help='A directory containing templates to be evaluated and staged for deployment.')
@click.option('--lambda-templates', envvar='LAMBDA_TEMPLATES', type=click.Path(exists=True),
              help='A directory containing lambda templates to be evaluated and staged for deployment.')
@click.option("--dry-run", is_flag=True, help="Prints the execution plan and displays the evaluated "
                                               "parameter values for the deployment.")
@click.pass_obj
def deploy_cloudformation(deploy_ctx, template, parameter_file, config_templates, lambda_templates,dry_run):
    deploy_plan = CloudFormationDeploy(deploy_ctx.stack_name, LocalTemplate(template, parameter_file, config_templates,lambda_templates), deploy_ctx)
    deploy_plan.do_deploy(dry_run)
