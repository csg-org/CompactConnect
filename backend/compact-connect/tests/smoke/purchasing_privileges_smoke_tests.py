#!/usr/bin/env python3
import time
from datetime import UTC, datetime

import requests
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
    get_provider_user_auth_headers_cached,
)

# This script can be run locally to test the privilege purchasing flow against a sandbox environment
# of the Compact Connect API.
# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.


def test_purchasing_privilege():
    # Step 1: Get latest versions of required attestations - GET '/v1/compact/{compact}/attestations/{attestationId}'.
    # Step 2: Purchase a privilege through the POST '/v1/purchases/privileges' endpoint.
    # Step 3: Verify a transaction id is returned in the response body.
    # Step 4: Load records for provider and verify that the privilege is added to the provider's record.

    # first cleaning up user's existing privileges to start in a clean state
    original_provider_data = call_provider_users_me_endpoint()
    original_privileges = original_provider_data.get('privileges')
    if original_privileges:
        provider_id = original_provider_data.get('providerId')
        compact = original_provider_data.get('compact')
        dynamodb_table = config.provider_user_dynamodb_table
        for privilege in original_privileges:
            privilege_pk = f'{compact}#PROVIDER#{provider_id}'
            privilege_sk = (
                f'{compact}#PROVIDER#privilege/{privilege["jurisdiction"]}#'
                f'{datetime.fromisoformat(privilege["dateOfRenewal"]).date().isoformat()}'
            )
            logger.info(f'Deleting privilege record:\n{privilege_pk}\n{privilege_sk}')
            dynamodb_table.delete_item(
                Key={
                    'pk': privilege_pk,
                    'sk': privilege_sk,
                }
            )
            # give dynamodb time to propagate
            time.sleep(1)

    # Get the latest attestation version
    compact = original_provider_data.get('compact')
    attestation_id = 'jurisprudence-confirmation'
    get_attestation_response = requests.get(
        url=f'{config.api_base_url}/v1/compacts/{compact}/attestations/{attestation_id}',
        headers=get_provider_user_auth_headers_cached(),
        params={'locale': 'en'},
        timeout=10,
    )

    if get_attestation_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to get attestation. Response: {get_attestation_response.json()}')
    logger.info(f'Received attestation response: {get_attestation_response.json()}')

    attestation = get_attestation_response.json()
    attestation_version = attestation.get('version')

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
        'attestations': [{'attestationId': attestation_id, 'version': attestation_version}],
    }

    headers = get_provider_user_auth_headers_cached()
    post_api_response = requests.post(
        url=config.api_base_url + '/v1/purchases/privileges', headers=headers, json=post_body, timeout=20
    )

    if post_api_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to purchase privilege. Response: {post_api_response.json()}')

    transaction_id = post_api_response.json().get('transactionId')

    provider_data = call_provider_users_me_endpoint()
    privileges = provider_data.get('privileges')
    if not privileges:
        raise SmokeTestFailureException('No privileges found in provider data')
    today = datetime.now(tz=UTC).date().isoformat()
    matching_privilege = next(
        (
            privilege
            for privilege in privileges
            if datetime.fromisoformat(privilege['dateOfIssuance']).date().isoformat() == today
        ),
        None,
    )
    if not matching_privilege:
        raise SmokeTestFailureException(f'No privilege record found for today ({today})')
    if matching_privilege['compactTransactionId'] != transaction_id:
        raise SmokeTestFailureException('Privilege record does not match transaction id')
    if not matching_privilege.get('attestations'):
        raise SmokeTestFailureException('No attestations found in privilege record')
    if matching_privilege['attestations'][0]['attestationId'] != attestation_id:
        raise SmokeTestFailureException('Attestation ID in privilege record does not match')
    if matching_privilege['attestations'][0]['version'] != attestation_version:
        raise SmokeTestFailureException('Attestation version in privilege record does not match')

    logger.info(f'Successfully purchased privilege record: {matching_privilege}')


if __name__ == '__main__':
    test_purchasing_privilege()
