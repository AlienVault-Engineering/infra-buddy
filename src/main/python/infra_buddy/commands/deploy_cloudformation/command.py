import os
import click
from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.aws.s3 import S3Buddy
from infra_buddy.commandline import cli


def do_command(deploy_ctx, template, parameter_file, config_templates):
    # Initialize our buddies
    s3 = S3Buddy(deploy_ctx)
    cloud_formation = CloudFormationBuddy(deploy_ctx)
    # Upload our template to s3 to make things a bit easier and keep a record
    template_file_url = s3.upload(file=template)
    # Upload all of our config files to S3 rendering any variables
    if config_templates:
        for template in os.listdir(config_templates):
            if template.endswith("tmpl"):
                rendered = deploy_ctx.render_template(os.path.join(config_templates,template))
                s3.upload(file=rendered,file_name=template.replace(".tmpl", ""))
    # render our parameter files
    parameter_file_rendered = deploy_ctx.render_template(parameter_file)
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
    do_command(deploy_ctx, template, parameter_file, config_templates)
