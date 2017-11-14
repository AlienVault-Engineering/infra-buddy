import os
import tempfile

from infra_buddy.aws import s3 as s3util
from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.aws.s3 import S3Buddy
from infra_buddy.deploy.deploy import Deploy
from infra_buddy.utility import print_utility
import datadog as dd


class DataDogMonitorDeploy(Deploy):
    def __init__(self, monitors, ctx):
        super(DataDogMonitorDeploy, self).__init__(ctx)
        self.monitors = monitors

    def _internal_deploy(self, dry_run):
        to_deploy = self.expand_monitors()
        for monitor in to_deploy:
            print_utility.info("Deploying datadog monitor: {}".format(monitor['name']))
            if not dry_run:
                self.init_dd()
                existing_id = self.find_monitor_if_exists(monitor['name'])
                if not existing_id:
                    response = dd.api.Monitor.create(**monitor)
                    created_name = response.get('name', None)
                    if created_name:
                        print_utility.info("Created monitor - {}".format(created_name))
                    else:
                        print_utility.error("Error creating monitor - {}".format(response), raise_exception=True)
                else:
                    response = dd.api.Monitor.update(id=existing_id, **monitor)
                    print_utility.info("Updated monitor - {}".format(response['name']))

    def init_dd(self):
        api_key = self.deploy_ctx.get('DATADOG_KEY', None)
        app_key = self.deploy_ctx.get('DATADOG_APP_KEY', None)
        if api_key is None or app_key is None:
            print_utility.error("Can not deploy datadog monitor without configuring DATADOG_KEY and DATADOG_APP_KEY",
                                raise_exception=True)
        dd.initialize(api_key=api_key, app_key=app_key)

    def expand_monitors(self):
        to_deploy = []
        for monitor in self.monitors:
            monitor = self.deploy_ctx.recursive_expand_vars(monitor)
            self.perform_data_checks(monitor)
            to_deploy.append(monitor)
        return to_deploy

    def __str__(self):
        return "{} - {} monitors".format(self.__class__.__name__, len(self.monitors))

    def perform_data_checks(self, monitor):
        # datadog exports more complex metric alerts are query alerts, but it wants them
        # created as metric alerts so help the user out if they just copy/pasted the datadog output
        if 'query alert' == monitor['type']:
            monitor['type'] = 'metric alert'
        monitor['name'] = self.deploy_ctx.expandvars("{}: {}".format("${ENVIRONMENT}-${APPLICATION}-${ROLE}", monitor['name']))

    def find_monitor_if_exists(self, name_):
        for mon in self.get_all_monitors_by_name(name_):
            if mon['name'] == name_:
                return mon['id']
        return None

    def get_all_monitors_by_name(self, name_):
        return dd.api.Monitor.get_all(name=name_)

    def delete_all_by_name(self, name):
        to_delete = self.get_all_monitors_by_name(name_=name)
        for mon in to_delete:
            dd.api.Monitor.delete(mon['id'])
