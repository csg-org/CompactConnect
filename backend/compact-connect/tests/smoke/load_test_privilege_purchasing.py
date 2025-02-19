# ruff: noqa: BLE001 allowing broad exception catching for load testing script
#!/usr/bin/env python3
import random
import time

import requests
from config import config, logger
from faker import Faker
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
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

name_faker = Faker(['en_US'])
faker = Faker(['en_US'])

AMEX_CARD_NUMBER = '370000000000002'

# List of valid test card numbers from Authorize.net documentation
# https://developer.authorize.net/hello_world/testing_guide.html
TEST_CARD_NUMBERS = [
    '4007000000027',  # Visa
    '4012888818888',  # Visa
    '4111111111111111',  # Visa
    '5424000000000015',  # Mastercard
    '2223000010309703',  # Mastercard
    '2223000010309711',  # Mastercard
    AMEX_CARD_NUMBER,  # American Express
    '6011000000000012',  # Discover
    '3088000000000017',  # JCB
]


def delete_existing_privileges():
    """Delete all existing privileges for the current user."""
    provider_data = call_provider_users_me_endpoint()
    privileges = provider_data.get('privileges')
    if not privileges:
        return

    provider_id = provider_data.get('providerId')
    compact = provider_data.get('compact')
    dynamodb_table = config.provider_user_dynamodb_table

    for privilege in privileges:
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

    military_records = [
        record for record in provider_data.get('militaryAffiliations', []) if record['status'] == 'active'
    ]
    if military_records:
        required_attestation_ids.append('military-affiliation-confirmation-attestation')

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


def purchase_privilege(jurisdiction: str, card_number: str, attestations: list[dict]) -> str:
    """Purchase a privilege for the given jurisdiction using the specified card number."""
    post_body = {
        'orderInformation': {
            'card': {
                'number': card_number,
                # this needs to be a random 3-digit number for everything but American Express,
                # which is 4 digits
                'cvv': str(random.randint(100, 999))
                if card_number != AMEX_CARD_NUMBER
                else str(random.randint(1000, 9999)),
                'expiration': '2050-12',
            },
            'billing': {
                'zip': '44628',
                'firstName': name_faker.first_name(),
                'lastName': name_faker.last_name(),
                'streetAddress': faker.street_address(),
                'state': faker.state_abbr(include_territories=False, include_freely_associated_states=False),
            },
        },
        'selectedJurisdictions': [jurisdiction],
        'attestations': attestations,
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
    attestations = get_required_attestations(provider_data)

    for iteration in range(num_iterations):
        logger.info(f'Starting iteration {iteration + 1} of {num_iterations}')

        try:
            # Delete existing privileges
            delete_existing_privileges()

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
                    purchase_privilege(jurisdiction, card, attestations)
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
