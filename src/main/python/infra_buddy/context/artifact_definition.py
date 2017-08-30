import json
import os

from jsonschema import validate

from infra_buddy.deploy.ecs_deploy import ECSDeploy
from infra_buddy.deploy.s3_deploy import S3Deploy
from infra_buddy.utility import print_utility

_ECS_ARTIFACT_TYPE = "ecs"
_S3_ARTIFACT_TYPE = "s3"

_ARTIFACT_TYPE = "artifact-type"
_ARTIFACT_IDENTIFIER = "artifact-identifier"
_ARTIFACT_LOCATION = "artifact-path"



class ArtifactDefinition(object):
    schema = {
        "type": "object",
        "properties": {
            _ARTIFACT_TYPE: {"type": "string", "enum": [_ECS_ARTIFACT_TYPE, _S3_ARTIFACT_TYPE]},
            _ARTIFACT_IDENTIFIER: {"type": "string"},
            _ARTIFACT_LOCATION: {"type": "string"}
        },
        "required": [
            _ARTIFACT_TYPE,
            _ARTIFACT_IDENTIFIER,
            _ARTIFACT_LOCATION
        ]
    }

    def __init__(self, artifact_directory):
        super(ArtifactDefinition, self).__init__()
        definition = self._load_artifact_definition(artifact_directory)
        if not definition:
            definition = self._search_for_legacy_implementation(artifact_directory)
        if definition:
            validate(definition, self.schema)
            self.artifact_type = definition[_ARTIFACT_TYPE]
            self.artifact_location = definition[_ARTIFACT_LOCATION]
            self.artifact_id = definition[_ARTIFACT_IDENTIFIER]
            self.noop = False
        else:
            self.noop = True

    def _search_for_legacy_implementation(self, artifact_directory):
        image_definition = os.path.join(artifact_directory, "containerurl.txt")
        ret = {_ARTIFACT_TYPE: _ECS_ARTIFACT_TYPE}
        if os.path.exists(image_definition):
            print_utility.warn("Defining ECS service udpate with deprecated containerurl.txt artifact")
            with open(image_definition, 'r') as image:
                image_def = self.image = image.read()
                rfind = image_def.rfind(":")
                ret[_ARTIFACT_LOCATION] = image_def[:rfind]
                ret[_ARTIFACT_IDENTIFIER] = image_def[rfind+1:]
            return ret
        return None

    def _load_artifact_definition(self, artifact_directory):
        artifact_def_path = os.path.join(artifact_directory, "artifact.json")
        if os.path.exists(artifact_def_path):
            print_utility.info("Defining artifact definition with artifact.json - {}".format(artifact_def_path))
            with open(artifact_def_path, 'r') as art_def:
                return json.load(art_def)
        else:
            print_utility.warn("Artifact definition (artifact.json) did not exist in artifact directory.")
        return None

    def generate_execution_plan(self, deploy_ctx):
        if self.noop: return None
        if self.artifact_type == _ECS_ARTIFACT_TYPE:
            return ECSDeploy(self.artifact_id, self.artifact_location,deploy_ctx)
        elif self.artifact_type == _S3_ARTIFACT_TYPE:
            return S3Deploy(self.artifact_id,self.artifact_location,deploy_ctx)
        else:
            raise Exception("Well, this is unexpected")
