import os

from pybuilder.core import init, use_plugin

use_plugin("python.core")
use_plugin("python.install_dependencies")
# use_plugin("python.coverage")
use_plugin("python.distutils")
use_plugin("exec")
use_plugin("python.unittest")
use_plugin("python.pylint")
use_plugin("copy_resources")
use_plugin("python.pycharm")
default_task = "publish"
requires_python = ">=3.6.0"

name = "infra-buddy-too"


@init
def initialize(project):

    build_number = project.get_property("build_number",os.environ.get('GITHUB_RUN_NUMBER',
                                                                      os.environ.get('TRAVIS_BUILD_NUMBER')))
    if build_number is not None and "" != build_number:
        project.version = build_number
    else:
        project.version = "0.0.999"

    # Project Manifest
    project.name = "infra-buddy-too"
    project.summary = "CLI for deploying micro-services"
    project.home_page = "https://github.com/Nudge-Security/infra-buddy"
    project.description = "CLI for deploying micro-services"
    project.author = "Nudge Security"
    project.license = "Apache 2.0"
    project.url = "https://github.com/Nudge-Security/infra-buddy"
    project.depends_on_requirements("requirements.txt")
    # Build and test settings
    #disable testing for now
    project.set_property('unittest_module_glob', 'test_*')
    # project.set_property("run_unit_tests_propagate_stdout", True)
    # project.set_property("run_unit_tests_propagate_stderr", True)
    project.set_property("coverage_branch_threshold_warn", 0)
    project.set_property("coverage_branch_partial_threshold_warn", 0)
    project.include_file('infra_buddy_too', "template/builtin-templates.json")
