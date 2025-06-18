#!/usr/bin/env python3
"""
Smoke tests for encumbrance functionality.

This script tests the end-to-end encumbrance workflow for both licenses and privileges,
including setting encumbrances and lifting them through the API endpoints.
"""

import time

import requests
from purchasing_privileges_smoke_tests import test_purchasing_privilege
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
    config,
    create_test_staff_user,
    delete_test_staff_user,
    get_all_provider_database_records,
    get_license_type_abbreviation,
    get_provider_user_dynamodb_table,
    get_staff_user_auth_headers,
    load_smoke_test_env,
    logger,
)


def _generate_license_encumbrance_url(
    compact: str, provider_id: str, jurisdiction: str, license_type_abbreviation: str, encumbrance_id: str = None
):
    base_url = (
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}'
        f'/licenses/jurisdiction/{jurisdiction}/licenseType/{license_type_abbreviation}/encumbrance'
    )
    if encumbrance_id:
        return f'{base_url}/{encumbrance_id}'
    return base_url


def _generate_privilege_encumbrance_url(
    compact: str, provider_id: str, jurisdiction: str, license_type_abbreviation: str, encumbrance_id: str = None
):
    base_url = (
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}'
        f'/privileges/jurisdiction/{jurisdiction}/licenseType/{license_type_abbreviation}/encumbrance'
    )
    if encumbrance_id:
        return f'{base_url}/{encumbrance_id}'
    return base_url


def clean_adverse_actions():
    """
    Clean up any existing adverse action records for the provider to start in a clean state.
    """
    logger.info('Cleaning up existing adverse action records...')

    # Get all provider database records
    all_records = get_all_provider_database_records()

    # Filter for adverse action records
    adverse_action_records = [record for record in all_records if record.get('type') == 'adverseAction']

    if not adverse_action_records:
        logger.info('No adverse action records found to clean up')
        return

    # Delete each adverse action record
    dynamodb_table = get_provider_user_dynamodb_table()
    for record in adverse_action_records:
        pk = record['pk']
        sk = record['sk']
        logger.info(f'Deleting adverse action record: {pk} / {sk}')
        dynamodb_table.delete_item(Key={'pk': pk, 'sk': sk})

    logger.info(f'Cleaned up {len(adverse_action_records)} adverse action records')


def _remove_encumbered_status_from_license_and_provider():
    # Get all provider database records
    all_records = get_all_provider_database_records()

    for record in all_records:
        if record.get('type') == 'license' or record.get('type') == 'provider':
            if record.get('encumberedStatus') == 'encumbered':
                logger.info(
                    f'Removing encumbered status from {record.get("type")} {record.get("pk")} / {record.get("sk")}'
                )
                dynamodb_table = get_provider_user_dynamodb_table()
                dynamodb_table.update_item(
                    Key={'pk': record['pk'], 'sk': record['sk']},
                    UpdateExpression='SET encumberedStatus = :unencumbered',
                    ExpressionAttributeValues={':unencumbered': 'unencumbered'},
                )


def setup_test_environment():
    """
    Set up the test environment by cleaning adverse actions and purchasing a privilege.
    """
    logger.info('Setting up test environment...')

    # Clean up any existing adverse actions
    clean_adverse_actions()

    # remove encumbered status from license and provider if present
    _remove_encumbered_status_from_license_and_provider()

    # Purchase a privilege to ensure we have one to test with
    logger.info('Purchasing a privilege for testing...')
    test_purchasing_privilege()

    logger.info('Test environment setup complete')


def create_test_staff_user_for_encumbrance(compact: str, jurisdiction: str):
    """
    Create a test staff user with permissions to create and lift encumbrances.
    """
    email = f'test-encumbrance-admin-{jurisdiction}@ccSmokeTestFakeEmail.com'
    user_sub = create_test_staff_user(
        email=email,
        compact=compact,
        jurisdiction=jurisdiction,
        permissions={'actions': {}, 'jurisdictions': {jurisdiction: {'admin'}}},
    )

    return email, user_sub


def _get_license_data_from_provider_response(provider_data: dict, jurisdiction: str, license_type: str):
    return next(
        (
            lic
            for lic in provider_data['licenses']
            if lic['jurisdiction'] == jurisdiction and lic['licenseType'] == license_type
        ),
        None,
    )


def _get_privilege_data_from_provider_response(provider_data: dict, jurisdiction: str):
    privileges = provider_data.get('privileges', [])
    if not privileges:
        raise SmokeTestFailureException('No privileges found for provider')

    return next((privilege for privilege in privileges if privilege['jurisdiction'] == jurisdiction), None)


def _validate_privilege_encumbered_status(
    expected_status: str,
    test_jurisdiction: str,
    test_license_type: str,
    max_wait_time: int = 60,
    check_interval: int = 10,
):
    """
    Validate that the privilege encumberedStatus matches the expected value.

    This method will poll the provider me endpoint every check_interval seconds
    for up to max_wait_time seconds, checking if the privilege has the expected
    encumberedStatus. This accounts for eventual consistency in downstream processing.

    :param expected_status: The expected encumberedStatus value ('licenseEncumbered', 'unencumbered', etc.)
    :param test_jurisdiction: The jurisdiction of the license that was encumbered/unencumbered
    :param test_license_type: The license type that was encumbered/unencumbered
    :param max_wait_time: Maximum time to wait in seconds (default: 60)
    :param check_interval: Time between checks in seconds (default: 10)

    :raises:
        :class:`~smoke_common.SmokeTestFailureException`: If the privilege status doesn't match within max_wait_time
    """
    logger.info(
        f'Validating privilege encumbered status is "{expected_status}" for jurisdiction "{test_jurisdiction}"...'
    )

    start_time = time.time()
    attempts = 0
    max_attempts = max_wait_time // check_interval

    while attempts < max_attempts:
        attempts += 1

        try:
            # Get current provider data
            provider_data = call_provider_users_me_endpoint()

            # Find the privilege that matches the license jurisdiction and type
            privileges = provider_data.get('privileges', [])
            matching_privilege = None

            for privilege in privileges:
                # Match by license jurisdiction and license type
                if (
                    privilege.get('licenseJurisdiction') == test_jurisdiction
                    and privilege.get('licenseType') == test_license_type
                ):
                    matching_privilege = privilege
                    break

            if not matching_privilege:
                logger.warning(
                    f'Attempt {attempts}/{max_attempts}: No privilege found matching license jurisdiction '
                    f'"{test_jurisdiction}" and license type "{test_license_type}"'
                )
            else:
                actual_status = matching_privilege.get('encumberedStatus')
                logger.info(
                    f'Attempt {attempts}/{max_attempts}: Privilege encumberedStatus is "{actual_status}", expecting '
                    f'"{expected_status}"'
                )

                if actual_status == expected_status:
                    elapsed_time = time.time() - start_time
                    logger.info(
                        f'✅ Privilege encumbered status validation successful after {elapsed_time:.1f} seconds'
                    )
                    return

            # If not the last attempt, wait before trying again
            if attempts < max_attempts:
                logger.info(f'Waiting {check_interval} seconds before next check...')
                time.sleep(check_interval)

        except Exception as e:  # noqa: BLE001
            logger.warning(f'Attempt {attempts}/{max_attempts}: Error checking privilege status: {e}')
            if attempts < max_attempts:
                time.sleep(check_interval)

    # If we get here, validation failed
    elapsed_time = time.time() - start_time
    raise SmokeTestFailureException(
        f'Privilege encumbered status validation failed after {elapsed_time:.1f} seconds. '
        f'Expected "{expected_status}" but status did not update within {max_wait_time} seconds. '
        f'This suggests the downstream processing is not working correctly.'
    )


def test_license_encumbrance_workflow():
    """
    Test the complete license encumbrance workflow:
    1. Encumber a license twice
    2. Verify that the associated privilege is also encumbered with a 'licenseEncumbered' encumberedStatus
    3. Lift one encumbrance (license should remain encumbered)
    4. Lift the final encumbrance (license should become unencumbered)
    5. Verify that the associated privilege is no longer encumbered (has an 'unencumbered' encumberedStatus)
    """
    logger.info('Starting license encumbrance workflow test...')

    # Get provider information
    provider_data = call_provider_users_me_endpoint()
    compact = provider_data['compact']
    provider_id = provider_data['providerId']

    # Get the first license for testing
    licenses = provider_data.get('licenses', [])
    license_jurisdiction = provider_data['licenseJurisdiction']
    if not licenses:
        raise SmokeTestFailureException('No licenses found for provider')

    license_record = [lic for lic in licenses if lic['jurisdiction'] == license_jurisdiction][0]
    jurisdiction = license_record['jurisdiction']
    license_type = license_record['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(license_type)
    license_encumbrance_url = _generate_license_encumbrance_url(
        compact, provider_id, jurisdiction, license_type_abbreviation
    )

    # Create test staff user for this jurisdiction
    staff_email, staff_user_sub = create_test_staff_user_for_encumbrance(compact, jurisdiction)

    try:
        # Get staff user auth headers
        staff_headers = get_staff_user_auth_headers(staff_email)

        # Step 1: Encumber the license twice
        logger.info('Step 1: Encumbering license two times...')

        encumbrance_body = {
            'encumbranceEffectiveDate': '2024-11-11',
            'clinicalPrivilegeActionCategory': 'Fraud, Deception, or Misrepresentation',
        }

        # First encumbrance
        response1 = requests.post(license_encumbrance_url, headers=staff_headers, json=encumbrance_body, timeout=10)

        if response1.status_code != 200:
            raise SmokeTestFailureException(f'Failed to create first license encumbrance. Response: {response1.json()}')

        logger.info('First license encumbrance created successfully')

        # Verify provider state after first encumbrance
        provider_data = call_provider_users_me_endpoint()

        # Check license status
        updated_license = _get_license_data_from_provider_response(provider_data, jurisdiction, license_type)
        if not updated_license:
            raise SmokeTestFailureException('License not found after encumbrance')

        if updated_license.get('encumberedStatus') != 'encumbered':
            raise SmokeTestFailureException(
                f"License encumberedStatus should be 'encumbered', got: {updated_license.get('encumberedStatus')}"
            )

        if updated_license.get('compactEligibility') != 'ineligible':
            raise SmokeTestFailureException(
                f"License compactEligibility should be 'ineligible', got: {updated_license.get('compactEligibility')}"
            )

        if updated_license.get('licenseStatus') != 'inactive':
            raise SmokeTestFailureException(
                f"License licenseStatus should be 'inactive', got: {updated_license.get('licenseStatus')}"
            )

        # Check provider status
        if provider_data.get('encumberedStatus') != 'encumbered':
            raise SmokeTestFailureException(
                f"Provider encumberedStatus should be 'encumbered', got: {provider_data.get('encumberedStatus')}"
            )

        if provider_data.get('compactEligibility') != 'ineligible':
            raise SmokeTestFailureException(
                f"Provider compactEligibility should be 'ineligible', got: {provider_data.get('compactEligibility')}"
            )

        # Verify adverse action exists
        adverse_actions = updated_license.get('adverseActions', [])
        license_adverse_actions = [
            aa
            for aa in adverse_actions
            if aa.get('actionAgainst') == 'license' and aa.get('jurisdiction') == jurisdiction
        ]
        if len(license_adverse_actions) != 1:
            raise SmokeTestFailureException(f'Expected 1 license adverse action, found: {len(license_adverse_actions)}')

        first_adverse_action_id = license_adverse_actions[0]['adverseActionId']
        logger.info('First license encumbrance verified successfully')

        # Step 2: Verify that the associated privilege is also encumbered with 'licenseEncumbered' status
        logger.info('Verifying associated privilege is encumbered...')
        _validate_privilege_encumbered_status(
            expected_status='licenseEncumbered', test_jurisdiction=jurisdiction, test_license_type=license_type
        )
        logger.info('Verified privilege is encumbered with licenseEncumbered status')

        # Second encumbrance
        second_encumbrance_body = {
            'encumbranceEffectiveDate': '2025-01-01',
            'clinicalPrivilegeActionCategory': 'Unsafe Practice or Substandard Care',
        }
        response2 = requests.post(
            license_encumbrance_url, headers=staff_headers, json=second_encumbrance_body, timeout=10
        )

        if response2.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to create second license encumbrance. Response: {response2.json()}'
            )

        logger.info('Second license encumbrance created successfully')

        # Verify we now have two adverse actions
        provider_data = call_provider_users_me_endpoint()
        updated_license = _get_license_data_from_provider_response(provider_data, jurisdiction, license_type)
        adverse_actions = updated_license.get('adverseActions', [])
        license_adverse_actions = [
            aa
            for aa in adverse_actions
            if aa.get('actionAgainst') == 'license' and aa.get('jurisdiction') == jurisdiction
        ]
        if len(license_adverse_actions) != 2:
            raise SmokeTestFailureException(
                f'Expected 2 license adverse actions, found: {len(license_adverse_actions)}'
            )

        second_adverse_action_id = next(
            aa['adverseActionId'] for aa in license_adverse_actions if aa['adverseActionId'] != first_adverse_action_id
        )

        # Step 3: Lift first encumbrance (license should remain encumbered)
        logger.info('Step 3: Lifting first license encumbrance...')

        lift_body = {
            'effectiveLiftDate': '2025-05-05',
        }

        # Generate URL with encumbrance ID for PATCH operation
        license_encumbrance_lift_url = _generate_license_encumbrance_url(
            compact, provider_id, jurisdiction, license_type_abbreviation, first_adverse_action_id
        )

        response3 = requests.patch(license_encumbrance_lift_url, headers=staff_headers, json=lift_body, timeout=10)

        if response3.status_code != 200:
            raise SmokeTestFailureException(f'Failed to lift first license encumbrance. Response: {response3.json()}')

        logger.info('First license encumbrance lifted successfully')

        # Verify license is still encumbered
        provider_data = call_provider_users_me_endpoint()
        updated_license = next(
            (
                lic
                for lic in provider_data['licenses']
                if lic['jurisdiction'] == jurisdiction and lic['licenseType'] == license_type
            ),
            None,
        )

        if updated_license.get('encumberedStatus') != 'encumbered':
            raise SmokeTestFailureException(
                f'License should still be encumbered after lifting first encumbrance, '
                f'got: {updated_license.get("encumberedStatus")}'
            )

        logger.info('Verified license remains encumbered after lifting first encumbrance')

        # Also verify the provider record is still encumbered
        if provider_data.get('encumberedStatus') != 'encumbered':
            raise SmokeTestFailureException(
                f"Provider encumberedStatus should still be 'encumbered', got: {provider_data.get('encumberedStatus')}"
            )

        logger.info('Verified provider remains encumbered after lifting first encumbrance')

        # Step 4: Lift final encumbrance (license should become unencumbered)
        logger.info('Step 4: Lifting final license encumbrance...')

        lift_body = {
            'effectiveLiftDate': '2025-05-25',
        }

        # Generate URL with encumbrance ID for PATCH operation
        license_encumbrance_lift_url = _generate_license_encumbrance_url(
            compact, provider_id, jurisdiction, license_type_abbreviation, second_adverse_action_id
        )

        response4 = requests.patch(license_encumbrance_lift_url, headers=staff_headers, json=lift_body, timeout=10)

        if response4.status_code != 200:
            raise SmokeTestFailureException(f'Failed to lift final license encumbrance. Response: {response4.json()}')

        logger.info('Final license encumbrance lifted successfully')

        # Verify license is now unencumbered
        provider_data = call_provider_users_me_endpoint()
        updated_license = next(
            (
                lic
                for lic in provider_data['licenses']
                if lic['jurisdiction'] == jurisdiction and lic['licenseType'] == license_type
            ),
            None,
        )

        if updated_license.get('encumberedStatus') != 'unencumbered':
            raise SmokeTestFailureException(
                f'License should be unencumbered after lifting all encumbrances, '
                f'got: {updated_license.get("encumberedStatus")}'
            )

        # Verify provider is also unencumbered (assuming no other encumbrances exist)
        if provider_data.get('encumberedStatus') != 'unencumbered':
            raise SmokeTestFailureException(
                f'Provider should be unencumbered after lifting all license encumbrances, '
                f'got: {provider_data.get("encumberedStatus")}'
            )

        # Step 5: Verify that the associated privilege is no longer encumbered (has 'unencumbered' status)
        logger.info('Verifying associated privilege is no longer encumbered...')
        _validate_privilege_encumbered_status(
            expected_status='unencumbered', test_jurisdiction=jurisdiction, test_license_type=license_type
        )
        logger.info('Verified privilege is unencumbered after lifting all license encumbrances')

        logger.info('License encumbrance workflow test completed successfully')

    finally:
        # Clean up test staff user
        delete_test_staff_user(staff_email, staff_user_sub, compact)


def test_privilege_encumbrance_workflow():
    """
    Test the complete privilege encumbrance workflow:
    1. Encumber a privilege twice
    2. Lift one encumbrance (privilege should remain encumbered)
    3. Lift the final encumbrance (privilege should become unencumbered)
    """
    logger.info('Starting privilege encumbrance workflow test...')

    # Get provider information
    provider_data = call_provider_users_me_endpoint()
    compact = provider_data['compact']
    provider_id = provider_data['providerId']

    # Get the first privilege for testing

    # the smoke tests purchase a privilege in ne, so we grab that particular privilege record
    privilege_record = _get_privilege_data_from_provider_response(provider_data, jurisdiction='ne')
    if not privilege_record:
        raise SmokeTestFailureException('Nebraska privilege not found for provider')
    jurisdiction = privilege_record['jurisdiction']
    license_type = privilege_record['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(license_type)
    privilege_encumbrance_url = _generate_privilege_encumbrance_url(
        compact, provider_id, jurisdiction, license_type_abbreviation
    )

    # Create test staff user for this jurisdiction
    staff_email, staff_user_sub = create_test_staff_user_for_encumbrance(compact, jurisdiction)

    try:
        # Get staff user auth headers
        staff_headers = get_staff_user_auth_headers(staff_email)

        # Step 1: Encumber the privilege twice
        logger.info('Step 1: Encumbering privilege twice...')

        encumbrance_body = {
            'encumbranceEffectiveDate': '2024-12-12',
            'clinicalPrivilegeActionCategory': 'Fraud, Deception, or Misrepresentation',
        }

        # First encumbrance
        response1 = requests.post(privilege_encumbrance_url, headers=staff_headers, json=encumbrance_body, timeout=10)

        if response1.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to create first privilege encumbrance. Response: {response1.json()}'
            )

        logger.info('First privilege encumbrance created successfully')

        # Verify provider state after first encumbrance
        provider_data = call_provider_users_me_endpoint()

        # Check privilege status
        updated_privilege = _get_privilege_data_from_provider_response(provider_data, jurisdiction)
        if not updated_privilege:
            raise SmokeTestFailureException('Privilege not found after encumbrance')

        if updated_privilege.get('encumberedStatus') != 'encumbered':
            raise SmokeTestFailureException(
                f"Privilege encumberedStatus should be 'encumbered', got: {updated_privilege.get('encumberedStatus')}"
            )

        # Check provider status
        if provider_data.get('encumberedStatus') != 'encumbered':
            raise SmokeTestFailureException(
                f"Provider encumberedStatus should be 'encumbered', got: {provider_data.get('encumberedStatus')}"
            )

        # Verify adverse action exists
        adverse_actions = updated_privilege.get('adverseActions', [])
        privilege_adverse_actions = [
            aa
            for aa in adverse_actions
            if aa.get('actionAgainst') == 'privilege' and aa.get('jurisdiction') == jurisdiction
        ]
        if len(privilege_adverse_actions) != 1:
            raise SmokeTestFailureException(
                f'Expected 1 privilege adverse action, found: {len(privilege_adverse_actions)}'
            )

        first_adverse_action_id = privilege_adverse_actions[0]['adverseActionId']
        logger.info('First privilege encumbrance verified successfully')

        # Second encumbrance
        second_encumbrance_body = {
            'encumbranceEffectiveDate': '2025-02-02',
            'clinicalPrivilegeActionCategory': 'Unsafe Practice or Substandard Care',
        }
        response2 = requests.post(
            privilege_encumbrance_url, headers=staff_headers, json=second_encumbrance_body, timeout=10
        )

        if response2.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to create second privilege encumbrance. Response: {response2.json()}'
            )

        logger.info('Second privilege encumbrance created successfully')

        # Verify we now have two adverse actions
        provider_data = call_provider_users_me_endpoint()
        updated_privilege = _get_privilege_data_from_provider_response(provider_data, jurisdiction)
        adverse_actions = updated_privilege.get('adverseActions', [])
        privilege_adverse_actions = [
            aa
            for aa in adverse_actions
            if aa.get('actionAgainst') == 'privilege' and aa.get('jurisdiction') == jurisdiction
        ]
        if len(privilege_adverse_actions) != 2:
            raise SmokeTestFailureException(
                f'Expected 2 privilege adverse actions, found: {len(privilege_adverse_actions)}'
            )

        second_adverse_action_id = next(
            aa['adverseActionId']
            for aa in privilege_adverse_actions
            if aa['adverseActionId'] != first_adverse_action_id
        )

        # Step 2: Lift first encumbrance (privilege should remain encumbered)
        logger.info('Step 2: Lifting first privilege encumbrance...')

        lift_body = {
            'effectiveLiftDate': '2025-03-03',
        }

        # Generate URL with encumbrance ID for PATCH operation
        privilege_encumbrance_lift_url = _generate_privilege_encumbrance_url(
            compact, provider_id, jurisdiction, license_type_abbreviation, first_adverse_action_id
        )

        response3 = requests.patch(privilege_encumbrance_lift_url, headers=staff_headers, json=lift_body, timeout=10)

        if response3.status_code != 200:
            raise SmokeTestFailureException(f'Failed to lift first privilege encumbrance. Response: {response3.json()}')

        logger.info('First privilege encumbrance lifted successfully')

        # Verify privilege is still encumbered
        provider_data = call_provider_users_me_endpoint()
        updated_privilege = _get_privilege_data_from_provider_response(provider_data, jurisdiction)

        if updated_privilege.get('encumberedStatus') != 'encumbered':
            raise SmokeTestFailureException(
                f'Privilege should still be encumbered after lifting first encumbrance, '
                f'got: {updated_privilege.get("encumberedStatus")}'
            )

        # Also verify the provider record is still encumbered
        if provider_data.get('encumberedStatus') != 'encumbered':
            raise SmokeTestFailureException(
                f"Provider encumberedStatus should still be 'encumbered', got: {provider_data.get('encumberedStatus')}"
            )

        logger.info('Verified privilege remains encumbered after lifting first encumbrance')

        # Step 3: Lift final encumbrance (privilege should become unencumbered)
        logger.info('Step 3: Lifting final privilege encumbrance...')

        lift_body = {
            'effectiveLiftDate': '2025-04-04',
        }

        # Generate URL with encumbrance ID for PATCH operation
        privilege_encumbrance_lift_url = _generate_privilege_encumbrance_url(
            compact, provider_id, jurisdiction, license_type_abbreviation, second_adverse_action_id
        )

        response4 = requests.patch(privilege_encumbrance_lift_url, headers=staff_headers, json=lift_body, timeout=10)

        if response4.status_code != 200:
            raise SmokeTestFailureException(f'Failed to lift final privilege encumbrance. Response: {response4.json()}')

        logger.info('Final privilege encumbrance lifted successfully')

        # Verify privilege is now unencumbered
        provider_data = call_provider_users_me_endpoint()
        updated_privilege = _get_privilege_data_from_provider_response(provider_data, jurisdiction)

        if updated_privilege.get('encumberedStatus') != 'unencumbered':
            raise SmokeTestFailureException(
                f'Privilege should be unencumbered after lifting all encumbrances, '
                f'got: {updated_privilege.get("encumberedStatus")}'
            )

        # Also verify the provider record is now unencumbered
        if provider_data.get('encumberedStatus') != 'unencumbered':
            raise SmokeTestFailureException(
                f"Provider encumberedStatus should now be 'unencumbered', got: {provider_data.get('encumberedStatus')}"
            )

        logger.info('Privilege encumbrance workflow test completed successfully')

    finally:
        # Clean up test staff user
        delete_test_staff_user(staff_email, staff_user_sub, compact)


def run_encumbrance_smoke_tests():
    """
    Run the complete suite of encumbrance smoke tests.
    """
    logger.info('Starting encumbrance smoke tests...')

    try:
        # Setup test environment
        setup_test_environment()

        # Run license encumbrance tests
        test_license_encumbrance_workflow()

        # Run privilege encumbrance tests
        test_privilege_encumbrance_workflow()

        logger.info('All encumbrance smoke tests completed successfully!')

        # Clean up adverse actions after tests
        clean_adverse_actions()

    except Exception as e:
        logger.error(f'Encumbrance smoke tests failed: {str(e)}')
        raise


if __name__ == '__main__':
    # Load environment variables from smoke_tests_env.json
    load_smoke_test_env()

    # Run the complete test suite
    run_encumbrance_smoke_tests()
