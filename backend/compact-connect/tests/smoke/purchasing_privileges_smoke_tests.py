#!/usr/bin/env python3
import time
from datetime import UTC, datetime

import requests
from boto3.dynamodb.conditions import Key

# Import the existing compact configuration tests
from compact_configuration_smoke_tests import (
    test_compact_configuration,
    test_jurisdiction_configuration,
    test_upload_payment_processor_credentials,
)
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
    generate_opaque_data,
    get_provider_user_auth_headers_cached,
    load_smoke_test_env,
)

# This script can be run locally to test the privilege purchasing flow against a sandbox environment
# of the Compact Connect API.
# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.


def _generate_post_body(attestations_from_system, license_type):
    # Generate a payment nonce for testing using the default test card
    payment_nonce = generate_opaque_data('4111111111111111')

    return {
        'orderInformation': {'opaqueData': payment_nonce},
        'selectedJurisdictions': ['ne'],
        'attestations': attestations_from_system,
        'licenseType': license_type,
    }


def test_purchase_privilege_options():
    """Test the GET /v1/purchases/privileges/options endpoint."""
    # First, ensure we have known configuration by calling the configuration tests
    # These will set up the configurations and return them for verification
    compact_config = test_compact_configuration()
    jurisdiction_config = test_jurisdiction_configuration()

    # Upload payment processor credentials to ensure they are available
    test_upload_payment_processor_credentials()

    # Now test the purchase privilege options endpoint
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

    # Verify compact data matches expected values based on what was set in test_compact_configuration
    expected_compact_data = {
        'type': 'compact',
        'compactName': compact_config['compactName'],
        'compactAbbr': compact_config['compactAbbr'],
        'compactCommissionFee': compact_config['compactCommissionFee'],
        'isSandbox': True,  # Should always be True in sandbox environment
    }

    # Add transaction fee config if it exists
    if 'transactionFeeConfiguration' in compact_config:
        expected_compact_data['transactionFeeConfiguration'] = compact_config['transactionFeeConfiguration']

    # Check if compact data matches our expectations
    for key, value in expected_compact_data.items():
        if key not in compact_data:
            raise SmokeTestFailureException(f'Key {key} not found in compact data')
        if compact_data[key] != value:
            raise SmokeTestFailureException(f'Value mismatch for key {key}. Expected {value}, got {compact_data[key]}')

    # Verify paymentProcessorPublicFields are present and contain expected values
    if 'paymentProcessorPublicFields' not in compact_data:
        raise SmokeTestFailureException('paymentProcessorPublicFields not found in compact data')

    payment_fields = compact_data['paymentProcessorPublicFields']

    # Verify apiLoginId matches what we uploaded
    if payment_fields.get('apiLoginId') != config.sandbox_authorize_net_api_login_id:
        raise SmokeTestFailureException(
            f'apiLoginId mismatch. Expected {config.sandbox_authorize_net_api_login_id}, '
            f'got {payment_fields.get("apiLoginId")}'
        )

    # Verify publicClientKey is present (we don't verify the exact value since it's from authorize.net)
    if not payment_fields.get('publicClientKey'):
        raise SmokeTestFailureException('publicClientKey is not present')

    # Verify the jurisdiction data (Kentucky) based on what was set in test_jurisdiction_configuration
    jurisdiction = jurisdiction_config['postalAbbreviation']
    jurisdiction_data = next(
        (item for item in response_body['items'] if item.get('postalAbbreviation') == jurisdiction), None
    )

    if not jurisdiction_data:
        raise SmokeTestFailureException(f'Jurisdiction {jurisdiction} not found in response')

    # Prepare expected jurisdiction data
    expected_jurisdiction_data = {
        'type': 'jurisdiction',
        'jurisdictionName': jurisdiction_config['jurisdictionName'],
        'postalAbbreviation': jurisdiction_config['postalAbbreviation'],
        'compact': jurisdiction_config['compact'],
        'privilegeFees': jurisdiction_config['privilegeFees'],
        'jurisprudenceRequirements': jurisdiction_config['jurisprudenceRequirements'],
    }

    # Check if jurisdiction data matches our expectations
    for key, value in expected_jurisdiction_data.items():
        if key not in jurisdiction_data:
            raise SmokeTestFailureException(
                f'Key {key} not found in jurisdiction data. \n'
                f'expected_response: {expected_jurisdiction_data}\n '
                f'actual_response: {jurisdiction_data}'
            )
        if jurisdiction_data[key] != value:
            raise SmokeTestFailureException(
                f'Value mismatch for key {key}. \n'
                f'expected_response: {value}\n '
                f'actual_response: {jurisdiction_data[key]}'
            )

    logger.info('Successfully verified purchase privilege options')


def test_purchasing_privilege(delete_current_privilege: bool = True):
    # Step 1: Get latest versions of required attestations - GET '/v1/compact/{compact}/attestations/{attestationId}'.
    # Step 2: Purchase a privilege through the POST '/v1/purchases/privileges' endpoint.
    # Step 3: Verify a transaction id is returned in the response body.
    # Step 4: Load records for provider and verify that the privilege is added to the provider's record.

    # first cleaning up user's existing 'ne' based privileges to start in a clean state
    original_provider_data = call_provider_users_me_endpoint()
    provider_id = original_provider_data.get('providerId')
    compact = original_provider_data.get('compact')
    if delete_current_privilege:
        dynamodb_table = config.provider_user_dynamodb_table
        # query for all ne related privilege records
        original_privilege_records = dynamodb_table.query(
            KeyConditionExpression=Key('pk').eq(f'{compact}#PROVIDER#{provider_id}')
            & Key('sk').begins_with(f'{compact}#PROVIDER#privilege/ne/')
        ).get('Items', [])
        for privilege in original_privilege_records:
            # delete the privilege records
            privilege_pk = privilege['pk']
            privilege_sk = privilege['sk']
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
        logger.info(f'Received attestation response for {attestation_id}')
        attestations_from_system.append({'attestationId': attestation_id, 'version': attestation['version']})

    license_type = original_provider_data['licenses'][0]['licenseType']

    post_body = _generate_post_body(attestations_from_system, license_type)

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
            raise SmokeTestFailureException(
                'Attestation version in privilege record does not match latest version in system'
            )

    logger.info(f'Successfully purchased privilege record: {matching_privilege}')


if __name__ == '__main__':
    # Load environment variables from smoke_tests_env.json
    load_smoke_test_env()

    # Run tests
    test_purchase_privilege_options()
    test_purchasing_privilege()
