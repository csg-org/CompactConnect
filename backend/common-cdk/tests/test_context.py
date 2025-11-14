"""
Test context constants for CDK synthesis tests.

These constants provide SSM parameter lookup values in the format that CDK stores them
in cdk.context.json files. This allows tests to provide context directly to the App
constructor, avoiding the need for example context files.
"""

import json

# Base test constants
TEST_ACCOUNT_ID = '000000000000'
TEST_REGION = 'us-east-1'
TEST_ENVIRONMENT_ACCOUNT_ID = '111122223333'
TEST_GITHUB_REPO_STRING = 'owner/repo'
TEST_APP_NAME = 'test-app'
TEST_CONNECTION_ID = '12345678-1234-1234-1234-123456789012'
TEST_EMAIL = 'test@example.com'

# Construct connection ARN from base constants
TEST_CONNECTION_ARN = f'arn:aws:codestar-connections:{TEST_REGION}:{TEST_ACCOUNT_ID}:connection/{TEST_CONNECTION_ID}'


def _make_ssm_context_key(account: str, parameter_name: str, region: str) -> str:
    """
    Generate SSM context key in CDK format.

    :param account: AWS account ID
    :param parameter_name: SSM parameter name
    :param region: AWS region
    :return: SSM context key
    """
    return f'ssm:account={account}:parameterName={parameter_name}:region={region}'


def _make_deploy_context_value() -> str:
    """
    Generate deploy environment context value.

    :return: JSON string for deploy environment context
    """
    return json.dumps(
        {
            'environments': {
                'deploy': {
                    'account_id': TEST_ACCOUNT_ID,
                    'region': TEST_REGION,
                    'notifications': {'email': [TEST_EMAIL], 'slack': []},
                }
            }
        }
    )


def _make_pipeline_context_value(environment_name: str, git_tag_pattern: str) -> str:
    """
    Generate pipeline environment context value.

    :param environment_name: Environment name (test, beta, etc.)
    :param git_tag_pattern: Git tag trigger pattern
    :return: JSON string for pipeline environment context
    """
    return json.dumps(
        {
            'github_repo_string': TEST_GITHUB_REPO_STRING,
            'app_name': TEST_APP_NAME,
            'environments': {
                'pipeline': {
                    'account_id': TEST_ACCOUNT_ID,
                    'region': TEST_REGION,
                    'connection_arn': TEST_CONNECTION_ARN,
                    'git_tag_trigger_pattern': git_tag_pattern,
                },
                environment_name: {
                    'account_id': TEST_ENVIRONMENT_ACCOUNT_ID,
                    'region': TEST_REGION,
                },
            },
        }
    )


# SSM lookup context for deploy environment (used by DeploymentResourcesStack)
DEPLOY_BACKEND_CONTEXT_KEY = _make_ssm_context_key(TEST_ACCOUNT_ID, 'deploy-compact-connect-context', TEST_REGION)
DEPLOY_FRONTEND_CONTEXT_KEY = _make_ssm_context_key(TEST_ACCOUNT_ID, 'deploy-ui-compact-connect-context', TEST_REGION)

DEPLOY_BACKEND_CONTEXT_VALUE = _make_deploy_context_value()
DEPLOY_FRONTEND_CONTEXT_VALUE = DEPLOY_BACKEND_CONTEXT_VALUE

# SSM lookup context for test environment (used by BasePipelineStack)
TEST_BACKEND_CONTEXT_KEY = _make_ssm_context_key(TEST_ACCOUNT_ID, 'test-compact-connect-context', TEST_REGION)
TEST_FRONTEND_CONTEXT_KEY = _make_ssm_context_key(TEST_ACCOUNT_ID, 'test-ui-compact-connect-context', TEST_REGION)

TEST_BACKEND_CONTEXT_VALUE = _make_pipeline_context_value('test', 'test-*')
TEST_FRONTEND_CONTEXT_VALUE = TEST_BACKEND_CONTEXT_VALUE

# SSM lookup context for beta environment (used by BasePipelineStack)
BETA_BACKEND_CONTEXT_KEY = _make_ssm_context_key(TEST_ACCOUNT_ID, 'beta-compact-connect-context', TEST_REGION)
BETA_FRONTEND_CONTEXT_KEY = _make_ssm_context_key(TEST_ACCOUNT_ID, 'beta-ui-compact-connect-context', TEST_REGION)

BETA_BACKEND_CONTEXT_VALUE = _make_pipeline_context_value('beta', 'beta-*')
BETA_FRONTEND_CONTEXT_VALUE = BETA_BACKEND_CONTEXT_VALUE


def get_deploy_context(pipeline_type: str) -> dict:
    """
    Get context dictionary for deploy environment.

    :param pipeline_type: 'backend' or 'frontend'
    :return: Context dictionary with SSM lookup values
    """
    if pipeline_type == 'backend':
        return {DEPLOY_BACKEND_CONTEXT_KEY: DEPLOY_BACKEND_CONTEXT_VALUE}
    return {DEPLOY_FRONTEND_CONTEXT_KEY: DEPLOY_FRONTEND_CONTEXT_VALUE}


def get_test_context(pipeline_type: str) -> dict:
    """
    Get context dictionary for test environment.

    :param pipeline_type: 'backend' or 'frontend'
    :return: Context dictionary with SSM lookup values
    """
    if pipeline_type == 'backend':
        return {TEST_BACKEND_CONTEXT_KEY: TEST_BACKEND_CONTEXT_VALUE}
    return {TEST_FRONTEND_CONTEXT_KEY: TEST_FRONTEND_CONTEXT_VALUE}


def get_beta_context(pipeline_type: str) -> dict:
    """
    Get context dictionary for beta environment.

    :param pipeline_type: 'backend' or 'frontend'
    :return: Context dictionary with SSM lookup values
    """
    if pipeline_type == 'backend':
        return {BETA_BACKEND_CONTEXT_KEY: BETA_BACKEND_CONTEXT_VALUE}
    return {BETA_FRONTEND_CONTEXT_KEY: BETA_FRONTEND_CONTEXT_VALUE}
