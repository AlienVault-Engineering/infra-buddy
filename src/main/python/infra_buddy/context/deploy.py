import json
import os

from jsonschema import validate


class Deploy(object):
    schema = {
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "properties": {
                "type":  {"type": "string"},
                "value":  {"type": "string"}
            }
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
        if os.path.exists(self.default_path):
            with open(self.default_path, 'r') as default_fp:
                def_obj = json.load(default_fp)
                validate(def_obj, self.schema)
            for key, value in def_obj.iteritems():
                self.defaults[key] = self._load_value(value)

    def _load_value(self, value):
        type_ = value['type']
        if type_ == "template":
            return self.deploy_ctx.expandvars(value['value'])
        elif type_ == "value":
            return value['value']
        elif type_ == "func":
            return ""
        elif type_ == "property":
            return self.deploy_ctx.get(value['key'],value.get('default',None))