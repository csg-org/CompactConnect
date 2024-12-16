# ruff: noqa: S101 T201  we use asserts and print statements for smoke testing
import json

import requests
from smoke_common import (
    get_api_base_url,
    get_staff_user_auth_headers,
    load_smoke_test_env,
)

from tests.smoke.smoke_common import SmokeTestFailureException, call_provider_users_me_endpoint

# This script can be run locally to test the Query/Get Provider flow against a sandbox environment of the Compact
# Connect API. It requires that you have both a staff user and a provider user set up in the same compact of the
# sandbox environment.

# The staff user should be created **without** any 'readPrivate' permissions, as this flow is intended to test
# the general provider data retrieval flow.

# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.

def get_provider_user_smoke_test():
    """
    Verifies that a provider record can be fetched from the GET provider users endpoint of the Compact Connect API.

    Step 1: Get the provider id of the provider user profile information.
    Step 2: The staff user calls the GET provider users endpoint with the provider id.
    Step 3: Verify the Provider response matches the profile.
    """
    # Step 1: Get the provider id of the provider user profile information.
    provider_user_profile = call_provider_users_me_endpoint()
    provider_id = provider_user_profile['providerId']
    provider_compact = provider_user_profile['compact']

    # Step 2: The staff user calls the GET provider users endpoint with the provider id.
    staff_users_headers = get_staff_user_auth_headers()

    get_provider_response = requests.get(
        url=get_api_base_url() + f'/v1/compacts/{provider_compact}/providers/{provider_id}',
        headers=staff_users_headers,
        timeout=10
    )

    if get_provider_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to query provider. Response: {get_provider_response.json()}')
    print('Received success response from GET endpoint')

    # Step 3: Verify the Provider response matches the profile.
    provider_object = get_provider_response.json()

    # verify the ssn is NOT in the response
    if 'ssn' in provider_object:
        raise SmokeTestFailureException(f'unexpected ssn field returned. Response: {get_provider_response.json()}')

    # remove the fields from the user profile that are not in the query response
    provider_user_profile.pop('ssn', None)
    for provider_license in provider_user_profile['licenses']:
        provider_license.pop('ssn', None)
    for military_affiliation in provider_user_profile['militaryAffiliations']:
        military_affiliation.pop('documentKeys', None)

    if provider_object != provider_user_profile:
        raise SmokeTestFailureException(f'Provider object does not match the profile.\n'
                                        f'Profile response: {json.dumps(provider_user_profile)}\n'
                                        f'Get Provider response: {json.dumps(provider_object)}')
    print('Successfully fetched expected provider records.')

def query_provider_user_smoke_test():
    """
    Verifies that a provider record can be uploaded to the Compact Connect API and the appropriate
    records are created in the provider table as well as the data events table.

    Step 1: Get the provider id of the provider user profile information.
    Step 2: Have the staff user query for that provider using the profile information.
    Step 3: Verify the Provider response matches the profile.
    """

    # Step 1: Get the provider id of the provider user profile information.
    provider_user_profile = call_provider_users_me_endpoint()
    provider_id = provider_user_profile['providerId']
    provider_compact = provider_user_profile['compact']

    # Step 2: Have the staff user query for that provider using the profile information.
    staff_users_headers = get_staff_user_auth_headers()
    post_body = {
        'query': {'providerId': provider_id}
    }

    post_response = requests.post(
        url=get_api_base_url() + f'/v1/compacts/{provider_compact}/providers/query',
        headers=staff_users_headers,
        json=post_body,
        timeout=10
    )

    if post_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to query provider. Response: {post_response.json()}')
    print('Received success response from query endpoint')
    # Step 3: Verify the Provider response matches the profile.
    provider_object = post_response.json()['providers'][0]

    # verify the ssn is NOT in the response
    if 'ssn' in provider_object:
        raise SmokeTestFailureException(f'unexpected ssn field returned. Response: {post_response.json()}')

    # remove the fields from the user profile that are not in the query response
    provider_user_profile.pop('ssn', None)
    provider_user_profile.pop('licenses')
    provider_user_profile.pop('militaryAffiliations')
    provider_user_profile.pop('privileges')

    if provider_object != provider_user_profile:
        raise SmokeTestFailureException(f'Provider object does not match the profile.\n'
                                        f'Profile response: {provider_user_profile}\n'
                                        f'Query Provider object: {provider_object}')

    print('Successfully queried expected provider record.')




if __name__ == '__main__':
    load_smoke_test_env()
    get_provider_user_smoke_test()
    query_provider_user_smoke_test()
    print('Query provider smoke tests passed')
