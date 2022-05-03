import os
import tempfile
from zipfile import ZipFile

import requests
from copy import deepcopy

from infra_buddy.aws import s3
from infra_buddy.context import monitor_definition
from infra_buddy.context.monitor_definition import MonitorDefinition
from infra_buddy.utility import print_utility
from requests.auth import HTTPDigestAuth, HTTPBasicAuth


class Template(object):
    def __init__(self, service_type, values, template_name='cloudformation'):
        super(Template, self).__init__()
        self.template_name = template_name
        self.service_type = service_type
        self.destination_relative = None
        self.destination_base_path=None
        self.destination = None
        self.valid = False
        self.default_env_values = values.get('default-values', {})
        self.values = values

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
        for suffix in ['template','json']:
            path = os.path.join(self._get_template_location(),f"{self.template_name}.{suffix}")
            if os.path.exists(path):
                return path
        return ""

    def get_config_dir(self):
        config_path = os.path.join(self._get_template_location(), "config")
        return config_path if os.path.exists(config_path) else None

    def get_lambda_dir(self):
        location = self._get_template_location()
        if not location: return None
        config_path = os.path.join(location, "lambda")
        return config_path if os.path.exists(config_path) else None

    def _get_template_location(self):
        if not self.destination:
            return None
        parts = [self.destination]
        if self.destination_base_path:
            parts.append(self.destination_base_path)
        if self.destination_relative:
            parts.append(self.destination_relative)
        return os.path.join(*parts)

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

    def _set_download_relative_path(self, relative_path,base_path):
        self.destination_relative = relative_path
        self.destination_base_path = base_path

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

        self.auth = None
        if "private-repo" in values and values.get("private-repo"):
            auth_type = values.get("auth_type", "basic")
            user_property = values.get("user_property", "VCS_USER")
            pass_property = values.get("pass_property", "VCS_PASS")
            user = os.environ.get(user_property)
            password = os.environ.get(pass_property)
            if not password:
                password = os.environ.get("VCS_PASSWORD")
            if auth_type == "basic":
                print_utility.info(f"Auth {user}:{password}")
                self.auth = HTTPBasicAuth(username=user, password=password)
            elif auth_type == "digest":
                self.auth = HTTPDigestAuth(username=user, password=password)
            else:
                print_utility.error(f"Tried to use unsupported auth_type for private repo: {auth_type} only "
                                    f"'basic' and 'digest' supported", raise_exception=True)

    def download_template(self):
        self._prep_download()
        dl_folder_name = URLTemplate.download_url_to_destination(self.download_url, self.destination, self.auth)
        if dl_folder_name != self.destination_base_path:
            print_utility.info(f"DL: {dl_folder_name} DR: {self.destination_base_path}")
            # Bitbucket downloads a folder in the form <repo-name>-<commit-hash> instead of <repo-name>-<tag>
            self.destination_base_path = dl_folder_name
        self._validate_template_dir()

    @staticmethod
    def download_url_to_destination(url, destination, auth=None):
        r = requests.get(url, stream=True, auth=auth)
        if r.status_code != 200:
            print_utility.error("Template could not be downloaded - {url} {status} {body}".format(url=url,
                                                                                                  status=r.status_code,
                                                                                                  body=r.text),raise_exception=True)
        temporary_file = tempfile.NamedTemporaryFile()
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                temporary_file.write(chunk)
        temporary_file.seek(0)
        with ZipFile(temporary_file) as zf:
            zf.extractall(destination)
        return os.listdir(destination)[0]


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

class GitTemplate(URLTemplate):

    def __init__(self, service_type, values, url_template):
        super(GitTemplate, self).__init__(service_type=service_type, values=values)
        tag = values.pop('tag', 'master')
        self.download_url = url_template.format(tag=tag, **values)
        if 'relative-path' in values:
            self._set_download_relative_path(
                base_path="{repo}-{tag}".format(tag=tag, **values),
                relative_path="{relative-path}".format(tag=tag, **values))
        else:
            self._set_download_relative_path(base_path="{repo}-{tag}".format(tag=tag, **values),relative_path=None)

class GitHubTemplate(GitTemplate):
    def __init__(self, service_type, values):
        super(GitHubTemplate, self).__init__(service_type=service_type, values=values,
                                             url_template="https://github.com/{owner}/{repo}/archive/{tag}.zip")
    def __str__(self) -> str:
        return f"{super().__str__()}: GitHub {self.download_url}"


class GitHubTemplateDefinitionLocation(GitHubTemplate):

    def _validate_template_dir(self, err_on_failure_to_locate=True):
        if not os.path.exists(self.get_defaults_file_path()):
            if err_on_failure_to_locate: print_utility.error("Remote Defaults file could not be "
                                                             "located for service - {service_type}".format(
                service_type=self.service_type), raise_exception=True)


class BitbucketTemplate(GitTemplate):
    def __init__(self, service_type, values):
        super(BitbucketTemplate, self).__init__(service_type=service_type, values=values,
                                                url_template="https://bitbucket.org/{owner}/{repo}/get/{tag}.zip")

    def __str__(self) -> str:
        return f"{super().__str__()}: GitHub {self.download_url}"


class BitbucketTemplateDefinitionLocation(BitbucketTemplate):

    def _validate_template_dir(self, err_on_failure_to_locate=True):
        print_utility.info(f"Defaults Path: {self.get_defaults_file_path()}")
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
