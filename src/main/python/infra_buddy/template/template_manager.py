import json
import os

import click
from jsonschema import validate

from infra_buddy.template.template import URLTemplate, GitHubTemplate, NamedLocalTemplate, S3Template
from infra_buddy.utility import print_utility


class TemplateManager(object):
    deploy_templates = {}
    service_modification_templates = {}

    schema = {
           "type": "object",
           "additionalProperties": {
               "type": "object",
               "properties": {
                   "type": {"type": "string"},
                   "owner": {"type": "string"},
                   "repo": {"type": "string"},
                   "tag": {"type": "string"},
                   "location": {"type": "string"},
                   "url": {"type": "string"}
               },
               "required":["type"]
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
        if user_default_service_templates:self._load_templates(user_default_service_templates)
        if user_default_service_modification_tempaltes:self._load_templates(user_default_service_modification_tempaltes)

    def get_known_service(self, service_type):
        # type: (str) -> Template
        template = self.locate_service(service_type)
        return template

    def get_known_service_modification(self, modification_name):
        # type: (str) -> Template
        template = self.locate_service(modification_name, modification=True)
        return template

    def get_resource_service(self, artifact_directory):
        # type: (str) -> Template
        try:
            template = NamedLocalTemplate(artifact_directory)
            return template
        except click.UsageError as e:
            return None

    def locate_service(self, service_type, modification=False):
        # type: (str, bool) -> Template
        source = self.service_modification_templates if modification else self.deploy_templates
        template = source.get(service_type, None)
        if not template:
            print_utility.error("Unknown service template - {}".format(service_type), raise_exception=True)
        template.download_template()
        return template

    def _load_templates(self, templates, service_modification=False):
        # type: (dict, bool) -> None
        target = self.service_modification_templates if service_modification else self.deploy_templates
        for name, values in templates.iteritems():
            type_ = values['type']
            if type_ == "github":
                target[name] = GitHubTemplate(service_type=name, values=values)
            elif type_ == "s3":
                target[name] = S3Template(service_type=name, values=values)
            elif type_ == "url":
                target[name] = URLTemplate(service_type=name, values=values)
            else:
                print_utility.error("Can not locate resource. Requested unknown template type - {}".format(type_),
                                    raise_exception=True)
