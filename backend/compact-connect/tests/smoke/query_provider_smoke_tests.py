# ruff: noqa: S101 T201  we use asserts and print statements for smoke testing
import json

import requests
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
    create_test_staff_user,
    delete_test_staff_user,
    get_staff_user_auth_headers,
    load_smoke_test_env,
)

# This script can be run locally to test the Query/Get Provider flow against a sandbox environment of the Compact
# Connect API. It requires that you have a provider user set up in the same compact of the sandbox environment.
# Your sandbox account must also be deployed with the "security_profile": "VULNERABLE" setting in your cdk.context.json
# file, which allows you to log in users using the boto3 Cognito client.

# The staff user should be created **without** any 'readPrivate' permissions, as this flow is intended to test
# the general provider data retrieval flow.

# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.


TEST_STAFF_USER_EMAIL = 'testStaffUser@fakeemail.com'


def get_general_provider_user_data_smoke_test():
    """
    Verifies that a provider record can be fetched from the GET provider users endpoint with private fields sanitized.

    Step 1: Get the provider id of the provider user profile information.
    Step 2: The staff user calls the GET provider users endpoint with the provider id.
    Step 3: Verify the Provider response matches the profile.
    """
    # Step 1: Get the provider id of the provider user profile information.
    test_user_profile = call_provider_users_me_endpoint()
    provider_id = provider_user_profile['providerId']
    compact = provider_user_profile['compact']

    # Step 2: The staff user calls the GET provider users endpoint with the provider id.
    # create staff user without 'readPrivate' permissions
    staff_users_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)

    get_provider_response = requests.get(
        url=config.api_base_url + f'/v1/compacts/{compact}/providers/{provider_id}',
        headers=staff_users_headers,
        timeout=10,
    )

    if get_provider_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to query provider. Response: {get_provider_response.json()}')
    logger.info('Received success response from GET endpoint')

    # Step 3: Verify the Provider response matches the profile.
    provider_object = get_provider_response.json()

    # verify the ssn is NOT in the response
    if 'ssn' in provider_object:
        raise SmokeTestFailureException(f'unexpected ssn field returned. Response: {get_provider_response.json()}')

    # remove the fields from the user profile that are not in the query response
    test_user_profile.pop('ssn', None)
    test_user_profile.pop('dateOfBirth', None)
    for provider_license in test_user_profile['licenses']:
        provider_license.pop('ssn', None)
        provider_license.pop('dateOfBirth', None)
    for military_affiliation in test_user_profile['militaryAffiliations']:
        military_affiliation.pop('documentKeys', None)

    if provider_object != test_user_profile:
        raise SmokeTestFailureException(
            f'Provider object does not match the profile.\n'
            f'Profile response: {json.dumps(test_user_profile)}\n'
            f'Get Provider response: {json.dumps(provider_object)}'
        )
    logger.info('Successfully fetched expected provider records.')


def query_provider_user_smoke_test():
    """
    Verifies that a provider record can be uploaded to the Compact Connect API and the appropriate
    records are created in the provider table as well as the data events table.

    Step 1: Get the provider id of the provider user profile information.
    Step 2: Have the staff user query for that provider using the profile information.
    Step 3: Verify the Provider response matches the profile.
    """

    # Step 1: Get the provider id of the provider user profile information.
    test_user_profile = call_provider_users_me_endpoint()
    provider_id = provider_user_profile['providerId']
    compact = provider_user_profile['compact']

    # Step 2: Have the staff user query for that provider using the profile information.
    staff_users_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
    post_body = {'query': {'providerId': provider_id}}

    post_response = requests.post(
        url=config.api_base_url + f'/v1/compacts/{compact}/providers/query',
        headers=staff_users_headers,
        json=post_body,
        timeout=10,
    )

    if post_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to query provider. Response: {post_response.json()}')
    logger.info('Received success response from query endpoint')
    # Step 3: Verify the Provider response matches the profile.
    provider_object = post_response.json()['providers'][0]

    # verify the ssn is NOT in the response
    if 'ssn' in provider_object:
        raise SmokeTestFailureException(f'unexpected ssn field returned. Response: {post_response.json()}')

    # remove the fields from the user profile that are not in the query response
    test_user_profile.pop('ssn', None)
    test_user_profile.pop('dateOfBirth', None)
    test_user_profile.pop('licenses')
    test_user_profile.pop('militaryAffiliations')
    test_user_profile.pop('privileges')

    if provider_object != test_user_profile:
        raise SmokeTestFailureException(
            f'Provider object does not match the profile.\n'
            f'Profile response: {test_user_profile}\n'
            f'Query Provider object: {provider_object}'
        )

    logger.info('Successfully queried expected provider record.')



if __name__ == '__main__':
    load_smoke_test_env()
    provider_user_profile = call_provider_users_me_endpoint()
    provider_compact = provider_user_profile['compact']
    # ensure the test staff user is in the same compact as the test provider user without 'readPrivate' permissions
    test_user_sub = create_test_staff_user(email=TEST_STAFF_USER_EMAIL, compact=provider_compact, jurisdiction='oh',
                           permissions={'actions': {'admin'}, 'jurisdictions': {'oh': {'write', 'admin'}}})
    try:
        get_general_provider_user_data_smoke_test()
        query_provider_user_smoke_test()
        logger.info('Query provider smoke tests passed')
    except SmokeTestFailureException as e:
        logger.error(f'Query provider smoke tests failed: {str(e)}')
    finally:
        delete_test_staff_user(TEST_STAFF_USER_EMAIL, user_sub=test_user_sub, compact=provider_compact)

