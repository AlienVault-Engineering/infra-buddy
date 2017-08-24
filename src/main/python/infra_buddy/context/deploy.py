import json
import os
import tempfile
from collections import defaultdict
from pprint import pformat

import pydash
from jsonschema import validate

from infra_buddy.utility import helper_functions, print_utility


class Deploy(object):
    schema = {
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "value": {"type": "string"},
                "default_value": {"type": "string"},
                "key": {"type": "string"}
            },
           "required":["type"]
        }

    }

    def __init__(self, stack_name, template, deploy_ctx):
        # type: (str, Template,DeployContext) -> None
        super(Deploy, self).__init__()
        self.deploy_ctx = deploy_ctx
        self.stack_name = stack_name
        self.config_directory = template.get_config_dir()
        self.parameter_file = template.get_parameter_file_path()
        self.template_file = template.get_template_file_path()
        self.default_path = template.get_defaults_file_path()
        self._load_defaults()

    def _load_defaults(self):
        self.defaults = {}
        if self.default_path and os.path.exists(self.default_path):
            with open(self.default_path, 'r') as default_fp:
                def_obj = json.load(default_fp)
                validate(def_obj, self.schema)
            for key, value in def_obj.iteritems():
                self.defaults[key] = self._load_value(value)

    def _load_value(self, value):
        type_ = value['type']
        if type_ == "template":
            return self.deploy_ctx.expandvars(value['value'], self.defaults)
        elif type_ == "value":
            return value['value']
        elif type_ == "func":
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
        elif type_ == "property":
            return self.deploy_ctx.get(value['key'], value.get('default', None))

    def get_rendered_config_files(self, deploy_ctx):
        self._prep_render_destination()
        rendered_config_files = []
        config_dir = self.config_directory
        if config_dir:
            for template in os.listdir(config_dir):
                rendered_config_files.append(deploy_ctx.render_template(os.path.join(config_dir, template), self.destination))
        return rendered_config_files

    def get_rendered_param_file(self, deploy_ctx):
        self._prep_render_destination()
        return deploy_ctx.render_template(self.parameter_file, self.destination)

    def validate(self, deploy_ctx):
        self.print_template_description()
        self.print_known_parameters(deploy_ctx)
        self.print_export()
        config_files = self.get_rendered_config_files(deploy_ctx)
        if len(config_files) ==0:
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

    def print_known_parameters(self, deploy_ctx):
        # type: (DeployContext) -> int
        known_param, warnings,errors = self._analyze_parameters(deploy_ctx)
        print_utility.banner_warn("Parameters", pformat(known_param))
        print_utility.warn("Parameter Warnings")
        self._print_info(warnings)
        print_utility.warn("Parameter Errors")
        self._print_error(errors)
        return len(errors)

    def print_export(self):
        # type: () -> int
        known_exports, warnings,errors = self._analyze_export()
        print_utility.warn("Export Values")
        self._print_info(known_exports)
        print_utility.warn("Export Values Warnings")
        self._print_error(errors)
        return len(errors)

    def analyze(self,deploy_ctx):
        errs = self.print_known_parameters(deploy_ctx)
        errs += self.print_export()
        return errs


    def _analyze_parameters(self, deploy_ctx):
        known_param = {}
        errors = defaultdict(list)
        warning = defaultdict(list)
        with open(self.template_file, 'r') as template:
            template_obj = json.load(template)
            template_params = pydash.get(template_obj, 'Parameters', '')
            for key, value in template_params.iteritems():
                description = value.get('Description', None)
                default = value.get('Default', None)
                if not description: warning[key].append("Parameter does not contain a description")
                if default: warning[key].append("Parameter has default value defined in CloudFormation Template - {}".format(default))
                known_param[key] = {'description': description, 'type': value['Type']}
        with open(self.parameter_file, 'r') as params:
            param_file_params = json.load(params)
            for param in param_file_params:
                key_ = param['ParameterKey']
                if key_ in known_param:
                    known_param[key_]['variable'] = param['ParameterValue']
                    expandvars = deploy_ctx.expandvars(param['ParameterValue'], self.defaults)
                    if "${" in expandvars: errors[key_].append("Parameter did not appear to validate - {}".format(expandvars))
                    known_param[key_]['default_value'] = expandvars
                else:
                    # exists in param file but not in template
                    errors[key_].append("Parameter does not exist in template but defined in param file")
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
            template_exports = pydash.get(template_obj, 'Outputs', '')
            for key, value in template_exports.iteritems():
                export = value.get('Export', None)
                value = value.get('Value', None)
                description = value.get('Description', None)
                if not description: warnings[key].append("Export does not contain a description")
                known_exports[key] = {'description': description, 'export': export,'value':value}
        return known_exports, warnings, errors

    def print_template_description(self):
        with open(self.template_file, 'r') as template:
            template_obj = json.load(template)
            print_utility.banner_warn("Deploy for Stack: {}".format(self.stack_name), pydash.get(template_obj, 'Description', ''))

    def _print_error(self, errors):
        for key,errs in errors.iteritems():
            print_utility.error(pformat(key,indent=1))
            print_utility.banner(pformat(errs,indent=2))

    def _print_info(self, errors):
        for key,errs in errors.iteritems():
            print_utility.warn(pformat(key,indent=1))
            print_utility.banner(pformat(errs,indent=2))

