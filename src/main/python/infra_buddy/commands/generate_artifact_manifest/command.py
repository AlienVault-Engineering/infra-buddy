import click

from infra_buddy.commandline import cli
from infra_buddy.context.artifact_definition import ArtifactDefinition
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.utility import print_utility


@cli.command(name='generate-artifact-manifest',
             short_help="Generate an artifact manifest for use by the deploy-service command.")
@click.option("--artifact-type",
              help="The type of artifact referenced in the manifest ( 'container' or 's3' currently supported).")
@click.option("--artifact-location",
              help="The location of the artifact referenced in the manifest (Docker registry or S3 bucket and path).")
@click.option("--artifact-identifier",
              help="The identifier for the artifact. (Docker tag or filename excluding 'zip' extension).")
def deploy_cloudformation(artifact_type, artifact_location, artifact_identifier):
    # type: (str,str,str) -> None
    path  = do_command(artifact_type, artifact_location, artifact_identifier)
    print_utility.info("Artifact Manifest saved to - {}".format(path))




def do_command(artifact_type, artifact_location, artifact_identifier, destination=None):
    # type: (str,str,str) -> str
    ad = ArtifactDefinition.create(artifact_type, artifact_location, artifact_identifier)
    print_utility.info("Generated artifact manifest - {}".format(ad.__class__.__class__))
    return ad.save_to_file(destination_dir=destination)
