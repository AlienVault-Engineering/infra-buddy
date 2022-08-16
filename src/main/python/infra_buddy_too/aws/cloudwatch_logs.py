from pprint import pformat

import boto3
import pydash
from infra_buddy.utility import print_utility



class CloudwatchLogsBuddy:

    def __init__(self, deploy_ctx):
        self.deploy_ctx = deploy_ctx
        self.cwclient = None

    def _get_cloudwatch_logs_client(self):
        if not self.cwclient:
            self.cwclient = boto3.client('logs', region_name=self.deploy_ctx.region)
        return self.cwclient

    def print_latest(self):
        try:
            self.print_latest_for_group("/{ENVIRONMENT}/{APPLICATION}/{ROLE}".format(**self.deploy_ctx))
        except Exception as ex:
            print_utility.error(f"Error printing cloudwatch logs {str(ex)}")

    def print_latest_for_group(self, cloudwatchlogs_group_name):
        log_stream = self.find_latest_stream(cloudwatchlogs_group_name)
        events = self.get_events(cloudwatchlogs_group_name, log_stream)
        nextToken = events.get('nextForwardToken', None)
        to_print = self._process_events(events)
        previousToken = None
        while  previousToken!=nextToken:
            events = self.get_events(cloudwatchlogs_group_name, log_stream, nextToken=nextToken)
            previousToken = nextToken
            nextToken = events.get('nextForwardToken', None)
            to_print.extend(self._process_events(events))
        print_utility.banner_warn(f"Cloudwatch Logs {cloudwatchlogs_group_name}",
                                  ["{message}".format(**event) for event in to_print])

    def get_events(self, cloudwatchlogs_group_name, log_stream, nextToken=None):
        params = {
            "logGroupName": cloudwatchlogs_group_name,
            "logStreamName": log_stream,
            "startFromHead": True
        }
        if nextToken:
            params['nextToken'] = nextToken
        return self._get_cloudwatch_logs_client().get_log_events(**params)

    def find_latest_stream(self, cloudwatchlogs_group_name):
        streams = self._get_cloudwatch_logs_client().describe_log_streams(logGroupName=cloudwatchlogs_group_name,
                                                                          descending=True,
                                                                          limit=1,
                                                                          orderBy="LastEventTime")
        return pydash.get(streams, 'logStreams.0.logStreamName')

    def _process_events(self, events)->list:
        return events['events']
