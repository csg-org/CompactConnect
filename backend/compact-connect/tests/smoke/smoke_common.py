import json
import os

import boto3
import requests


class SmokeTestFailureException(Exception):
    """
    Custom exception to raise when a smoke test fails.
    """

    def __init__(self, message):
        super().__init__(message)


def get_provider_user_auth_headers():
    return {
        'Authorization': 'Bearer ' + os.environ['TEST_PROVIDER_USER_ID_TOKEN'],
    }


def get_staff_user_auth_headers():
    return {
        'Authorization': 'Bearer ' + os.environ['TEST_STAFF_USER_ACCESS_TOKEN'],
    }


def get_api_base_url():
    return os.environ['CC_TEST_API_BASE_URL']


def get_provider_user_dynamodb_table():
    return boto3.resource('dynamodb').Table(os.environ['CC_TEST_PROVIDER_DYNAMO_TABLE_NAME'])


def get_data_events_dynamodb_table():
    return boto3.resource('dynamodb').Table(os.environ['CC_TEST_DATA_EVENT_DYNAMO_TABLE_NAME'])


def load_smoke_test_env():
    with open(os.path.join(os.path.dirname(__file__), 'smoke_tests_env.json')) as env_file:
        env_vars = json.load(env_file)
        os.environ.update(env_vars)


def call_provider_users_me_endpoint():
    # Get the provider data from the GET '/v1/provider-users/me' endpoint.
    get_provider_data_response = requests.get(
        url=get_api_base_url() + '/v1/provider-users/me', headers=get_provider_user_auth_headers(), timeout=10
    )
    if get_provider_data_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to GET provider data. Response: {get_provider_data_response.json()}')
    # return the response body
    return get_provider_data_response.json()
