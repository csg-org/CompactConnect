import json
import logging
import os
from functools import cached_property

import boto3
from aws_lambda_powertools import Logger


logging.basicConfig()
logger = Logger()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false').lower() == 'true' else logging.INFO)


class _Config():
    @property
    def api_base_url(self):
        return os.environ['CC_TEST_API_BASE_URL']

    @property
    def provider_user_dynamodb_table(self):
        return boto3.resource('dynamodb').Table(os.environ['CC_TEST_PROVIDER_DYNAMO_TABLE_NAME'])

    @property
    def data_events_dynamodb_table(self):
        return boto3.resource('dynamodb').Table(os.environ['CC_TEST_DATA_EVENT_DYNAMO_TABLE_NAME'])

    @property
    def staff_users_dynamodb_table(self):
        return boto3.resource('dynamodb').Table(os.environ['CC_TEST_STAFF_USER_DYNAMO_TABLE_NAME'])

    @property
    def cognito_staff_user_client_id(self):
        return os.environ['CC_TEST_COGNITO_STAFF_USER_POOL_CLIENT_ID']

    @property
    def cognito_staff_user_pool_id(self):
        return os.environ['CC_TEST_COGNITO_STAFF_USER_POOL_ID']

    @property
    def cognito_provider_user_client_id(self):
        return os.environ['CC_TEST_COGNITO_PROVIDER_USER_POOL_CLIENT_ID']

    @property
    def cognito_provider_user_pool_id(self):
        return os.environ['CC_TEST_COGNITO_PROVIDER_USER_POOL_ID']

    @property
    def test_provider_user_username(self):
        return os.environ['CC_TEST_PROVIDER_USER_USERNAME']

    @property
    def test_provider_user_password(self):
        return os.environ['CC_TEST_PROVIDER_USER_PASSWORD']

    @cached_property
    def cognito_client(self):
        return boto3.client('cognito-idp')

def load_smoke_test_env():
    with open(os.path.join(os.path.dirname(__file__), 'smoke_tests_env.json')) as env_file:
        env_vars = json.load(env_file)
        os.environ.update(env_vars)

load_smoke_test_env()
config = _Config()
