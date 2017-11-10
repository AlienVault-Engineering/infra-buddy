import os
import tempfile

from infra_buddy.aws import s3
from infra_buddy.aws.cloudformation import CloudFormationBuddy
from infra_buddy.aws.s3 import S3Buddy
from infra_buddy.commandline import cli
from infra_buddy.commands.generate_artifact_manifest import command
from infra_buddy.context.artifact_definition import ArtifactDefinition
from infra_buddy.context.deploy_ctx import DeployContext
from infra_buddy.context.monitor_definition import MonitorDefinition, DatadogMonitorDefinition
from infra_buddy.deploy.cloudformation_deploy import CloudFormationDeploy
from infra_buddy.template.template import NamedLocalTemplate
from infra_buddy.utility import helper_functions
from testcase_parent import ParentTestCase


class MonitorDefinitionTestCase(ParentTestCase):
    def tearDown(self):
        pass

    @classmethod
    def setUpClass(cls):
        super(MonitorDefinitionTestCase, cls).setUpClass()

    def test_monitor_definition(self):
        monitor_directory = self._get_resource_path('monitor_definition_tests/artifact_monitor_definition')
        md = MonitorDefinition.create_from_directory(monitor_directory)
        self.assertEqual(len(md.monitors),1,"Did not parse monitors")
        self.assertTrue(isinstance(md,DatadogMonitorDefinition),"Did not return correct class")
        try:
            monitor_directory = self._get_resource_path('monitor_definition_tests/artifact_bad_monitor_definition')
            md = MonitorDefinition.create_from_directory(monitor_directory)
            self.fail("Didd not err on bad monitor def")
        except:
            pass

    def test_monitor_expansion(self):
        monitor_directory = self._get_resource_path('monitor_definition_tests/artifact_monitor_definition')
        md = MonitorDefinition.create_from_directory(monitor_directory)
        dd_deploy = md.generate_execution_plan(self.test_deploy_ctx)
        expanded = dd_deploy.expand_monitors()
        first_monitor = expanded[0]

        self.assertEqual(first_monitor['name'],
                         "{} {}-{}: ELB 500s High".format(self.test_deploy_ctx.environment,
                                                      self.test_deploy_ctx.application,
                                                      self.test_deploy_ctx.role),
                         "Did not get expanded name")
        self.assertTrue("application:{}".format(self.test_deploy_ctx.application) in first_monitor['query'],"Did not format query")
        self.assertEqual(first_monitor['tags'],["application:{}".format(self.test_deploy_ctx.application),
                                                "role:{}".format(self.test_deploy_ctx.role),
                                                'environment:{}'.format(self.test_deploy_ctx.environment)])
        self.assertEqual(first_monitor['type'],"metric alert","Did not rationalize metric type")

    def test_monitor_creation(self):
        monitor_directory = self._get_resource_path('monitor_definition_tests/artifact_monitor_definition')
        md = MonitorDefinition.create_from_directory(monitor_directory)
        dd_deploy = md.generate_execution_plan(self.test_deploy_ctx)
        expanded = dd_deploy.expand_monitors()
        first_monitor = expanded[0]
        name = first_monitor['name']
        dd_deploy.do_deploy()
        try:
            existing = dd_deploy.get_all_monitors_by_name(name)
            self.assertEqual(len(existing),1)
            #validate an update happens next time through
            dd_deploy.monitors[0]['options']['timeout_h'] = 1
            dd_deploy.do_deploy()
            existing = dd_deploy.get_all_monitors_by_name(name)
            self.assertEqual(len(existing),1)
            self.assertEqual(existing[0]['options']['timeout_h'],1,'Update failed to occur')
        finally:
            dd_deploy.delete_all_by_name(name)


        




