#!/usr/bin/env python3
import json
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


def test_purchase_privilege_options():
    """Test the GET /v1/purchases/privileges/options endpoint."""
    headers = get_provider_user_auth_headers_cached()
    response = requests.get(
        url=f'{config.api_base_url}/v1/purchases/privileges/options',
        headers=headers,
        timeout=10,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to get purchase privilege options. Response: {response.json()}')

    response_body = response.json()
    logger.info('Received purchase privilege options response:', data=response_body)

    compact_data = next((item for item in response_body['items'] if item.get('type') == 'compact'), None)

    # Verify compact data matches expected values
    expected_compact_data = {
        'type': 'compact',
        'compactName': 'Audiology and Speech Language Pathology',
        'compactAbbr': 'aslp',
        'compactCommissionFee': {'feeType': 'FLAT_RATE', 'feeAmount': 3.50},
        'transactionFeeConfiguration': {
            'licenseeCharges': {'active': True, 'chargeType': 'FLAT_FEE_PER_PRIVILEGE', 'chargeAmount': 3.00}
        },
    }

    if compact_data != expected_compact_data:
        raise SmokeTestFailureException(
            f'Compact data does not match expected values.\nExpected:\n {json.dumps(expected_compact_data)}\nActual:\n '
            f'{json.dumps(compact_data)}'
        )

    # now we verify the ky jurisdiction data
    # we only verify this one for brevity, since the other jurisdictions are loaded as configured in the yaml files
    ky_jurisdiction_data = next(
        (item for item in response_body['items'] if item.get('postalAbbreviation') == 'ky'), None
    )

    expected_ky_jurisdiction_data = {
        'type': 'jurisdiction',
        'jurisdictionName': 'Kentucky',
        'postalAbbreviation': 'ky',
        'compact': 'aslp',
        'jurisdictionFee': 100,
        'militaryDiscount': {'active': True, 'discountType': 'FLAT_RATE', 'discountAmount': 10},
        'jurisprudenceRequirements': {'required': True},
    }

    if ky_jurisdiction_data != expected_ky_jurisdiction_data:
        raise SmokeTestFailureException(
            f'KY jurisdiction data does not match expected values.\nExpected:\n '
            f'{json.dumps(expected_ky_jurisdiction_data)}\nActual:\n {json.dumps(ky_jurisdiction_data)}'
        )

    logger.info('Successfully verified purchase privilege options')


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
            privilege_sk = f'{compact}#PROVIDER#privilege/{privilege["jurisdiction"]}#'
            logger.info(f'Deleting privilege record:\n{privilege_pk}\n{privilege_sk}')
            dynamodb_table.delete_item(
                Key={
                    'pk': privilege_pk,
                    'sk': privilege_sk,
                }
            )
            # give dynamodb time to propagate
            time.sleep(1)

    # Get the latest version of every attestation required for the privilege purchase
    required_attestation_ids = [
        'jurisprudence-confirmation',
        'scope-of-practice-attestation',
        'personal-information-home-state-attestation',
        'personal-information-address-attestation',
        'discipline-no-current-encumbrance-attestation',
        'discipline-no-prior-encumbrance-attestation',
        'provision-of-true-information-attestation',
        'not-under-investigation-attestation',
    ]
    military_records = [
        record for record in original_provider_data.get('militaryAffiliations', []) if record['status'] == 'active'
    ]
    if military_records:
        required_attestation_ids.append('military-affiliation-confirmation-attestation')
    compact = original_provider_data.get('compact')
    attestations_from_system = []
    for attestation_id in required_attestation_ids:
        get_attestation_response = requests.get(
            url=f'{config.api_base_url}/v1/compacts/{compact}/attestations/{attestation_id}',
            headers=get_provider_user_auth_headers_cached(),
            params={'locale': 'en'},
            timeout=10,
        )

        if get_attestation_response.status_code != 200:
            raise SmokeTestFailureException(f'Failed to get attestation. Response: {get_attestation_response.json()}')

        attestation = get_attestation_response.json()
        logger.info(f'Received attestation response for {attestation_id}: {attestation}')
        attestations_from_system.append({'attestationId': attestation_id, 'version': attestation['version']})

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
        'attestations': attestations_from_system,
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
    for attestation in matching_privilege['attestations']:
        matching_attestation_from_system = next(
            (
                attestation_from_system
                for attestation_from_system in attestations_from_system
                if attestation_from_system['attestationId'] == attestation['attestationId']
            ),
            None,
        )
        if not matching_attestation_from_system:
            raise SmokeTestFailureException(f'No matching attestation found for {attestation["attestationId"]}')
        if attestation['version'] != matching_attestation_from_system['version']:
            raise SmokeTestFailureException('Attestation version in privilege record does not match')
        if attestation['version'] != attestations_from_system[0]['version']:
            raise SmokeTestFailureException(
                f'Attestation {attestation["attestationId"]} version in privilege record '
                f'does not match latest version in system'
            )

    logger.info(f'Successfully purchased privilege record: {matching_privilege}')


if __name__ == '__main__':
    test_purchase_privilege_options()
    test_purchasing_privilege()
