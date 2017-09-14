import click

from infra_buddy.commandline import cli
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.context import service_definition
from infra_buddy.context.service_definition import ServiceDefinition
from infra_buddy.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy.template.template import NamedLocalTemplate
from infra_buddy.utility import print_utility


@cli.command(name='generate-service-definition',
             short_help="Generate a service definition for use by the deploy-service command.")
@click.option("--template-directory", type=click.Path(exists=True), help="The directory containing "
                                                                         "the service template.")
@click.option("--service-type", help="The service-type that corresponds with the provided template directory (or a "
                                     "built-in service type).")
@click.pass_obj
def deploy_cloudformation(deploy_ctx, service_template_directory, service_type):
    # type: (DeployContext,str,str) -> None
    do_command(deploy_ctx, service_template_directory, service_type)


def do_command(deploy_ctx, service_template_directory=None, service_type=None, destination=None):
    # type: (DeployContext,[str or None],str) -> str
    if service_template_directory is None:
        print_utility.warn(
            "Service template directory was not provided.  Assuming service-type '{}' is built-in.".format(
                service_type))
        template = deploy_ctx.template_manager.get_known_service(service_type=service_type)
        if not template:
            print_utility.warn(
                "Service template was not found.  Assuming service-type '{}' is a service modification.".format(
                    service_type))
            template = deploy_ctx.template_manager.get_known_service_modification(service_type=service_type)
        deploy = CloudFormationDeploy(stack_name=deploy_ctx.stack_name, template=template, deploy_ctx=deploy_ctx)
    else:
        deploy = CloudFormationDeploy(stack_name=deploy_ctx.stack_name,
                                      template=NamedLocalTemplate(service_template_directory, service_type),
                                      deploy_ctx=deploy_ctx)
    return ServiceDefinition.save_to_file(application=deploy_ctx.application,
                                          role=deploy_ctx.role,
                                          deploy_params=deploy.get_default_params(),
                                          known_service_modifications=deploy_ctx.template_manager.service_modification_templates
                                          , service_type=service_type,
                                          destination=destination)
