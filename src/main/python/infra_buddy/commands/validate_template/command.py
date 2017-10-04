import click

from infra_buddy.commandline import cli
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy.template.template import NamedLocalTemplate
from infra_buddy.utility import print_utility


@cli.command(name='validate-template',short_help="Analyze a service template or built-in service-type for logical "
                                                 "errors and usability issues.")
@click.option("--service-template-directory", type=click.Path(exists=True), help="The directory containing "
                                                                         "the service template.")
@click.option("--service-type", help="The service-type of an internal template.")
@click.pass_obj
def deploy_cloudformation(deploy_ctx, service_template_directory, service_type):
    # type: (DeployContext,str,str) -> None
    do_command(deploy_ctx, service_template_directory, service_type)


def do_command(deploy_ctx, service_template_directory=None, service_type=None):
    # type: (DeployContext,[str or None],str) -> None
    if service_template_directory is None:
        print_utility.warn(
            "Service template directory was not provided.  Assuming service-type '{}' is built-in.".format(
                service_type))
        template = deploy_ctx.template_manager.get_known_template(template_name=service_type)
        deploy = CloudFormationDeploy(stack_name=deploy_ctx.stack_name, template=template, deploy_ctx=deploy_ctx)
    else:
        deploy = CloudFormationDeploy(stack_name=deploy_ctx.stack_name,
                                      template=NamedLocalTemplate(service_template_directory ),
                                      deploy_ctx=deploy_ctx)
    errs = deploy.analyze()
    if errs > 0:
        print_utility.error("Template raised {} errors ".format(errs), raise_exception=True)
