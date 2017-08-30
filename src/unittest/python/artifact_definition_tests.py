import os
import tempfile

from infra_buddy.aws import s3
from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.aws.s3 import S3Buddy
from infra_buddy.commandline import cli
from infra_buddy.commands.deploy_cloudformation import command
from infra_buddy.context.artifact_definition import ArtifactDefinition
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy.template.template import NamedLocalTemplate
from infra_buddy.utility import helper_functions
from testcase_parent import ParentTestCase


class ArtifactDefinitionTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(ArtifactDefinitionTestCase, cls).setUpClass()

    def test_artifact_definition(self):
        artifact_directory = self._get_resource_path('artifact_directory_tests/artifact_service_definition')
        art = ArtifactDefinition(artifact_directory)
        self.assertEqual(art.artifact_id,"39","Did not parse artifact id")
        self.assertEqual(art.artifact_location,"https://docker.io/my-registry/artifact","Did not parse artifact location")
        self.assertEqual(art.artifact_type,"ecs","Did not parse artifact type")
        artifact_directory = self._get_resource_path('artifact_directory_tests/artifact_s3_definition')
        art = ArtifactDefinition(artifact_directory)
        self.assertEqual(art.artifact_id,"39","Did not parse artifact id")
        self.assertEqual(art.artifact_location,"s3_bucket/path","Did not parse artifact location")
        self.assertEqual(art.artifact_type,"s3","Did not parse artifact type")
        artifact_directory = self._get_resource_path('artifact_directory_tests/legacy_artifact_definition')
        art = ArtifactDefinition(artifact_directory)
        self.assertEqual(art.artifact_id,"39","Did not parse artifact id")
        self.assertEqual(art.artifact_location,"https://docker.io/my-registry/artifact","Did not parse artifact location")
        self.assertEqual(art.artifact_type,"ecs","Did not parse artifact type")