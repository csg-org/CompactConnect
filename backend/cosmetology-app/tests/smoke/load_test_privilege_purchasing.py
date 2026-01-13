# ruff: noqa: BLE001 allowing broad exception catching for load testing script
#!/usr/bin/env python3
import time

import requests
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
    generate_opaque_data,
    get_license_type_abbreviation,
    get_provider_user_auth_headers_cached,
)

# Load-Testing Script for populating authorize.net with transactions
# This is a bit of a hack, because in order to purchase so many
# privileges with a single user we have to delete the records from
# the DB right after completing the transactions (the system does not allow you to purchase
# a privilege for the same jurisdiction twice in a row unless the home state license is updated)

# If you intend to run this script against a authorize.net sandbox account
# You will likely want to turn off the 'Hourly Velocity Filter', 'Suspicious Transaction Filter'
# and the 'Transaction IP Velocity Filter', which you can do through the Account Settings under the
# 'Fraud Detection Suite'

# List of valid test card numbers from Authorize.net documentation
# https://developer.authorize.net/hello_world/testing_guide.html
TEST_CARD_NUMBERS = [
    '4007000000027',  # Visa
    '4012888818888',  # Visa
    '4111111111111111',  # Visa
    '5424000000000015',  # Mastercard
    '2223000010309703',  # Mastercard
    '2223000010309711',  # Mastercard
    '6011000000000012',  # Discover
]


def deactivate_existing_privileges():
    """Deactivate all existing privileges for the current user by setting administratorSetStatus to 'inactive'."""
    provider_data = call_provider_users_me_endpoint()
    privileges = provider_data.get('privileges')
    if not privileges:
        return

    provider_id = provider_data.get('providerId')
    compact = provider_data.get('compact')
    dynamodb_table = config.provider_user_dynamodb_table

    for privilege in privileges:
        license_type_abbreviation = get_license_type_abbreviation(privilege['licenseType'])
        privilege_pk = f'{compact}#PROVIDER#{provider_id}'
        privilege_sk = f'{compact}#PROVIDER#privilege/{privilege["jurisdiction"]}/{license_type_abbreviation}#'
        logger.info(f'Deactivating privilege record:\n{privilege_pk}\n{privilege_sk}')

        # Update the privilege record to set administratorSetStatus to 'inactive'
        dynamodb_table.update_item(
            Key={'pk': privilege_pk, 'sk': privilege_sk},
            UpdateExpression='SET administratorSetStatus = :status',
            ExpressionAttributeValues={':status': 'inactive'},
        )
    # give dynamodb time to propagate
    time.sleep(0.5)


def get_required_attestations(provider_data: dict) -> list[dict]:
    """Get the latest version of required attestations."""
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

    compact = provider_data.get('compact')
    attestations = []

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
        attestations.append({'attestationId': attestation_id, 'version': attestation['version']})

    return attestations


def purchase_privilege(jurisdiction: str, card_number: str, attestations: list[dict], license_type: str) -> str:
    """Purchase a privilege for the given jurisdiction using the specified card number."""
    # Generate opaque data using the card number
    payment_nonce = generate_opaque_data(card_number)

    post_body = {
        'orderInformation': {'opaqueData': payment_nonce},
        'selectedJurisdictions': [jurisdiction],
        'attestations': attestations,
        'licenseType': license_type,
    }

    headers = get_provider_user_auth_headers_cached()
    post_api_response = requests.post(
        url=f'{config.api_base_url}/v1/purchases/privileges',
        headers=headers,
        json=post_body,
        timeout=20,
    )

    if post_api_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to purchase privilege. Response: {post_api_response.json()}')

    transaction_id = post_api_response.json().get('transactionId')
    logger.info(f'Successfully purchased privilege for {jurisdiction} with transaction ID: {transaction_id}')
    return transaction_id


def run_load_test(num_iterations: int):
    """Run the load test for the specified number of iterations."""
    logger.info(f'Starting load test with {num_iterations} iterations')

    # Get provider data and attestations
    provider_data = call_provider_users_me_endpoint()
    # Grab the license type from the user's first license
    license_type = provider_data['licenses'][0]['licenseType']
    attestations = get_required_attestations(provider_data)

    for iteration in range(num_iterations):
        logger.info(f'Starting iteration {iteration + 1} of {num_iterations}')

        try:
            # Deactivate existing privileges
            deactivate_existing_privileges()

            # Use different card numbers for each jurisdiction
            card_index = iteration % len(TEST_CARD_NUMBERS)
            ne_card = TEST_CARD_NUMBERS[card_index]
            oh_card = TEST_CARD_NUMBERS[(card_index + 1) % len(TEST_CARD_NUMBERS)]
            ky_card = TEST_CARD_NUMBERS[(card_index + 2) % len(TEST_CARD_NUMBERS)]

            # Purchase privileges for each jurisdiction
            jurisdictions = [
                ('ne', ne_card),
                ('oh', oh_card),
                ('ky', ky_card),
            ]

            for jurisdiction, card in jurisdictions:
                try:
                    purchase_privilege(jurisdiction, card, attestations, license_type)
                except Exception as e:
                    logger.error(f'Failed to purchase privilege for {jurisdiction} with card {card}: {str(e)}')
                    continue

            logger.info(f'Successfully completed iteration {iteration + 1}')
            # add slight delay between iterations for dynamodb to propagate
            time.sleep(0.5)

        except Exception as e:
            logger.error(f'Failed iteration {iteration + 1}: {str(e)}')
            continue


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run load tests for privilege purchasing')
    parser.add_argument('iterations', type=int, help='Number of iterations to run')
    args = parser.parse_args()

    run_load_test(args.iterations)
