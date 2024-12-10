# ruff: noqa: S101 T201  we use asserts and print statements for smoke testing
import json
import os
from datetime import UTC, datetime

import boto3
import requests

# This script can be run locally to test the privilege purchasing flow against a sandbox environment
# of the Compact Connect API.
# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.


def _call_users_me_endpoint(headers):
    # Get the provider data from the GET '/v1/provider-users/me' endpoint.
    get_provider_data_response = requests.get(
        url=os.environ['CC_TEST_API_BASE_URL'] + '/v1/provider-users/me', headers=headers, timeout=10
    )
    assert (
        get_provider_data_response.status_code == 200
    ), f'Failed to GET provider data. Response: {get_provider_data_response.json()}'
    # check the response for a top level 'privileges' field and verify it has a new record with the correct
    # jurisdiction and transaction id
    return get_provider_data_response.json()


def test_purchasing_privilege():
    # Step 1: Purchase a privilege through the POST '/v1/purchases/privileges' endpoint.
    # Step 2: Verify a transaction id is returned in the response body.
    # Step 3: Load records for provider and verify that the privilege is added to the provider's record.

    headers = {
        'Authorization': 'Bearer ' + os.environ['TEST_PROVIDER_USER_ID_TOKEN'],
    }

    # first cleaning up user's existing privileges to start in a clean state
    original_provider_data = _call_users_me_endpoint(headers)
    original_privileges = original_provider_data.get('privileges')
    if original_privileges:
        provider_id = original_provider_data.get('providerId')
        compact = original_provider_data.get('compact')
        dynamodb_table_name = os.environ['CC_TEST_PROVIDER_DYNAMO_TABLE_NAME']
        dynamodb_table = boto3.resource('dynamodb').Table(dynamodb_table_name)
        for privilege in original_privileges:
            print(f'Deleting privilege record: {privilege}')
            dynamodb_table.delete_item(
                Key={
                    'pk': f'{compact}#PROVIDER#{provider_id}',
                    'sk': f'{compact}#PROVIDER#privilege/{privilege["jurisdiction"]}'
                    f'#{datetime.fromisoformat(privilege["dateOfRenewal"]).date().isoformat()}',
                }
            )

    post_body = {
        'orderInformation': {
            'card': {
                # This test card number is defined in authorize.net's testing documentation
                # https://developer.authorize.net/hello_world/testing_guide.html
                'number': '4007000000027',
                'cvv': '123',
                'expiration': '2050-12',
            },
            'billing': {
                'zip': '44628',
                'firstName': 'Joe',
                'lastName': 'Dokes',
                'streetAddress': '14 Main Street',
                'streetAddress2': 'Apt. 12J',
                'state': 'TX',
            },
        },
        'selectedJurisdictions': ['ne'],
    }

    post_api_response = requests.post(
        url=os.environ['CC_TEST_API_BASE_URL'] + '/v1/purchases/privileges', headers=headers, json=post_body, timeout=20
    )

    assert post_api_response.status_code == 200, f'Failed to purchase privilege. Response: {post_api_response.json()}'

    transaction_id = post_api_response.json().get('transactionId')

    provider_data = _call_users_me_endpoint(headers)
    privileges = provider_data.get('privileges')
    assert privileges, 'No privileges found in provider data'
    today = datetime.now(tz=UTC).date().isoformat()
    matching_privilege = next(
        (
            privilege
            for privilege in privileges
            if datetime.fromisoformat(privilege['dateOfIssuance']).date().isoformat() == today
        ),
        None,
    )
    assert matching_privilege, f'No privilege record found for today ({today})'
    assert (
        matching_privilege['compactTransactionId'] == transaction_id
    ), 'Privilege record does not match transaction id'

    print(f'Successfully purchased privilege record: {matching_privilege}')


if __name__ == '__main__':
    with open(os.path.join(os.path.dirname(__file__), 'smoke_tests_env.json')) as env_file:
        env_vars = json.load(env_file)
        os.environ.update(env_vars)
    test_purchasing_privilege()
