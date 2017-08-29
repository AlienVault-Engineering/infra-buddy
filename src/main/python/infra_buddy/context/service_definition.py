import json
import os

from jsonschema import validate

from infra_buddy.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy.template.template_manager import TemplateManager
from infra_buddy.utility import print_utility

_MODIFICATIONS = 'service-modifications'

_DEPLOYMENT_PARAMETERS = 'deployment-parameters'
_CI_DEPLOYMENT_PARAMETERS = 'ci-deployment-parameters'
_PROD_DEPLOYMENT_PARAMETERS = 'prod-deployment-parameters'
_DEV_DEPLOYMENT_PARAMETERS = 'dev-deployment-parameters'
_UNIT_TEST_DEPLOYMENT_PARAMETERS = 'unit-test-deployment-parameters'
_DOCKER_REGISTRY = 'registry-url'
_SERVICE_TYPE = 'service-type'
_ROLE = 'role'
_APPLICATION = 'application'


class ServiceDefinition(object):
    schema = {
        "type": "object",
        "properties": {
            _APPLICATION: {"type": "string"},
            _ROLE: {"type": "string"},
            _SERVICE_TYPE: {"type": "string"},
            _DOCKER_REGISTRY: {"type": ["string", "null"], 'maxLength': 1000},
            _DEPLOYMENT_PARAMETERS: {
                "type": "object",
                "properties": {
                },
                "additionalProperties": True
            },
            _CI_DEPLOYMENT_PARAMETERS: {
                "type": "object",
                "properties": {
                },
                "additionalProperties": True
            },
            _PROD_DEPLOYMENT_PARAMETERS: {
                "type": "object",
                "properties": {
                },
                "additionalProperties": True
            },
            _DEV_DEPLOYMENT_PARAMETERS: {
                "type": "object",
                "properties": {
                },
                "additionalProperties": True
            }
        },
        "required": [
            _APPLICATION,
            _ROLE,
            _DEPLOYMENT_PARAMETERS,
            _SERVICE_TYPE
        ]
    }

    def __init__(self, artifact_directory, environment):
        super(ServiceDefinition, self).__init__()
        self.artifact_directory = artifact_directory
        service_definition_path = os.path.join(artifact_directory, "service.json")
        if not os.path.exists(service_definition_path):
            err_msg = "Service definition (service.json) does not exist in artifact directory - {}".format(
                artifact_directory)
            print_utility.error(err_msg)
            raise Exception(err_msg)
        with open(service_definition_path, 'r') as fp:
            service_definition = json.load(fp)
            validate(service_definition, self.schema)
            self.application = service_definition[_APPLICATION]
            self.role = service_definition[_ROLE]
            self.service_type = service_definition[_SERVICE_TYPE]
            self.docker_registry = service_definition[_DOCKER_REGISTRY]
            deployment_parameters = _DEPLOYMENT_PARAMETERS
            if deployment_parameters in service_definition:
                self.deployment_parameters = service_definition[deployment_parameters]
            env_deployment_parameters = '{environment}-deployment-parameters'.format(environment=environment)
            if env_deployment_parameters in service_definition:
                self.deployment_parameters.update(service_definition[env_deployment_parameters])
            self.service_modifications = service_definition.get(_MODIFICATIONS, [])

    def generate_execution_plan(self, template_manager, deploy_ctx):
        # type: (TemplateManager) -> list
        ret = []
        ret.append(CloudFormationDeploy(stack_name=deploy_ctx.stack_name,
                                        template=template_manager.get_known_service(self.service_type),
                                        deploy_ctx=deploy_ctx))
        resource_deploy = template_manager.get_resource_service(self.artifact_directory)
        if resource_deploy:
            ret.append(CloudFormationDeploy(stack_name=deploy_ctx.resource_stack_name,
                                            template=resource_deploy,
                                            deploy_ctx=deploy_ctx))
        for mod in self.service_modifications:
            template = template_manager.get_known_service_modification(mod)
            ret.append(CloudFormationDeploy(stack_name=deploy_ctx.generate_modification_stack_name(mod),
                                            template=template,
                                            deploy_ctx=deploy_ctx))
        return ret
