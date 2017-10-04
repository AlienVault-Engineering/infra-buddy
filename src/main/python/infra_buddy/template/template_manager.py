import json
import os
from collections import defaultdict

import click
from jsonschema import validate

from infra_buddy.template.template import URLTemplate, GitHubTemplate, NamedLocalTemplate, S3Template, AliasTemplate
from infra_buddy.utility import print_utility


class TemplateManager(object):
    deploy_templates = {}
    service_modification_templates = defaultdict(dict)
    default_service_modification_templates = {}

    schema = {
        "type": "object",
        "additionalProperties": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "owner": {"type": "string"},
                "lookup": {"type": "string"},
                "default-values": {"type": "object"},
                "compatible": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "minItems": 1,
                    "uniqueItems": True
                },
                "repo": {"type": "string"},
                "tag": {"type": "string"},
                "location": {"type": "string"},
                "url": {"type": "string"}
            },
            "required": ["type"]
        }

    }

    def __init__(self, user_default_service_templates=None, user_default_service_modification_tempaltes=None):
        # type: (DeployContext) -> None
        super(TemplateManager, self).__init__()
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'builtin-templates.json'), 'r') as f:
            built_in = json.load(f)
        service_templates_ = built_in['service-templates']
        validate(service_templates_, self.schema)
        self._load_templates(service_templates_)
        modification_templates_ = built_in['service-modification-templates']
        validate(modification_templates_, self.schema)
        self._load_templates(modification_templates_, service_modification=True)
        if user_default_service_templates: self._load_templates(user_default_service_templates)
        if user_default_service_modification_tempaltes: self._load_templates(
            user_default_service_modification_tempaltes)

    def get_known_service(self, service_type):
        # type: (str) -> Template
        return self.locate_service(service_type)

    def get_known_service_modification(self, service_type, modification_name):
        # type: (str,str) -> Template
        return self.locate_service_modification(service_type=service_type, mod_type=modification_name)

    def get_service_modifications_for_service(self, service_type):
        ret = {}
        ret.update(self.service_modification_templates.get(service_type, {}))
        ret.update(self.default_service_modification_templates)
        return ret

    def get_known_template(self, template_name):
        template = self.deploy_templates.get(template_name,
                                             self.default_service_modification_templates.get(template_name))
        if not template:
            for service, template_map in self.service_modification_templates.iteritems():
                template = template_map.get(template_name, None)
        if template:
            template.download_template()
            return template
        else:
            print_utility.error("Unknown service template - {}".format(template_name), raise_exception=True)

    def get_resource_service(self, artifact_directory):
        # type: (str) -> Template
        try:
            template = NamedLocalTemplate(directory=artifact_directory,
                                          err_on_failure_to_locate=False,
                                          service_type='aws-resources',
                                          template_name='aws-resources')
            if template.valid:
                return template
            else:
                return None
        except click.UsageError as e:
            return None

    def locate_service(self, service_type):
        # type: (str, bool) -> Template
        template = self.deploy_templates.get(service_type, None)
        if not template:
            print_utility.error("Unknown service template - {}".format(service_type), raise_exception=True)
        template.download_template()
        return template

    def locate_service_modification(self, service_type, mod_type):
        # type: (str, str) -> Template
        template = self.service_modification_templates.get(service_type, {}).get(mod_type, None)
        if not template:
            template = self.default_service_modification_templates.get(mod_type, None)
        if not template:
            print_utility.error(
                "Unknown service modification '{}' for type '{}'"
                " Known modifications are {}".format(mod_type,
                                                     service_type,
                                                     self.get_service_modifications_for_service(
                                                         service_type=service_type)),
                raise_exception=True)
        template.download_template()
        return template

    def _load_templates(self, templates, service_modification=False):
        # type: (dict, bool) -> None
        alias_templates = []
        all_service_mods = {}
        for name, values in templates.iteritems():
            type_ = values['type']
            if type_ == "github":
                template = GitHubTemplate(service_type=name, values=values)
            elif type_ == "s3":
                template = S3Template(service_type=name, values=values)
            elif type_ == "url":
                template = URLTemplate(service_type=name, values=values)
            elif type_ == "alias":
                template = AliasTemplate(service_type=name, values=values)
                alias_templates.append(template)
            else:
                print_utility.error("Can not locate resource. Requested unknown template type - {}".format(type_),
                                    raise_exception=True)
                raise Exception("")
            if service_modification:
                compatibility = values.get('compatible', [])
                for service in compatibility:
                    if service == "*":
                        self.default_service_modification_templates[name] = template
                    else:
                        self.service_modification_templates[service][name] = template
                    all_service_mods[name]=(template)
            else:
                self.deploy_templates[name] = template
        for alias in alias_templates:
            alias.resolve(all_service_mods if service_modification else self.deploy_templates)

