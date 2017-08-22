import json
import os
import tempfile
from zipfile import ZipFile

import click
import requests

from infra_buddy.aws import s3
from infra_buddy.context.deploy import Deploy
from infra_buddy.utility import print_utility


class Template(object):
    def __init__(self, service_type):
        super(Template, self).__init__()
        self.service_type = service_type
        self.destination_relative = None

    def get_parameter_file_path(self):
        return os.path.join(self._get_template_location(),
                            "{service_type}.parameters.json".format(service_type=self.service_type))

    def get_template_file_path(self):
        return os.path.join(self._get_template_location(), "{service_type}.template".format(service_type=self.service_type))

    def get_config_dir(self):
        config_path = os.path.join(self._get_template_location(), "config")
        return config_path if os.path.exists(config_path) else None

    def _get_template_location(self):
        return os.path.join(self.destination,self.destination_relative) if self.destination_relative else self.destination

    def _validate_template_dir(self):
        if not os.path.exists(self.get_template_file_path()):
            print_utility.error("Template file could not be located for service - {service_type}".format(
                service_type=self.service_type), raise_exception=True)
        if not os.path.exists(self.get_parameter_file_path()):
            print_utility.error("Parameter file could not be located for service - {service_type}".format(
                service_type=self.service_type), raise_exception=True)

    def _prep_download(self):
        self.destination = tempfile.mkdtemp()

    def _set_download_relative_path(self,path):
        self.destination_relative = path


class URLTemplate(Template):
    def __init__(self, service_type, values):
        super(URLTemplate, self).__init__(service_type)
        self.download_url = values.get('url',None)

    def download_template(self):
        self._prep_download()
        r = requests.get(self.download_url, stream=True)
        temporary_file = tempfile.NamedTemporaryFile()
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                temporary_file.write(chunk)
        temporary_file.seek(0)
        with ZipFile(temporary_file) as zf:
            zf.extractall(self.destination)
        self._validate_template_dir()


class GitHubTemplate(URLTemplate):

    def __init__(self, service_type, values):
        super(GitHubTemplate, self).__init__(service_type=service_type,values=values)
        tag = values.get('tag', 'master')
        self.download_url = "https://github.com/{owner}/{repo}/archive/{tag}.zip".format(tag=tag, **values)
        self._set_download_relative_path("{repo}-{tag}".format(tag=tag,**values))


class AWSResourceTemplate(Template):
    def __init__(self, directory):
        super(AWSResourceTemplate, self).__init__("aws-resources")
        self.destination = directory
        self._validate_template_dir()


class S3Template(Template):
    def __init__(self, service_type, values):
        super(S3Template, self).__init__(service_type)
        self.s3_location = values['location']

    def download_template(self):
        self._prep_download()
        s3.download_zip_from_s3_url(self.s3_location, self.destination)


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
        return Deploy(stack_name=self.deploy_ctx.stack_name, template=template)

    def get_known_service_modification(self, modification_name):
        template = self.locate_service(modification_name, modification=True)
        return Deploy(stack_name=self.deploy_ctx.generate_modification_stack_name(modification_name),
                      template=template)

    def get_resource_service(self, artifact_directory):
        try:
            template = AWSResourceTemplate(artifact_directory)
            return Deploy(self.deploy_ctx.resource_stack_name, template)
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
