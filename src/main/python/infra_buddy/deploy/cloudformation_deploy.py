import json
import os
import tempfile
from collections import defaultdict
from pprint import pformat

import pydash
from copy import deepcopy
from jsonschema import validate

from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.aws.s3 import S3Buddy, CloudFormationDeployS3Buddy
from infra_buddy.deploy.deploy import Deploy
from infra_buddy.utility import helper_functions, print_utility

_PARAM_TYPE_PROPERTY = "property"
_PARAM_TYPE_TRANSFORM = "transform"

_PARAM_TYPE_FUNC = "func"

_PARAM_TYPE_TEMPLATE = "template"


class CloudFormationDeploy(Deploy):
    schema = {
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": [_PARAM_TYPE_PROPERTY,
                                                    _PARAM_TYPE_FUNC,
                                                    _PARAM_TYPE_TEMPLATE,
                                                    _PARAM_TYPE_TRANSFORM]},
                "value": {"type": "string"},
                "default_value": {"type": "string"},
                "key": {"type": "string"}
            },
            "required": ["type"]
        }

    }

    def __init__(self, stack_name, template, deploy_ctx):
        # type: (str, Template,DeployContext) -> None
        super(CloudFormationDeploy, self).__init__(deploy_ctx)
        self.stack_name = stack_name
        self.config_directory = template.get_config_dir()
        self.parameter_file = template.get_parameter_file_path()
        self.template_file = template.get_template_file_path()
        self.default_path = template.get_defaults_file_path()
        self._load_defaults(template.get_default_env_values())

    def _load_defaults(self, default_env_values):
        self.defaults = {}
        if self.default_path and os.path.exists(self.default_path):
            with open(self.default_path, 'r') as default_fp:
                def_obj = json.load(default_fp)
                validate(def_obj, self.schema)
            self._process_default_dict(def_obj)
        self.defaults.update(default_env_values)

    def _process_default_dict(self, def_obj):
        _transformations = {}
        for key, value in def_obj.iteritems():
            self.defaults[key] = self._load_value(value, key, _transformations)
        for key, value in _transformations.iteritems():
            transform = self.transform(value,self.defaults.get(key,None))
            if transform is not None:
                self.defaults[key] = transform

    def _load_value(self, value, key, transformations):
        type_ = value['type']
        if type_ == _PARAM_TYPE_TEMPLATE:
            return self.deploy_ctx.expandvars(value['value'], self.defaults)
        elif type_ == _PARAM_TYPE_FUNC:
            if 'default_key' in value:
                # look for a default value before calling the func
                def_key = value['default_key']
                if def_key in self.defaults:
                    return self.defaults[def_key]
                elif def_key in self.deploy_ctx:
                    return self.deploy_ctx[def_key]
            # someday make it dynamic
            func_name = value['func_name']
            if "load_balancer_name" == func_name:
                return helper_functions.load_balancer_name(self.deploy_ctx)
            elif 'rule_priority' == func_name:
                return helper_functions.calculate_rule_priority(self.deploy_ctx, self.stack_name)
            else:
                print_utility.error(
                    "Can not locate function for defaults.json: Stack {} Function {}".format(self.stack_name,
                                                                                             func_name))
        elif type_ == _PARAM_TYPE_PROPERTY:
            default_value = value.get('default', None)
            if isinstance(default_value, basestring):
                default_value = self.deploy_ctx.expandvars(str(default_value), self.defaults)
            return self.deploy_ctx.get(value['key'], default_value)
        elif type_ == _PARAM_TYPE_TRANSFORM:
            # add it to the list of properties to transform after load
            transformations[key] = value
            # Load like a normal property, so override the type
            value['type'] = _PARAM_TYPE_PROPERTY
            # and recurse
            return self._load_value(value, None, None)
        else:
            # should die on JSON validation but to be complete
            print_utility.error(
                "Can not load value for type in defaults.json: Stack {} Type {}".format(self.stack_name, type_))

    def transform(self, definition, value):
        func_name = definition['func_name']
        if 'transform_fargate_cpu' == func_name:
            return helper_functions.transform_fargate_cpu(self.defaults, value)
        elif 'transform_fargate_memory' == func_name:
            return helper_functions.transform_fargate_memory(self.defaults, value)
        else:
            print_utility.error(
                "Can not locate function for defaults.json: Stack {} Function {}".format(self.stack_name,
                                                                                         func_name))

    def get_rendered_config_files(self):
        self._prep_render_destination()
        rendered_config_files = []
        config_dir = self.config_directory
        if config_dir:
            for template in os.listdir(config_dir):
                rendered_config_files.append(
                    self.deploy_ctx.render_template(os.path.join(config_dir, template), self.destination))
        return rendered_config_files

    def get_rendered_param_file(self):
        self._prep_render_destination()
        return self.deploy_ctx.render_template(self.parameter_file, self.destination)

    def validate(self):
        self.print_template_description()
        self.print_known_parameters()
        self.print_export()
        config_files = self.get_rendered_config_files()
        if len(config_files) == 0:
            print_utility.warn("No Configuration Files")
        else:
            print_utility.warn("Configuration Files:")
            for config_file in config_files:
                self._print_file(config_file)

    def _print_file(self, config_file):
        with open(config_file, 'r') as cf:
            print_utility.warn(os.path.basename(config_file))
            for line in cf.readlines():
                print_utility.banner(line)

    def _prep_render_destination(self):
        self.destination = tempfile.mkdtemp()

    def print_known_parameters(self):
        # type: (DeployContext) -> int
        known_param, warnings, errors = self._analyze_parameters()
        print_utility.banner_warn("Parameters", pformat(known_param))
        print_utility.warn("Parameter Warnings")
        self._print_info(warnings)
        print_utility.warn("Parameter Errors")
        self._print_error(errors)
        return len(errors)

    def print_export(self):
        # type: () -> int
        known_exports, warnings, errors = self._analyze_export()
        print_utility.warn("Export Values")
        self._print_info(known_exports)
        print_utility.warn("Export Values Warnings")
        self._print_error(errors)
        return len(errors)

    def analyze(self):
        errs = self.print_known_parameters()
        errs += self.print_export()
        return errs

    def _analyze_parameters(self):
        known_param = {}
        errors = defaultdict(list)
        warning = defaultdict(list)
        with open(self.template_file, 'r') as template:
            template_obj = json.load(template)
            template_params = pydash.get(template_obj, 'Parameters', {})
            for key, value in template_params.iteritems():
                description = value.get('Description', None)
                default = value.get('Default', None)
                if not description: warning[key].append("Parameter does not contain a description")
                if default: warning[key].append(
                    "Parameter has default value defined in CloudFormation Template - {}".format(default))
                known_param[key] = {'description': description, 'type': value['Type']}
        value_to_key = {}
        with open(self.parameter_file, 'r') as params:
            param_file_params = json.load(params)
            for param in param_file_params:
                key_ = param['ParameterKey']
                if key_ in known_param:
                    known_param[key_]['variable'] = param['ParameterValue']
                    value_to_key[param['ParameterValue'].replace("$", "").replace("{", "").replace("}", "")] = key_
                    expandvars = self.deploy_ctx.expandvars(param['ParameterValue'], self.defaults)
                    if "${" in expandvars: warning[key_].append(
                        "Parameter did not appear to validate ensure it is populated when using the template - {}"
                            .format(expandvars))
                    known_param[key_]['default_value'] = expandvars
                else:
                    # exists in param file but not in template
                    errors[key_].append("Parameter does not exist in template but defined in param file")
        if self.default_path and os.path.exists(self.default_path):
            with open(self.default_path, 'r') as defs:
                defs = json.load(defs)
                for key_, param in defs.iteritems():
                    if key_ in value_to_key:
                        param_key = value_to_key[key_]
                        known_param[param_key]['default_type'] = param['type']
                        known_param[param_key].update(param)
                    else:
                        # exists in param file but not in template
                        errors[key_].append("Parameter does not exist in parameter file but defined in defaults file")

        for key, value in known_param.iteritems():
            if 'variable' not in value:
                errors[key].append("Parameter does not exist in param file but defined in template")
        return known_param, warning, errors

    def _analyze_export(self):
        known_exports = {}
        errors = defaultdict(list)
        warnings = defaultdict(list)
        with open(self.template_file, 'r') as template:
            template_obj = json.load(template)
            template_exports = pydash.get(template_obj, 'Outputs', {})
            for key, value in template_exports.iteritems():
                export = value.get('Export', None)
                value = value.get('Value', None)
                description = value.get('Description', None)
                if not description: warnings[key].append("Export does not contain a description")
                known_exports[key] = {'description': description, 'export': export, 'value': value}
        return known_exports, warnings, errors

    def print_template_description(self):
        with open(self.template_file, 'r') as template:
            template_obj = json.load(template)
            print_utility.banner_warn("Deploy for Stack: {}".format(self.stack_name),
                                      pydash.get(template_obj, 'Description', ''))

    def _print_error(self, errors):
        for key, errs in errors.iteritems():
            print_utility.error(pformat(key, indent=4))
            print_utility.banner(pformat(errs, indent=8))

    def _print_info(self, errors):
        for key, errs in errors.iteritems():
            print_utility.warn(pformat(key, indent=4))
            print_utility.banner(pformat(errs, indent=8))

    def _internal_deploy(self, dry_run):
        # Initialize our buddies
        s3 = CloudFormationDeployS3Buddy(self.deploy_ctx)
        cloud_formation = CloudFormationBuddy(self.deploy_ctx)
        if dry_run:
            self.validate()
            return
        # Upload our template to s3 to make things a bit easier and keep a record
        template_file_url = s3.upload(file=(self.template_file))
        # Upload all of our config files to S3 rendering any variables
        config_files = self.get_rendered_config_files()
        for rendered in config_files:
            s3.upload(file=rendered)
        # render our parameter files
        parameter_file_rendered = self.get_rendered_param_file()
        # see if we are updating or creating
        if cloud_formation.should_create_change_set():
            cloud_formation.create_change_set(template_file_url=template_file_url,
                                              parameter_file=parameter_file_rendered)
            # make sure it is available and that there are no special conditions
            if cloud_formation.should_execute_change_set():
                print_utility.progress("Updating existing stack with ChangeSet - {}".format(self.stack_name))
                cloud_formation.execute_change_set()
            else:
                print_utility.warn("No computed changes for stack - {}".format(self.stack_name))
                # if there are no changes then clean up and exit
                cloud_formation.delete_change_set()
                return
        else:
            print_utility.progress("Creating new stack - {}".format(self.stack_name))
            cloud_formation.create_stack(template_file_url=template_file_url,
                                         parameter_file=parameter_file_rendered)

    def get_default_params(self):
        return self._analyze_parameters()[0]
