import os
import tempfile
from zipfile import ZipFile

import requests

from infra_buddy.aws import s3
from infra_buddy.utility import print_utility


class Template(object):
    def __init__(self, service_type):
        super(Template, self).__init__()
        self.service_type = service_type
        self.destination_relative = None
        self.destination = None
        self.valid = False

    def get_parameter_file_path(self):
        return os.path.join(self._get_template_location(),
                            "{service_type}.parameters.json".format(service_type=self.service_type))

    def get_defaults_file_path(self):
        return os.path.join(self._get_template_location(),
                            "defaults.json".format(service_type=self.service_type))

    def get_template_file_path(self):
        return os.path.join(self._get_template_location(),
                            "{service_type}.template".format(service_type=self.service_type))

    def get_config_dir(self):
        config_path = os.path.join(self._get_template_location(), "config")
        return config_path if os.path.exists(config_path) else None

    def _get_template_location(self):
        return os.path.join(self.destination,
                            self.destination_relative) if self.destination_relative else self.destination

    def _validate_template_dir(self, err_on_failure_to_locate=True):
        if not os.path.exists(self.get_template_file_path()):
            if err_on_failure_to_locate: print_utility.error("Template file could not be "
                                                             "located for service - {service_type}".format(
                service_type=self.service_type), raise_exception=True)
            return
        if not os.path.exists(self.get_parameter_file_path()):
            if err_on_failure_to_locate: print_utility.error("Parameter file could not be "
                                                             "located for service - {service_type}".format(
                service_type=self.service_type), raise_exception=True)
            return
        self.valid = True

    def _prep_download(self):
        if not self.destination:
            self.destination = tempfile.mkdtemp()

    def _set_download_relative_path(self, path):
        self.destination_relative = path


class URLTemplate(Template):
    def __init__(self, service_type, values):
        super(URLTemplate, self).__init__(service_type)
        self.download_url = values.get('url', None)

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
        super(GitHubTemplate, self).__init__(service_type=service_type, values=values)
        tag = values.pop('tag', 'master')
        self.download_url = "https://github.com/{owner}/{repo}/archive/{tag}.zip".format(tag=tag, **values)
        self._set_download_relative_path("{repo}-{tag}".format(tag=tag, **values))


class NamedLocalTemplate(Template):
    def __init__(self, directory, service_type="aws-resources", err_on_failure_to_locate=True):
        super(NamedLocalTemplate, self).__init__(service_type)
        self.destination = directory
        self._validate_template_dir(err_on_failure_to_locate=err_on_failure_to_locate)


class S3Template(Template):
    def __init__(self, service_type, values):
        super(S3Template, self).__init__(service_type)
        self.s3_location = values['location']

    def download_template(self):
        self._prep_download()
        s3.download_zip_from_s3_url(self.s3_location, self.destination)


class LocalTemplate(Template):
    def __init__(self, template, parameter_file, config_dir=None):
        super(LocalTemplate, self).__init__("")
        self.config_dir = config_dir
        self.parameter_file = parameter_file
        self.template = template

    def get_parameter_file_path(self):
        return self.parameter_file

    def get_defaults_file_path(self):
        return None

    def get_template_file_path(self):
        return self.template

    def get_config_dir(self):
        return self.config_dir
