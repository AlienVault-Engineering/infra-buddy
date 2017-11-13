import json
import os

from jsonschema import validate

from infra_buddy.deploy.datadog_monitor_deploy import DataDogMonitorDeploy
from infra_buddy.deploy.ecs_deploy import ECSDeploy
from infra_buddy.deploy.s3_deploy import S3Deploy
from infra_buddy.utility import print_utility

_DATADOG_PROVIDER = "datadog"

_MONITORS = "monitors"

_PROVIDER = "provider"

_ARTIFACT_FILE = "monitor.json"


class MonitorDefinition(object):
    schema = {
        "type": "object",
        "properties": {
            _PROVIDER: {"type": "string", "enum": [_DATADOG_PROVIDER]},
            _MONITORS: {
                "type": "array",
                "items":
                    {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "query": {"type": "string"},
                            "name": {"type": "string"},
                            "message": {"type": "string"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "options": {
                                "type": "object",
                                "properties": {
                                    "timeout_h": {"type": "number"},
                                    "notify_no_data": {"type": "boolean"},
                                    "notify_no_data_timeframe": {"type": ["string", "null"]},
                                    "notify_audit": {"type": "boolean"},
                                    "require_full_window": {"type": "boolean"},
                                    "new_host_delay": {"type": "number"},
                                    "include_tags": {"type": "boolean"},
                                    "escalation_message": {"type": "string"},
                                    "locked": {"type": "boolean"},
                                    "renotify_interval": {"type": "number"},
                                    "evaluation_delay": {"type": "number"},
                                    "thresholds": {
                                        "type": "object",
                                        "properties": {
                                            "ok": {"type": "number"},
                                            "warning": {"type": "number"},
                                            "critical": {"type": "number"}
                                        }
                                    },
                                    "silenced": {
                                        "type": "object",
                                        "patternProperties": {
                                            "^.*$": {"type": "integer"}
                                        }
                                    }

                                }

                            }
                        },
                        "required": [
                            "type",
                            "query",
                            "name"
                        ]
                    }
            }
        }
    }

    @classmethod
    def create(cls, provider=None, monitors=None):
        # type: (str, str, str) -> MonitorDefinition
        if provider == _DATADOG_PROVIDER:
            return DatadogMonitorDefinition(monitors=monitors)
        else:
            return NOOPMonitorDefinition(None)

    @classmethod
    def create_from_directory(cls, artifact_directory):
        # type: (str) -> MonitorDefinition
        definition = MonitorDefinition._load_monitor_definition(artifact_directory)
        if definition:
            validate(definition, MonitorDefinition.schema)
            return cls.create(definition[_PROVIDER], definition[_MONITORS])
        else:
            return cls.create()

    def __init__(self, monitors):
        super(MonitorDefinition, self).__init__()
        self.monitors = monitors

    @staticmethod
    def _load_monitor_definition(artifact_directory):
        artifact_def_path = os.path.join(artifact_directory, _ARTIFACT_FILE)
        if os.path.exists(artifact_def_path):
            print_utility.info("Defining artifact definition with monitor.json - {}".format(artifact_def_path))
            with open(artifact_def_path, 'r') as art_def:
                return json.load(art_def)
        else:
            print_utility.warn("Monitor definition (monitor.json) did not exist in artifact directory."
                               " Continuing infrastructure update without monitor deploy.")
        return None

    def generate_execution_plan(self, deploy_ctx):
        raise Exception("Abstract Method not implemented")

    def save_to_file(self, destination_dir=None):
        if destination_dir:
            path = os.path.join(destination_dir, _ARTIFACT_FILE)
        else:
            path = _ARTIFACT_FILE
        print_utility.info("Persisting monitor definition - {}".format(path))
        with open(path, 'w') as file:
            json.dump(self.monitors, file)
        return path

    def register_env_variables(self, deploy_ctx):
        pass


class DatadogMonitorDefinition(MonitorDefinition):
    def generate_execution_plan(self, deploy_ctx):
        return [DataDogMonitorDeploy(self.monitors, deploy_ctx)]


class NOOPMonitorDefinition(MonitorDefinition):
    def generate_execution_plan(self, deploy_ctx):
        return None
