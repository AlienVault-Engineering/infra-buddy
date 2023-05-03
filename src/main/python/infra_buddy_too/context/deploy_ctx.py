import datetime
import json
import os
import re
import tempfile
import zipfile
from collections import OrderedDict
from pprint import pformat

from infra_buddy_too.aws import s3
from infra_buddy_too.context.artifact_definition import ArtifactDefinition
from infra_buddy_too.context.monitor_definition import MonitorDefinition
from infra_buddy_too.context.service_definition import ServiceDefinition
from infra_buddy_too.notifier.datadog_notifier import DataDogNotifier
from infra_buddy_too.template.template_manager import TemplateManager
from infra_buddy_too.utility import print_utility

STACK_NAME = 'STACK_NAME'

DOCKER_REGISTRY = 'DOCKER_REGISTRY_URL'
ROLE = 'ROLE'
IMAGE = 'IMAGE'
APPLICATION = 'APPLICATION'
ENVIRONMENT = 'ENVIRONMENT'
REGION = 'REGION'
SKIP_ECS = 'SKIP_ECS'
WAIT_FOR_ECS_TASK_RUN_FINISH = 'WAIT_FOR_ECS_TASK_RUN_FINISH'
ECS_TASK_RUN_MAX_RETRIES = 'ECS_TASK_RUN_MAX_RETRIES'
ECS_TASK_RUN = 'ECS_TASK_RUN'
# default to env variables on these
built_in = [DOCKER_REGISTRY, ROLE, APPLICATION, ENVIRONMENT, REGION, SKIP_ECS, ECS_TASK_RUN,
            WAIT_FOR_ECS_TASK_RUN_FINISH]
env_variables = OrderedDict()
env_variables['VPCAPP'] = "${VPCAPP}"
env_variables['DEPLOY_DATE'] = "${DEPLOY_DATE}"
env_variables[STACK_NAME] = "${ENVIRONMENT}-${APPLICATION}-${ROLE}"
env_variables['EnvName'] = "${STACK_NAME}"  # alias
env_variables['ECS_SERVICE_STACK_NAME'] = "${STACK_NAME}"  # alias
env_variables['SERVICE_STACK_NAME'] = "${STACK_NAME}"  # alias
env_variables['VPC_STACK_NAME'] = "${ENVIRONMENT}-${VPCAPP}-vpc"
env_variables['CF_BUCKET_NAME'] = "${ENVIRONMENT}-${VPCAPP}-cloudformation-deploy-resources"
env_variables['TEMPLATE_BUCKET'] = "${ENVIRONMENT}-${VPCAPP}-cloudformation-deploy-resources"  # alias
env_variables['CF_DEPLOY_RESOURCE_PATH'] = "${STACK_NAME}/${DEPLOY_DATE}"
env_variables[
    'CONFIG_TEMPLATES_URL'] = "https://s3-${REGION}.amazonaws.com/${CF_BUCKET_NAME}/${CF_DEPLOY_RESOURCE_PATH}"
env_variables['CONFIG_TEMPLATES_EAST_URL'] = "https://s3.amazonaws.com/${CF_BUCKET_NAME}/${CF_DEPLOY_RESOURCE_PATH}"
env_variables['CLUSTER_STACK_NAME'] = "${ENVIRONMENT}-${APPLICATION}-cluster"
env_variables['RESOURCE_STACK_NAME'] = "${ENVIRONMENT}-${APPLICATION}-${ROLE}-resources"
env_variables['ECS_SERVICE_RESOURCE_STACK_NAME'] = "${RESOURCE_STACK_NAME}"  # alias
env_variables['KEY_NAME'] = "${ENVIRONMENT}-${APPLICATION}"
env_variables['CHANGE_SET_NAME'] = "${STACK_NAME}-deploy-cloudformation-change-set"
env_variables['S3_DEPLOY_BUCKET_EXPORT'] = "WWW-Files"
env_variables['S3_DEPLOY_BUCKET'] = None


class DeployContext(dict):
    def __init__(self, defaults, environment):
        super(DeployContext, self).__init__()
        self.current_deploy = None
        self.temp_files = []
        self._initalize_defaults(defaults, environment)

    @classmethod
    def create_deploy_context_artifact(cls, artifact_directory, environment, defaults=None):
        # type: (str, str) -> DeployContext
        """
        :rtype DeployContext
        :param artifact_directory: Path to directory containing service definition.
                May be a s3 URL pointing at a zip archive
        :param defaults: Dict containing default environment settings
        """
        ret = DeployContext(defaults=defaults, environment=environment)
        ret._initialize_artifact_directory(artifact_directory)
        ret._initialize_environment_variables()
        return ret

    @classmethod
    def create_deploy_context(cls, application, role, environment, defaults=None):
        # type: (str, str, str, str) -> DeployContext
        """
        :rtype DeployContext
        :param application: Application name
        :param role: Role of service
        :param environment: Environment to deploy
        :param defaults: Path to json file containing default environment settings
        """
        ret = DeployContext(defaults=defaults, environment=environment)
        ret['APPLICATION'] = application
        ret['ROLE'] = role
        ret._initialize_environment_variables()
        return ret

    def print_self(self):
        print_utility.warn("Context:")
        print_utility.warn("Stack: {}".format(self.stack_name))
        if len(self.stack_name_cache) > 0:
            print_utility.warn("Depth: {}".format(self.stack_name_cache))
        if self.current_deploy:
            print_utility.banner_info("Deploy Defaults:", pformat(self.current_deploy.defaults))
        print_utility.banner_info("Environment:", pformat(self))

    def _initialize_artifact_directory(self, artifact_directory):
        # type: (str) -> None
        if artifact_directory.startswith("s3://"):
            tmp_dir = tempfile.mkdtemp()
            s3.download_zip_from_s3_url(artifact_directory, destination=tmp_dir)
            artifact_directory = tmp_dir
        service_definition = ServiceDefinition(artifact_directory, self['ENVIRONMENT'])
        self[APPLICATION] = service_definition.application
        self[ROLE] = service_definition.role
        self[DOCKER_REGISTRY] = service_definition.docker_registry
        self.update(service_definition.deployment_parameters)
        self.load_remote_defaults(service_definition.service_template_definition_locations)
        self.service_definition = service_definition
        self.artifact_definition = ArtifactDefinition.create_from_directory(artifact_directory)
        self.monitor_definition = MonitorDefinition.create_from_directory(artifact_directory)
        self.artifact_definition.register_env_variables(self)

    def _initialize_environment_variables(self):
        application = self['APPLICATION']
        self['VPCAPP'] = application if not application or '-' not in application else application[
                                                                                       :application.find('-')]
        # allow for partial stack names for validation and introspection usecases
        stack_template = "${ENVIRONMENT}"
        if application:
            stack_template += "-${APPLICATION}"
            if self['ROLE']:
                stack_template += "-${ROLE}"
        env_variables[STACK_NAME] = stack_template
        self['DEPLOY_DATE'] = datetime.datetime.now().strftime("%b_%d_%Y_Time_%H_%M")
        for property_name in built_in:
            self.__dict__[property_name.lower()] = self.get(property_name, None)
        for variable, template in env_variables.items():
            evaluated_template = self.expandvars(template)
            self[variable] = evaluated_template
            self.__dict__[variable.lower()] = evaluated_template
        # s3 has non-standardized behavior in us-east-1 you can not use the region in the url
        if self['REGION'] == 'us-east-1':
            self['CONFIG_TEMPLATES_URL'] = self['CONFIG_TEMPLATES_EAST_URL']
            self.__dict__['CONFIG_TEMPLATES_URL'.lower()] = self['CONFIG_TEMPLATES_EAST_URL']

        print_utility.info("deploy_ctx = {}".format(repr(self.__dict__)))

    def _initalize_defaults(self, defaults, environment):
        self['DATADOG_KEY'] = ""
        self['ENVIRONMENT'] = environment.lower() if environment else "dev"
        if defaults:
            self.update(defaults)
        self.update(os.environ)
        if 'REGION' not in self:
            default_region = os.environ.get('AWS_DEFAULT_REGION',None)
            if default_region:
                print_utility.info("Did not find 'REGION' variable using 'AWS_DEFAULT_REGION'")
                self['REGION'] = default_region
            else:
                print_utility.warn("Region not configured using default 'us-west-1'. "
                                   "This is probably not what you want - N. California is slow, like real slow."
                                   "  Set the environment variable 'REGION' or pass a default configuration file to override. ")
                self['REGION'] = 'us-west-1'
        self.template_manager = TemplateManager(self.get_deploy_templates(), self.get_service_modification_templates())
        self.stack_name_cache = []
        if self.get('DATADOG_KEY', '') != '':
            self.notifier = DataDogNotifier(key=self['DATADOG_KEY'], deploy_context=self)
        else:
            self.notifier = None

    def get_deploy_templates(self):
        return self.get('service-templates', {})

    def get_service_modification_templates(self):
        return self.get('service-modification-templates', {})

    def generate_modification_stack_name(self, mod_name, ending=None):
        name__format = '{ENVIRONMENT}-{APPLICATION}-{ROLE}-{mod_name}'.format(mod_name=mod_name, **self)
        return name__format if not ending else f"{name__format}-{ending}"

    def generate_modification_resource_stack_name(self, mod_name):
        return "{ENVIRONMENT}-{APPLICATION}-{ROLE}-{mod_name}-resources".format(mod_name=mod_name, **self)

    def get_region(self):
        return self._get_required_default_configuration(REGION)

    def _get_required_default_configuration(self, key):
        region = self.get(key, os.environ.get(key, None))
        if not region:
            raise Exception("Required default not set {key}.\n"
                            "Configure --configuration-defaults or set ENVIRONMENT variable {key}".format(
                key=key))
        return region

    def notify_event(self, title, type, message=None):
        if self.notifier:
            self.notifier.notify_event(title, type, message)
        else:
            print_utility.warn("Notify {type}: {title} - {message}".format(type=type, title=title, message=message))

    def get_service_modifications(self):
        return self.service_definition.service_modifications

    def should_skip_ecs_trivial_update(self):
        return self._assert_true(SKIP_ECS, "true")

    def _assert_true(self, variable, default_value):
        return str(self.get(variable, os.environ.get(variable, default_value))).lower() == "true"

    def wait_for_run_task_finish(self):
        return self._assert_true(WAIT_FOR_ECS_TASK_RUN_FINISH, "true")

    def get_task_max_retry(self):
        return self.get(ECS_TASK_RUN_MAX_RETRIES,1200)

    def is_task_run_service(self):
        return self._assert_true(ECS_TASK_RUN, "false")

    def render_template(self, file, destination):
        if zipfile.is_zipfile(file): return  os.path.abspath(file)
        with open(file, 'r') as source:
            with open(os.path.join(destination, os.path.basename(file).replace('.tmpl', '')), 'w+') as destination:
                temp_file_path = os.path.abspath(destination.name)
                print_utility.info("Rendering template to path: {}".format(temp_file_path))
                self.temp_files.append(temp_file_path)
                for line in source:
                    destination.write(self.expandvars(line))
                return temp_file_path

    def __del__(self):
        for file in self.temp_files:
            os.remove(file)

    def get_execution_plan(self):
        # type: () -> list(Deploy)
        execution_plan = self.service_definition.generate_execution_plan(self.template_manager, self)
        artifact_plan = self.artifact_definition.generate_execution_plan(self)
        if artifact_plan:
            execution_plan.extend(artifact_plan)
        monitor_plan = self.monitor_definition.generate_execution_plan(self)
        if monitor_plan:
            execution_plan.extend(monitor_plan)
        print_utility.progress("Execution Plan:")
        for deploy in execution_plan:
            # Propogate flag to indicate that we should not actually deploy (see deploy-environments['skip'])
            if self.service_definition.dry_run:
                deploy.dry_run = True
            print_utility.info_banner("\t" + str(deploy))
        return execution_plan

    def expandvars(self, template_string, aux_dict=None):
        if not template_string: return template_string  # if you pass none, return none
        """Expand ENVIRONMENT variables of form $var and ${var}.
        """

        def replace_var(m):
            if aux_dict:
                val = aux_dict.get(m.group(2) or m.group(1), None)
                if val is not None: return transform(val)
            # if we are in a deployment values set in that context take precedent
            if self.current_deploy is not None:
                val = self.current_deploy.defaults.get(m.group(2) or m.group(1), None)
                if val is not None: return transform(val)
            return transform(self.get(m.group(2) or m.group(1), m.group(0)))

        def transform(val):
            if isinstance(val, bool):
                return str(val).lower()
            return str(val)

        reVar = r'(?<!\\)\$(\w+|\{([^}]*)\})'
        sub = re.sub(reVar, replace_var, template_string)
        return sub

    def recursive_expand_vars(self, source):
        if isinstance(source, dict):
            ret = {}
            for key, value in source.items():
                ret[key] = self.recursive_expand_vars(value)
            return ret
        elif isinstance(source, list):
            ret = []
            for item in source:
                ret.append(self.recursive_expand_vars(item))
            return ret
        elif isinstance(source, str):
            return self.expandvars(source)
        else:
            return source

    def push_deploy_ctx(self, deploy_):
        # type: (CloudFormationDeploy) -> None
        if deploy_.stack_name:
            self.stack_name_cache.append(self[STACK_NAME])
            self._update_stack_name(deploy_.stack_name)
        self.current_deploy = deploy_

    def _update_stack_name(self, new_val):
        self[STACK_NAME] = new_val
        self.stack_name = new_val

    def pop_deploy_ctx(self):
        if self.current_deploy.stack_name:
            new_val = self.stack_name_cache.pop()
            self._update_stack_name(new_val)
        self.current_deploy = None

    def load_remote_defaults(self, service_template_definition_locations):
        if service_template_definition_locations is None or len(service_template_definition_locations) == 0:
            return
        for location in service_template_definition_locations:
            self.template_manager.load_additional_templates(remote_template_definition_location=location)
