import json
import os
from collections import defaultdict

import click
from jsonschema import validate

from infra_buddy_too.template.template import URLTemplate, GitHubTemplate, NamedLocalTemplate, S3Template, AliasTemplate, \
    GitHubTemplateDefinitionLocation, BitbucketTemplateDefinitionLocation, BitbucketTemplate
from infra_buddy_too.utility import print_utility


class TemplateManager(object):
    deploy_templates = {}
    all_service_mods = {}
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
                "private-repo": {"type": "boolean"},
                "auth-type": {"type": "string"},
                "user-property": {"type": "string"},
                "pass-property": {"type": "string"},
                "relative-path": {"type": "string"},
                "url": {"type": "string"}
            },
            "required": ["type"]
        }

    }

    def __init__(self, user_default_service_templates=None, user_default_service_modification_tempaltes=None):
        # type: (DeployContext) -> None
        super(TemplateManager, self).__init__()
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'builtin-templates.json')
        self._load_template_from_file(template_path)
        if user_default_service_templates:
            self._load_templates(user_default_service_templates)
        if user_default_service_modification_tempaltes:
            self._load_templates(user_default_service_modification_tempaltes, service_modification=True)

    def _load_template_from_file(self, template_path):
        with open(template_path, 'r') as f:
            built_in = json.load(f)
        service_templates_ = built_in['service-templates']
        self._load_templates(service_templates_)
        modification_templates_ = built_in['service-modification-templates']
        self._load_templates(modification_templates_, service_modification=True)

    def load_additional_templates(self, remote_template_definition_location):
        type_ = remote_template_definition_location['type']
        print_utility.banner_info("Loading additional templates from definition", remote_template_definition_location)
        if type_ == "github":
            remote_defaults = GitHubTemplateDefinitionLocation(service_type="remote-defaults",
                                                               values=remote_template_definition_location)
        elif type_ == 'bitbucket':
            remote_defaults = BitbucketTemplateDefinitionLocation(service_type="remote-defaults",
                                                                  values=remote_template_definition_location)
        else:
            raise Exception(f"Unsupported type for remote template {type_} - only github and bitbucket supported "
                            f"right now!")
        remote_defaults.download_template()
        self._load_template_from_file(remote_defaults.get_defaults_file_path())

    def get_known_service(self, service_type):
        # type: (str) -> Template
        return self.locate_service(service_type)

    def get_known_service_modification(self, service_type, modification_name):
        # type: (str,str) -> Template
        return self.locate_service_modification(service_type=service_type, mod_type=modification_name)

    def get_service_modifications_for_service(self, service_type):
        ret = {}
        ret.update(self.service_modification_templates.get(service_type, {}))
        # also get modifications for
        service = self.get_known_service(service_type=service_type)
        if isinstance(service, AliasTemplate):
            ret.update(self.service_modification_templates.get(service.get_root_service_type(),{}))
        ret.update(self.default_service_modification_templates)
        return ret

    def get_known_template(self, template_name):
        template = self.deploy_templates.get(
            template_name,
            self.default_service_modification_templates.get(template_name)
        )
        if not template:
            template = self.all_service_mods.get(template_name)
        if template:
            template.download_template()
            return template
        else:
            print_utility.error(
                f"Unknown service template - {template_name} "
                f"- known templates are deploy_templates={self.deploy_templates.keys()} "
                f"- service_mod_templates={self.all_service_mods.keys()}",
                raise_exception=True
            )

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
        print_utility.info(f"Locating service {service_type} - {type(template)} - {template.values}")
        template.download_template()
        return template

    def locate_service_modification(self, service_type, mod_type):
        # type: (str, str) -> Template
        template = self.get_service_modifications_for_service(service_type).get(mod_type, None)
        if not template:
            print_utility.error(
                "Unknown service modification '{}' for type '{}'"
                " Known modifications are {}".format(
                    mod_type,
                    service_type,
                    self.get_service_modifications_for_service(
                        service_type=service_type)
                ),
                raise_exception=True)
        template.download_template()
        return template

    def _load_templates(self, templates, service_modification=False):
        # type: (dict, bool) -> None
        validate(templates, self.schema)
        alias_templates = []
        for name, values in templates.items():
            type_ = values['type']
            if type_ == "github":
                template = GitHubTemplate(service_type=name, values=values)
            elif type_ == "bitbucket":
                template = BitbucketTemplate(service_type=name, values=values)
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
            print_utility.info(f"Loading template {template.service_type} - {type_}")
            if service_modification:
                compatibility = values.get('compatible', [])
                for service in compatibility:
                    if service == "*":
                        self.default_service_modification_templates[name] = template
                    else:
                        self.service_modification_templates[service][name] = template
                    self.all_service_mods[name] = template
            else:
                if name in self.deploy_templates:
                    print_utility.info(f"Overwriting existing template for service {name}: {self.deploy_templates[name]}")
                self.deploy_templates[name] = template
        for alias in alias_templates:
            alias.resolve(self.all_service_mods if service_modification else self.deploy_templates)
