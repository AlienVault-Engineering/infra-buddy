import os
import tempfile
from zipfile import ZipFile

import requests
from copy import deepcopy

from infra_buddy.aws import s3
from infra_buddy.context import monitor_definition
from infra_buddy.context.monitor_definition import MonitorDefinition
from infra_buddy.utility import print_utility


class Template(object):
    def __init__(self, service_type, values, template_name='cloudformation'):
        super(Template, self).__init__()
        self.template_name = template_name
        self.service_type = service_type
        self.destination_relative = None
        self.destination = None
        self.valid = False
        self.default_env_values = values.get('default-values', {})

    def __str__(self) -> str:
        return f"Template for {self.service_type}"

    def get_default_env_values(self):
        return self.default_env_values

    def get_parameter_file_path(self):
        return os.path.join(self._get_template_location(),
                            "{template_name}.parameters.json".format(template_name=self.template_name))

    def get_defaults_file_path(self):
        return os.path.join(self._get_template_location(),
                            "defaults.json".format(service_type=self.service_type))

    def get_template_file_path(self):
        return os.path.join(self._get_template_location(),
                            "{template_name}.template".format(template_name=self.template_name))

    def get_config_dir(self):
        config_path = os.path.join(self._get_template_location(), "config")
        return config_path if os.path.exists(config_path) else None

    def get_lambda_dir(self):
        location = self._get_template_location()
        if not location: return None
        config_path = os.path.join(location, "lambda")
        return config_path if os.path.exists(config_path) else None

    def _get_template_location(self):
        return os.path.join(self.destination,
                            self.destination_relative) if self.destination_relative else self.destination

    def _validate_template_dir(self, err_on_failure_to_locate=True):
        if not os.path.exists(self.get_template_file_path()):
            if err_on_failure_to_locate: print_utility.error(f"Template file could not be located for service - "
                                                             f"{self.service_type} - {self.__str__()}",
                                                             raise_exception=True)
            return
        if not os.path.exists(self.get_parameter_file_path()):
            if err_on_failure_to_locate: print_utility.error(f"Parameter file could not be located for service  - "
                                                             f"{self.service_type} - {self.__str__()}",
                                                             raise_exception=True)
            return
        self.valid = True

    def _prep_download(self):
        if not self.destination:
            self.destination = tempfile.mkdtemp()

    def _set_download_relative_path(self, path):
        self.destination_relative = path

    def has_monitor_definition(self):
        return os.path.exists(self.get_monitor_definition_file())

    def get_monitor_artifact(self):
        return MonitorDefinition.create_from_directory(self._get_template_location())

    def get_monitor_definition_file(self):
        return os.path.join(self._get_template_location(), monitor_definition._ARTIFACT_FILE)


class URLTemplate(Template):
    def __init__(self, service_type, values):
        super(URLTemplate, self).__init__(service_type, values)
        self.download_url = values.get('url', None)

    def download_template(self):
        self._prep_download()
        URLTemplate.download_url_to_destination(self.download_url, self.destination)
        self._validate_template_dir()

    @staticmethod
    def download_url_to_destination(url, destination):
        r = requests.get(url, stream=True)
        if r.status_code != 200:
            print_utility.error("Template could not be downloaded - {url} {status} {body}".format(url=url,
                                                                                                  status=r.status_code,
                                                                                                  body=r.text))
        temporary_file = tempfile.NamedTemporaryFile()
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                temporary_file.write(chunk)
        temporary_file.seek(0)
        with ZipFile(temporary_file) as zf:
            zf.extractall(destination)


class AliasTemplate(Template):

    def __init__(self, service_type, values):
        super(AliasTemplate, self).__init__(service_type, values=values)
        self.lookup = values.get('lookup', None)
        self.delegate = None

    def __str__(self) -> str:
        return f"{super().__str__()}: Alias {self.lookup} - {self.delegate}"

    def resolve(self, templates):
        # type: (dict()) -> None
        if self.lookup in templates:
            self.delegate = templates[self.lookup]
        else:
            raise Exception("Unable to resolve alias template - {}".format(self.lookup))

    def download_template(self):
        self.delegate.download_template()

    def has_monitor_definition(self):
        return self.delegate.has_monitor_definition()

    def get_monitor_artifact(self):
        return self.delegate.get_monitor_artifact()

    def get_monitor_definition_file(self):
        return self.delegate.get_monitor_definition_file()

    def get_template_file_path(self):
        return self.delegate.get_template_file_path()

    def get_defaults_file_path(self):
        return self.delegate.get_defaults_file_path()

    def get_config_dir(self):
        return self.delegate.get_config_dir()

    def get_parameter_file_path(self):
        return self.delegate.get_parameter_file_path()

    def get_default_env_values(self):
        values = deepcopy(self.delegate.get_default_env_values())
        values.update(self.default_env_values)
        return values

    def get_root_service_type(self):
        if isinstance(self.delegate, AliasTemplate):
            return self.delegate.get_root_service_type()
        else:
            return self.delegate.service_type


class GitHubTemplate(URLTemplate):
    def __init__(self, service_type, values):
        super(GitHubTemplate, self).__init__(service_type=service_type, values=values)
        tag = values.pop('tag', 'master')
        self.download_url = "https://github.com/{owner}/{repo}/archive/{tag}.zip".format(tag=tag, **values)
        if 'relative-path' in values:
            self._set_download_relative_path("{repo}-{tag}/{relative-path}".format(tag=tag, **values))
        else:
            self._set_download_relative_path("{repo}-{tag}".format(tag=tag, **values))

    def __str__(self) -> str:
        return f"{super().__str__()}: GitHub {self.download_url}"


class GitHubTemplateDefinitionLocation(GitHubTemplate):

    def _validate_template_dir(self, err_on_failure_to_locate=True):
        if not os.path.exists(self.get_defaults_file_path()):
            if err_on_failure_to_locate: print_utility.error("Remote Defaults file could not be "
                                                             "located for service - {service_type}".format(
                service_type=self.service_type), raise_exception=True)


class NamedLocalTemplate(Template):
    def __init__(self, directory, service_type="local-template", err_on_failure_to_locate=True,
                 template_name="cloudformation"):
        super(NamedLocalTemplate, self).__init__(service_type, values={}, template_name=template_name)
        self.destination = directory
        self._validate_template_dir(err_on_failure_to_locate=err_on_failure_to_locate)

    def __str__(self) -> str:
        return f"{super().__str__()}: NamedLocalTemplate {self.destination}"


class S3Template(Template):
    def __init__(self, service_type, values):
        super(S3Template, self).__init__(service_type, values=values)
        self.s3_location = values['location']

    def download_template(self):
        self._prep_download()
        s3.download_zip_from_s3_url(self.s3_location, self.destination)

    def __str__(self) -> str:
        return f"{super().__str__()}: S3Template {self.s3_location}"


class LocalTemplate(Template):
    def __init__(self, template, parameter_file, config_dir=None, lambda_dir=None):
        super(LocalTemplate, self).__init__("", values={})
        self.lambda_dir = lambda_dir
        self.config_dir = config_dir
        self.parameter_file = parameter_file
        self.template = template

    def __str__(self) -> str:
        return f"{super().__str__()}: LocalTemplate {self.template}"

    def get_parameter_file_path(self):
        return self.parameter_file

    def get_defaults_file_path(self):
        return None

    def get_template_file_path(self):
        return self.template

    def get_config_dir(self):
        return self.config_dir

    def get_lambda_dir(self):
        return self.lambda_dir
