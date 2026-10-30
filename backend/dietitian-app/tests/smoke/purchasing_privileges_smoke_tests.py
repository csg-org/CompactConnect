#!/usr/bin/env python3
import uuid
from datetime import UTC, datetime

import requests

# Import the existing compact configuration tests
from compact_configuration_smoke_tests import test_compact_configuration, test_jurisdiction_configuration
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
    create_test_staff_user,
    delete_existing_privilege_records,
    delete_test_staff_user,
    generate_opaque_data,
    get_license_type_abbreviation,
    get_provider_user_auth_headers_cached,
    get_provider_user_records,
    get_staff_user_auth_headers,
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
    original_provider_data = call_provider_users_me_endpoint()
    compact = original_provider_data.get('compact')
    # First, ensure we have known configuration by calling the configuration tests
    # These will set up the configurations and return them for verification
    compact_config = test_compact_configuration(compact=compact)
    jurisdiction_config = test_jurisdiction_configuration(compact=compact)

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


_CURRENT_ENCUMBRANCE_MESSAGE = (
    'You have a license or privilege that is currently encumbered, and are unable '
    'to purchase privileges at this time.'
)


def _required_attestation_ids(provider_data: dict) -> list[str]:
    required_attestation_ids = [
        'jurisprudence-confirmation',
        'scope-of-practice-attestation',
        'personal-information-home-state-attestation',
        'personal-information-address-attestation',
        'discipline-no-current-encumbrance-attestation',
        'provision-of-true-information-attestation',
        'not-under-investigation-attestation',
    ]
    provider_military_status = provider_data.get('militaryStatus', 'notApplicable')
    if provider_military_status in ('tentative', 'approved'):
        required_attestation_ids.remove('personal-information-home-state-attestation')
        required_attestation_ids.append('military-affiliation-confirmation-attestation')
        required_attestation_ids.append('military-personal-information-state-license-attestation')
    return required_attestation_ids


def _latest_attestations(compact: str, attestation_ids: list[str]) -> list[dict]:
    attestations_from_system = []
    for attestation_id in attestation_ids:
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
    return attestations_from_system


def _post_privilege_purchase(attestations_from_system: list[dict], license_type: str) -> requests.Response:
    return requests.post(
        url=config.api_base_url + '/v1/purchases/privileges',
        headers=get_provider_user_auth_headers_cached(),
        json=_generate_post_body(attestations_from_system, license_type),
        timeout=20,
    )


def _license_encumbrance_url(compact: str, provider_id: str, jurisdiction: str, license_type_abbreviation: str) -> str:
    return (
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}'
        f'/licenses/jurisdiction/{jurisdiction}/licenseType/{license_type_abbreviation}/encumbrance'
    )


def test_recently_lifted_encumbrance_does_not_block_privilege_purchase():
    """
    An encumbrance that is still in effect blocks a privilege purchase. Lifting it on the same day
    restores license eligibility immediately, and the purchase succeeds.
    """
    provider_data = call_provider_users_me_endpoint()
    licenses = provider_data.get('licenses') or []
    if not licenses:
        raise SmokeTestFailureException('Cannot encumber a license: provider has no license')

    license_record = licenses[0]
    compact = provider_data['compact']
    provider_id = provider_data['providerId']
    license_jurisdiction = license_record['jurisdiction']
    license_type = license_record['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(license_type)
    if not license_type_abbreviation:
        raise SmokeTestFailureException(f'Could not find abbreviation for license type: {license_type}')

    # The purchase below buys an 'ne' privilege. Remove any existing one so the successful purchase
    # is an issuance, and so this encumbrance does not land on the privilege we are about to buy.
    delete_existing_privilege_records(provider_id=provider_id, compact=compact, jurisdiction='ne')

    staff_email = f'test-purchase-lookback-{uuid.uuid4().hex[:8]}@ccSmokeTestFakeEmail.com'
    staff_user_sub = None
    encumbrance_id = None
    encumbrance_lifted = False
    today = datetime.now(tz=UTC).date().isoformat()
    encumbrance_url = _license_encumbrance_url(compact, provider_id, license_jurisdiction, license_type_abbreviation)

    try:
        staff_user_sub = create_test_staff_user(
            email=staff_email,
            compact=compact,
            jurisdiction=license_jurisdiction,
            permissions={'actions': {}, 'jurisdictions': {license_jurisdiction: {'admin'}}},
        )
        staff_headers = get_staff_user_auth_headers(staff_email)

        encumbrance_response = requests.post(
            encumbrance_url,
            headers=staff_headers,
            json={
                'encumbranceEffectiveDate': today,
                'encumbranceType': 'reprimand',
                'clinicalPrivilegeActionCategories': ['Unsafe Practice or Substandard Care'],
            },
            timeout=10,
        )
        if encumbrance_response.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to encumber license. Response: {encumbrance_response.status_code} '
                f'{encumbrance_response.text}'
            )

        provider_records = get_provider_user_records(compact, provider_id)
        unlifted_actions = [
            adverse_action
            for adverse_action in provider_records.get_adverse_action_records_for_license(
                license_jurisdiction, license_type_abbreviation
            )
            if adverse_action.effectiveLiftDate is None
        ]
        if len(unlifted_actions) != 1:
            raise SmokeTestFailureException(
                f'Expected 1 unlifted license adverse action after encumbering, found {len(unlifted_actions)}'
            )
        encumbrance_id = str(unlifted_actions[0].adverseActionId)

        license_after_encumbrance = provider_records.get_specific_license_record(
            license_jurisdiction, license_type_abbreviation
        )
        if license_after_encumbrance is None:
            raise SmokeTestFailureException('License not found after encumbering')
        if license_after_encumbrance.compactEligibility != 'ineligible':
            raise SmokeTestFailureException(
                'License compactEligibility should be ineligible while the encumbrance is in effect, '
                f'got {license_after_encumbrance.compactEligibility}'
            )

        attestations = _latest_attestations(compact, _required_attestation_ids(provider_data))
        blocked_purchase = _post_privilege_purchase(attestations, license_type)
        if blocked_purchase.status_code != 400:
            raise SmokeTestFailureException(
                f'Purchase should be rejected while the license is encumbered. Response: {blocked_purchase.text}'
            )
        if blocked_purchase.json().get('message') != _CURRENT_ENCUMBRANCE_MESSAGE:
            raise SmokeTestFailureException(
                f'Unexpected rejection while encumbered: {blocked_purchase.json()}'
            )

        lift_response = requests.patch(
            f'{encumbrance_url}/{encumbrance_id}',
            headers=staff_headers,
            json={'effectiveLiftDate': today},
            timeout=10,
        )
        if lift_response.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to lift license encumbrance. Response: {lift_response.status_code} {lift_response.text}'
            )
        encumbrance_lifted = True

        provider_records = get_provider_user_records(compact, provider_id)
        lifted_license = provider_records.get_specific_license_record(license_jurisdiction, license_type_abbreviation)
        if lifted_license is None:
            raise SmokeTestFailureException('License not found after lifting the encumbrance')
        if lifted_license.encumberedStatus != 'unencumbered':
            raise SmokeTestFailureException(
                f"License encumberedStatus should be 'unencumbered' after a same-day lift, "
                f'got {lifted_license.encumberedStatus}'
            )
        if lifted_license.compactEligibility != 'eligible':
            raise SmokeTestFailureException(
                'License compactEligibility should be eligible immediately after the encumbrance is lifted, '
                f'got {lifted_license.compactEligibility}'
            )
        provider_record = provider_records.get_provider_record()
        if provider_record.encumberedStatus != 'unencumbered':
            raise SmokeTestFailureException(
                f"Provider encumberedStatus should be 'unencumbered' after the lift, "
                f'got {provider_record.encumberedStatus}'
            )
        lifted_action = provider_records.get_adverse_action_by_id(unlifted_actions[0].adverseActionId)
        if lifted_action is None or str(lifted_action.effectiveLiftDate) != today:
            raise SmokeTestFailureException(
                f'Expected the adverse action to remain on record with a lift date of {today}'
            )

        logger.info('Same-day lift restored eligibility; purchasing a privilege')
        test_purchasing_privilege()
    finally:
        if encumbrance_id and not encumbrance_lifted and staff_user_sub:
            lift_response = requests.patch(
                f'{encumbrance_url}/{encumbrance_id}',
                headers=get_staff_user_auth_headers(staff_email),
                json={'effectiveLiftDate': today},
                timeout=10,
            )
            if lift_response.status_code != 200:
                logger.error(
                    'Failed to lift the smoke-test encumbrance during cleanup',
                    response=lift_response.text,
                )
        if staff_user_sub:
            delete_test_staff_user(staff_email, staff_user_sub, compact)


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
        delete_existing_privilege_records(provider_id=provider_id, compact=compact, jurisdiction='ne')

    attestations_from_system = _latest_attestations(compact, _required_attestation_ids(original_provider_data))
    license_type = original_provider_data['licenses'][0]['licenseType']
    post_api_response = _post_privilege_purchase(attestations_from_system, license_type)

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

    # check activeSince field and make sure it matches today
    active_since = matching_privilege.get('activeSince')
    if not active_since or (datetime.fromisoformat(active_since).date() != datetime.now(tz=UTC).date()):
        raise SmokeTestFailureException(f'activeSince field did not match today as expected: {active_since}')

    logger.info(f'Successfully purchased privilege record: {matching_privilege}')


if __name__ == '__main__':
    # Load environment variables from smoke_tests_env.json
    load_smoke_test_env()

    # Run tests
    test_purchase_privilege_options()
    test_recently_lifted_encumbrance_does_not_block_privilege_purchase()
    test_purchasing_privilege()
