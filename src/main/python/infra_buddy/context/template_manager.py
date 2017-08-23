import json
import os

import click

from infra_buddy.context.deploy import Deploy
from infra_buddy.context.template import URLTemplate, GitHubTemplate, NamedLocalTemplate, S3Template
from infra_buddy.utility import print_utility


class TemplateManager(object):
    deploy_templates = {}
    service_modification_templates = {}

    def __init__(self, deploy_ctx):
        # type: (DeployContext) -> None
        super(TemplateManager, self).__init__()
        self.deploy_ctx = deploy_ctx
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'builtin-templates.json'), 'r') as f:
            built_in = json.load(f)
        self._load_templates(built_in['service-templates'])
        self._load_templates(built_in['service-modification-templates'], service_modification=True)
        self._load_templates(deploy_ctx.get_deploy_templates())
        self._load_templates(deploy_ctx.get_service_modification_templates())

    def get_known_service(self, service_type):
        # type: (str) -> Deploy
        template = self.locate_service(service_type)
        return Deploy(stack_name=self.deploy_ctx.stack_name, template=template,deploy_ctx=self.deploy_ctx)

    def get_known_service_modification(self, modification_name):
        template = self.locate_service(modification_name, modification=True)
        return Deploy(stack_name=self.deploy_ctx.generate_modification_stack_name(modification_name),
                      template=template,
                      deploy_ctx=self.deploy_ctx)

    def get_resource_service(self, artifact_directory):
        try:
            template = NamedLocalTemplate(artifact_directory)
            return Deploy(stack_name=self.deploy_ctx.resource_stack_name,
                          template=template,
                          deploy_ctx=self.deploy_ctx)
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
                print_utility.error("Can not locate resource. Requested uknown template type - {}".format(type_),
                                    raise_exception=True)
