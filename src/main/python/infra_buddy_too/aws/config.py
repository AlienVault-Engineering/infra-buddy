import os
from botocore.config import Config


def build_user_agent_string():
    if not os.environ.get('BITBUCKET_REPO_SLUG'):
        return "infra-buddy-too"
    else:
        env_variables = [os.environ.get('BITBUCKET_REPO_SLUG', ''),
                         os.environ.get('BITBUCKET_BRANCH', ''),
                         os.environ.get('BITBUCKET_DEPLOYMENT_ENVIRONMENT', ''),
                         os.environ.get('BITBUCKET_COMMIT', ''),
                         os.environ.get('BITBUCKET_PR_ID', '')]
    return "infra-buddy-too" + ":::".join(env_variables)


def get_boto_config():
    return Config(user_agent_extra=build_user_agent_string())
