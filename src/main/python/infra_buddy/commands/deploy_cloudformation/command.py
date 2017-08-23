import os
import click
from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.aws.s3 import S3Buddy
from infra_buddy.commandline import cli
from infra_buddy.context.deploy import Deploy
from infra_buddy.context.template import LocalTemplate


def do_command(deploy_ctx, deploy_plan):
    # type: (DeployContext, Deploy) -> None

    template = deploy_plan.template_file
    # Initialize our buddies
    s3 = S3Buddy(deploy_ctx)
    cloud_formation = CloudFormationBuddy(deploy_ctx)
    # Upload our template to s3 to make things a bit easier and keep a record
    template_file_url = s3.upload(file=template)
    # Upload all of our config files to S3 rendering any variables
    config_files = deploy_plan.get_rendered_config_files(deploy_ctx)
    for rendered in config_files:
        s3.upload(file=rendered)
    # render our parameter files
    parameter_file_rendered = deploy_plan.get_rendered_param_file(deploy_ctx)
    # see if we are updating or creating
    if cloud_formation.does_stack_exist():
        cloud_formation.create_change_set(template_file_url=template_file_url, parameter_file=parameter_file_rendered)
        # make sure it is avaiable and that there are no special conditions
        if cloud_formation.should_execute_change_set():
            cloud_formation.execute_change_set()
        else:
            # if there are no changes then clean up and exit
            cloud_formation.delete_change_set()
            return
    else:
        cloud_formation.create_stack(template_file_url=template_file_url,
                                     parameter_file=parameter_file_rendered)



@cli.command(name='deploy-cloudformation')
@click.option('--template', envvar='TEMPLATE', type=click.Path(exists=True),
              help='The cloudformation template to deploy')
@click.option('--parameter-file', envvar='PARAMETER_FILE', type=click.Path(exists=True),
              help='The json parameter file that corresponds with the cloudformation template to deploy')
@click.option('--config-templates', envvar='CONFIG_TEMPLATES', type=click.Path(exists=True),
              help='A directory containing templates to be evaluated and staged for deployment.')
@click.pass_obj
def deploy_cloudformation(deploy_ctx, template, parameter_file, config_templates):
    deploy_plan = Deploy(deploy_ctx.stack_name, LocalTemplate(template,parameter_file,config_templates),deploy_ctx)
    do_command(deploy_ctx, deploy_plan)
