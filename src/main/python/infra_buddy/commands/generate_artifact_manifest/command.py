import click

from infra_buddy.commandline import cli
from infra_buddy.context.artifact_definition import ArtifactDefinition
from infra_buddy.context.deploy_ctx import DeployContext


@cli.command(name='generate-artifact-manifest')
@click.option("--artifact-type", help="The type of artifact referenced in the manifest ( 'ecs' or 's3' currently supported).")
@click.option("--artifact-location", help="The location of the artifact referenced in the manifest (Docker registry or S3 bucket and path).")
@click.option("--artifact-identifier", help="The identifier for the artifact. (Docker tag or filename excluding 'zip' extension).")
def deploy_cloudformation(artifact_type,artifact_location,artifact_identifier):
    # type: (str,str,str) -> None
    do_command(artifact_type,artifact_location,artifact_identifier)


def do_command(artifact_type, artifact_location, artifact_identifier, destination=None):
    # type: (str,str,str) -> str
    ad = ArtifactDefinition.create(artifact_type,artifact_location,artifact_identifier)
    return ad.save_to_file(destination_dir=destination)
