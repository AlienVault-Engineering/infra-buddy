import json
import os

from jsonschema import validate

from infra_buddy.deploy.ecs_deploy import ECSDeploy
from infra_buddy.deploy.s3_deploy import S3Deploy
from infra_buddy.utility import print_utility

_ARTIFACT_FILE = "artifact.json"

_CONTAINER_ARTIFACT_TYPE = "container"
_S3_ARTIFACT_TYPE = "s3"
_NOOP_ARTIFACT_TYPE = "noop"

_ARTIFACT_TYPE = "artifact-type"
_ARTIFACT_IDENTIFIER = "artifact-identifier"
_ARTIFACT_LOCATION = "artifact-path"


class ArtifactDefinition(object):
    schema = {
        "type": "object",
        "properties": {
            _ARTIFACT_TYPE: {"type": "string", "enum": [_CONTAINER_ARTIFACT_TYPE, _S3_ARTIFACT_TYPE]},
            _ARTIFACT_IDENTIFIER: {"type": "string"},
            _ARTIFACT_LOCATION: {"type": "string"}
        },
        "required": [
            _ARTIFACT_TYPE,
            _ARTIFACT_IDENTIFIER,
            _ARTIFACT_LOCATION
        ]
    }

    @classmethod
    def create(cls, artifact_type=None, artifact_location=None, artifact_identifier=None):
        # type: (str, str, str) -> ArtifactDefinition
        if artifact_type == _CONTAINER_ARTIFACT_TYPE:
            return ECSArtifactDefinition(artifact_location=artifact_location,
                                         artifact_identifier=artifact_identifier)
        elif artifact_type == _S3_ARTIFACT_TYPE:
            return S3ArtifactDefinition(artifact_location=artifact_location,
                                        artifact_identifier=artifact_identifier)
        elif artifact_type:
            raise Exception("Unknown artifact type")
        else:
            return NOOPArtifactDefinition(None, None)

    @classmethod
    def create_from_directory(cls, artifact_directory):
        # type: (str) -> ArtifactDefinition
        definition = ArtifactDefinition._load_artifact_definition(artifact_directory)
        if not definition:
            definition = ArtifactDefinition._search_for_legacy_implementation(artifact_directory)
        if definition:
            validate(definition, ArtifactDefinition.schema)
            return cls.create(definition[_ARTIFACT_TYPE], definition[_ARTIFACT_LOCATION],
                              definition[_ARTIFACT_IDENTIFIER])
        else:
            return cls.create()

    def __init__(self, artifact_type, artifact_location, artifact_identifier):
        super(ArtifactDefinition, self).__init__()
        self.artifact_type = artifact_type
        self.artifact_location = artifact_location
        self.artifact_id = artifact_identifier

    @staticmethod
    def _search_for_legacy_implementation(artifact_directory):
        image_definition = os.path.join(artifact_directory, "containerurl.txt")
        ret = {_ARTIFACT_TYPE: _CONTAINER_ARTIFACT_TYPE}
        if os.path.exists(image_definition):
            print_utility.warn("Defining ECS service udpate with deprecated containerurl.txt artifact")
            with open(image_definition, 'r') as image:
                image_def = image.read().strip()
                rfind = image_def.rfind(":")
                ret[_ARTIFACT_LOCATION] = image_def[:rfind]
                ret[_ARTIFACT_IDENTIFIER] = image_def[rfind + 1:]
            return ret
        return None

    @staticmethod
    def _load_artifact_definition(artifact_directory):
        artifact_def_path = os.path.join(artifact_directory, _ARTIFACT_FILE)
        if os.path.exists(artifact_def_path):
            print_utility.info("Defining artifact definition with artifact.json - {}".format(artifact_def_path))
            with open(artifact_def_path, 'r') as art_def:
                return json.load(art_def)
        else:
            print_utility.warn("Artifact definition (artifact.json) did not exist in artifact directory."
                               " Continuing infrastructure update without artifact deploy.")
        return None

    def generate_execution_plan(self, deploy_ctx):
        raise Exception("Well, this is unexpected")

    def save_to_file(self, destination_dir=None):
        if destination_dir:
            path = os.path.join(destination_dir, _ARTIFACT_FILE)
        else:
            path = _ARTIFACT_FILE
        print_utility.info("Persisting artifact manfiest - {}".format(path))
        with open(path, 'w') as file:
            json.dump({_ARTIFACT_TYPE: self.artifact_type,
                       _ARTIFACT_LOCATION: self.artifact_location,
                       _ARTIFACT_IDENTIFIER: self.artifact_id}, file)
        return path

    def register_env_variables(self, deploy_ctx):
        if self.artifact_type == _CONTAINER_ARTIFACT_TYPE:
            # For first time deploys of ECS services
            deploy_ctx['IMAGE'] = "{location}:{tag}".format(location=self.artifact_location, tag=self.artifact_id)


class ECSArtifactDefinition(ArtifactDefinition):
    def __init__(self, artifact_location, artifact_identifier):
        super(ECSArtifactDefinition, self).__init__(_CONTAINER_ARTIFACT_TYPE, artifact_location, artifact_identifier)

    def generate_execution_plan(self, deploy_ctx):
        return [ECSDeploy(self.artifact_id, self.artifact_location, deploy_ctx)]


class S3ArtifactDefinition(ArtifactDefinition):
    def __init__(self, artifact_location, artifact_identifier):
        super(S3ArtifactDefinition, self).__init__(_S3_ARTIFACT_TYPE, artifact_location, artifact_identifier)

    def generate_execution_plan(self, deploy_ctx):
        return [S3Deploy(self.artifact_id, self.artifact_location, deploy_ctx)]


class NOOPArtifactDefinition(ArtifactDefinition):
    def __init__(self, artifact_location, artifact_identifier):
        super(NOOPArtifactDefinition, self).__init__(_NOOP_ARTIFACT_TYPE, artifact_location, artifact_identifier)

    def generate_execution_plan(self, deploy_ctx):
        return None
