import json

from jsonschema import validate

_MODIFICATIONS = 'service-modifications'

_DEPLOYMENT_PARAMETERS = 'deployment-parameters'
_CI_DEPLOYMENT_PARAMETERS = 'ci-deployment-parameters'
_PROD_DEPLOYMENT_PARAMETERS = 'prod-deployment-parameters'
_DEV_DEPLOYMENT_PARAMETERS = 'dev-deployment-parameters'
_UNIT_TEST_DEPLOYMENT_PARAMETERS = 'unit_test-deployment-parameters'
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

    def __init__(self, service_definition_path, environment):
        super(ServiceDefinition, self).__init__()
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
            else:
                self.deployment_parameters = {}
            env_deployment_parameters = '{environment}-deployment-parameters'.format(environment=environment)
            if env_deployment_parameters in service_definition:
                self.deployment_parameters.update(service_definition[env_deployment_parameters])
            if _MODIFICATIONS in service_definition:
                self.service_modifications = service_definition[_MODIFICATIONS]
