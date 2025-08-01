# ruff: noqa: S101 T201  we use asserts and print statements for smoke testing
import json

import requests
from config import config, logger
from deepdiff import DeepDiff
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


TEST_STAFF_USER_EMAIL = 'testStaffUserQuerySmokeTests@smokeTestFakeEmail.com'


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
    get_provider_general_provider_object = get_provider_response.json()

    # verify the ssn is NOT in the response
    if 'ssn' in get_provider_general_provider_object:
        raise SmokeTestFailureException(f'unexpected ssn field returned. Response: {get_provider_response.json()}')

    # remove the fields from the user profile that are not in the query response
    test_user_profile.pop('ssnLastFour', None)
    test_user_profile.pop('dateOfBirth', None)
    test_user_profile.pop('encumberedStatus', None)
    for provider_license in test_user_profile['licenses']:
        provider_license.pop('ssnLastFour', None)
        provider_license.pop('dateOfBirth', None)
        provider_license.pop('encumberedStatus', None)
        for history_event in provider_license['history']:
            history_event['previous'].pop('ssnLastFour', None)
            history_event['previous'].pop('dateOfBirth', None)
            history_event['previous'].pop('encumberedStatus', None)
    for military_affiliation in test_user_profile['militaryAffiliations']:
        military_affiliation.pop('documentKeys', None)

    if get_provider_general_provider_object != test_user_profile:
        formatted_test_user_profile = json.dumps(test_user_profile, sort_keys=True, indent=4)
        formatted_get_provider_response = json.dumps(get_provider_general_provider_object, sort_keys=True, indent=4)
        logger.error(
            'Provider object does not match the profile.',
            provider_profile=formatted_test_user_profile,
            get_provider_response=formatted_get_provider_response,
            diff=DeepDiff(test_user_profile, get_provider_general_provider_object),
        )
        raise SmokeTestFailureException('Get provider object response does not match the profile.')
    logger.info('Successfully fetched expected provider records.')


def query_provider_user_smoke_test():
    """
    Verifies that a provider record can be queried .

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
    providers = post_response.json()['providers']
    if not providers:
        raise SmokeTestFailureException(f'No providers returned by query. Response: {post_response.json()}')

    provider_object = providers[0]

    # verify the ssn is NOT in the response
    if 'ssn' in provider_object:
        raise SmokeTestFailureException(f'unexpected ssn field returned. Response: {post_response.json()}')

    # remove the fields from the user profile that are not in the query response
    test_user_profile.pop('ssnLastFour', None)
    test_user_profile.pop('dateOfBirth', None)
    test_user_profile.pop('licenses')
    test_user_profile.pop('militaryAffiliations')
    test_user_profile.pop('privileges')
    test_user_profile.pop('encumberedStatus', None)

    if provider_object != test_user_profile:
        raise SmokeTestFailureException(
            f'Provider list object does not match the profile.\n{DeepDiff(test_user_profile, provider_object)}'
        )

    logger.info('Successfully queried expected provider record.')


def get_provider_data_with_read_private_access_smoke_test(test_staff_user_id: str):
    """
    Verifies that a staff user can read private fields of a provider record if they have the 'readPrivate' permission.

    Step 1: Update the staff user's permissions using the PATCH '/v1/staff-users/me/permissions' endpoint to include
    the 'readPrivate' permission.
    Step 2: Generate a new token and call the GET provider users endpoint with the new token.
    Step 3: Verify the Provider response matches the profile.
    """

    # Step 1: Get the provider user profile information.
    test_user_profile = call_provider_users_me_endpoint()
    provider_id = provider_user_profile['providerId']
    compact = provider_user_profile['compact']
    # Step 1: Update the staff user's permissions using the PATCH '/v1/staff-users/me/permissions' endpoint.
    staff_users_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
    patch_body = {'permissions': {'aslp': {'actions': {'readPrivate': True}}}}
    patch_response = requests.patch(
        url=config.api_base_url + f'/v1/compacts/{compact}/staff-users/{test_staff_user_id}',
        headers=staff_users_headers,
        json=patch_body,
        timeout=10,
    )

    if patch_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to PATCH staff user permissions. Response: {patch_response.json()}')
    logger.info('Successfully updated staff user permissions.')

    # Step 2: Generate a new token and call the GET provider users endpoint with the new token.
    staff_users_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
    get_provider_response = requests.get(
        url=config.api_base_url + f'/v1/compacts/{compact}/providers/{provider_id}',
        headers=staff_users_headers,
        timeout=10,
    )

    if get_provider_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to GET staff user. Response: {get_provider_response.json()}')

    logger.info('Received success response from GET endpoint')

    # Step 3: Verify the Provider response matches the profile.
    provider_object = get_provider_response.json()
    # because this test staff user is a compact admin, there will be download links present for the
    # military affiliation files, so we need to account for those here by removing them from the
    # list of military records and checking the links to verify they are valid
    for record in provider_object['militaryAffiliations']:
        if 'downloadLinks' in record.keys():
            download_links = record.pop('downloadLinks')
            # Verify the download link is valid and can download the file
            for download_link in download_links:
                if 'url' not in download_link or 'fileName' not in download_link:
                    raise SmokeTestFailureException(f'Invalid download link structure: {download_link}')

                # Attempt to download the file using the pre-signed URL
                logger.info(f'downloading test file from {download_link["url"]}')
                download_response = requests.get(download_link['url'], timeout=30)
                if download_response.status_code != 200:
                    raise SmokeTestFailureException(
                        f'Failed to download file from pre-signed URL. Status code: {download_response.status_code}, '
                        f'URL: {download_link["url"]}, File name: {download_link["fileName"]}'
                    )
                logger.info(f'Successfully downloaded file: {download_link["fileName"]}')
        else:
            raise SmokeTestFailureException(
                f'Missing expected download links for military affiliation. Military affiliation: {record}'
            )

    if provider_object != test_user_profile:
        raise SmokeTestFailureException(
            f'Provider object does not match the profile.\n{DeepDiff(test_user_profile, provider_object)}'
        )

    logger.info('Successfully fetched expected user profile.')


if __name__ == '__main__':
    load_smoke_test_env()
    provider_user_profile = call_provider_users_me_endpoint()
    provider_compact = provider_user_profile['compact']
    # ensure the test staff user is in the same compact as the test provider user without 'readPrivate' permissions
    test_user_sub = create_test_staff_user(
        email=TEST_STAFF_USER_EMAIL,
        compact=provider_compact,
        jurisdiction='oh',
        permissions={'actions': {'admin'}, 'jurisdictions': {'oh': {'write', 'admin'}}},
    )
    try:
        get_general_provider_user_data_smoke_test()
        query_provider_user_smoke_test()
        get_provider_data_with_read_private_access_smoke_test(test_staff_user_id=test_user_sub)
        logger.info('Query provider smoke tests passed')
    except SmokeTestFailureException as e:
        logger.error(f'Query provider smoke tests failed: {str(e)}')
    finally:
        delete_test_staff_user(TEST_STAFF_USER_EMAIL, user_sub=test_user_sub, compact=provider_compact)
