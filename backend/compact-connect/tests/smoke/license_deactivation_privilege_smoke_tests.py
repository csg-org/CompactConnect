#!/usr/bin/env python3
"""
Smoke tests for license deactivation privilege functionality.

This module contains end-to-end tests for the license deactivation workflow where privileges
are automatically deactivated when their associated home state license is
deactivated by a jurisdiction.

The tests create their own test data from scratch and clean up after themselves.
"""

import time

from smoke_common import (
    SmokeTestFailureException,
    cleanup_test_provider_records,
    config,
    create_test_privilege_record,
    create_test_staff_user,
    delete_test_staff_user,
    get_staff_user_auth_headers,
    load_smoke_test_env,
    logger,
    upload_license_record,
    wait_for_provider_creation,
)

# Test configuration
TEST_COMPACT = 'aslp'
TEST_JURISDICTION = 'oh'  # Home jurisdiction
TEST_PRIVILEGE_JURISDICTION = 'ne'  # Where privilege is purchased
TEST_LICENSE_TYPE = 'speech-language pathologist'
TEST_GIVEN_NAME = 'TestProvider'
TEST_FAMILY_NAME = 'LicenseDeactivation'
TEST_SSN = '999-99-9999'  # Test SSN for license uploads


def get_provider_details_from_api(staff_headers: dict, compact: str, provider_id: str):
    """
    Get provider details from the staff API endpoint.

    :param staff_headers: Authentication headers for staff user
    :param compact: The compact abbreviation
    :param provider_id: The provider's ID
    :returns: Provider details from the API including privileges list
    :raises SmokeTestFailureException: If the API request fails
    """
    import requests

    response = requests.get(
        url=f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}',
        headers=staff_headers,
        timeout=10,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to get provider details. Response: {response.json()}')

    return response.json()


def validate_privilege_deactivation(
    staff_headers: dict,
    provider_id: str,
    compact: str,
    license_jurisdiction: str,
    license_type: str,
    max_wait_time: int = 120,
    check_interval: int = 15,
):
    """
    Validate that privilege is deactivated due to license deactivation.

    This function polls the API to check if a privilege has been automatically
    deactivated after its associated license was deactivated. It retries
    multiple times within the specified time window.

    :param staff_headers: Authentication headers for staff user
    :param provider_id: The provider's ID
    :param compact: The compact abbreviation
    :param license_jurisdiction: The license jurisdiction
    :param license_type: The license type
    :param max_wait_time: Maximum time to wait in seconds (default: 120)
    :param check_interval: Time between checks in seconds (default: 15)
    :returns: The matching privilege record if validation succeeds
    :raises SmokeTestFailureException: If privilege is not properly deactivated within the time limit
    """
    logger.info(f'Validating privilege deactivation for provider {provider_id}...')

    start_time = time.time()
    attempts = 0
    max_attempts = max_wait_time // check_interval

    while attempts < max_attempts:
        attempts += 1

        try:
            provider_data = get_provider_details_from_api(staff_headers, compact, provider_id)
            privileges = provider_data.get('privileges', [])

            # Find the privilege that matches our test criteria
            matching_privilege = None
            for privilege in privileges:
                if (
                    privilege.get('licenseJurisdiction') == license_jurisdiction
                    and privilege.get('licenseType') == license_type
                ):
                    matching_privilege = privilege
                    break

            if not matching_privilege:
                logger.warning(f'Attempt {attempts}/{max_attempts}: No matching privilege found')
            else:
                privilege_status = matching_privilege.get('status')
                logger.info(f'Attempt {attempts}/{max_attempts}: privilege status = {privilege_status}')

                # Check if privilege is properly deactivated
                if privilege_status == 'inactive':
                    elapsed_time = time.time() - start_time
                    logger.info(f'✅ Privilege deactivation validation successful after {elapsed_time:.1f} seconds')
                    return matching_privilege

            # Wait before next attempt
            if attempts < max_attempts:
                logger.info(f'Waiting {check_interval} seconds before next check...')
                time.sleep(check_interval)

        except Exception as e:  # noqa: BLE001
            logger.warning(f'Attempt {attempts}/{max_attempts}: Error checking privilege: {e}')
            if attempts < max_attempts:
                time.sleep(check_interval)

    # If we get here, validation failed
    elapsed_time = time.time() - start_time
    raise SmokeTestFailureException(
        f'Privilege deactivation validation failed after {elapsed_time:.1f} seconds. '
        f'Expected privilege status to be "inactive" but it was not set within {max_wait_time} seconds.'
    )


def test_license_deactivation_privilege_workflow():
    """
    The test validates that when a home state license is deactivated,
    any privileges associated with that license are automatically
    deactivated as well.

    This test performs the following steps:

    1. Upload an active license and wait for provider creation
    2. Update provider registration details
    3. Create a test privilege record
    4. Upload the same license with inactive status
    5. Validate that the privilege is automatically deactivated
    6. Clean up all test data

    :raises SmokeTestFailureException: If any step of the workflow fails
    """
    logger.info('Starting license deactivation privilege workflow test...')

    provider_id = None
    staff_email = None
    staff_user_sub = None

    try:
        # Create test staff user with permissions to upload licenses
        staff_email = f'test-license-deactivation-{TEST_JURISDICTION}@ccSmokeTestFakeEmail.com'
        staff_user_sub = create_test_staff_user(
            email=staff_email,
            compact=TEST_COMPACT,
            jurisdiction=TEST_JURISDICTION,
            permissions={'actions': {'admin'}, 'jurisdictions': {TEST_JURISDICTION: {'write', 'admin'}}},
        )

        staff_headers = get_staff_user_auth_headers(staff_email)

        # Step 1: Upload an active license and wait for provider creation
        logger.info('Step 1: Uploading active license and waiting for provider creation...')

        upload_license_record(
            staff_headers=staff_headers,
            compact=TEST_COMPACT,
            jurisdiction=TEST_JURISDICTION,
            data_overrides={
                'givenName': TEST_GIVEN_NAME,
                'familyName': TEST_FAMILY_NAME,
                'licenseType': TEST_LICENSE_TYPE,
                'ssn': TEST_SSN,
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
            },
        )

        # Wait for provider to be created
        provider_id = wait_for_provider_creation(
            staff_headers=staff_headers,
            compact=TEST_COMPACT,
            given_name=TEST_GIVEN_NAME,
            family_name=TEST_FAMILY_NAME,
            max_wait_time=660,  # 11 minutes (to account for message batch windows)
        )

        # Step 2: Create a test privilege record
        logger.info('Step 2: Creating test privilege record...')

        create_test_privilege_record(
            provider_id=provider_id,
            compact=TEST_COMPACT,
            jurisdiction=TEST_PRIVILEGE_JURISDICTION,
            license_jurisdiction=TEST_JURISDICTION,
            license_type=TEST_LICENSE_TYPE,
        )

        # Verify privilege was created and is active
        provider_data = get_provider_details_from_api(staff_headers, TEST_COMPACT, provider_id)
        privileges = provider_data.get('privileges', [])

        test_privilege = None
        for privilege in privileges:
            if (
                privilege.get('licenseJurisdiction') == TEST_JURISDICTION
                and privilege.get('licenseType') == TEST_LICENSE_TYPE
            ):
                test_privilege = privilege
                break

        if not test_privilege:
            raise SmokeTestFailureException('Test privilege record was not created successfully')

        if test_privilege.get('status') != 'active':
            raise SmokeTestFailureException(
                f'Test privilege should have status "active" initially, but found: {test_privilege.get("status")}'
            )

        logger.info('✅ Test privilege record created successfully and is in expected initial state (active status)')

        # Step 3: Upload the same license with inactive status
        logger.info('Step 3: Uploading license with inactive status to trigger deactivation...')

        upload_license_record(
            staff_headers=staff_headers,
            compact=TEST_COMPACT,
            jurisdiction=TEST_JURISDICTION,
            data_overrides={
                'givenName': TEST_GIVEN_NAME,
                'familyName': TEST_FAMILY_NAME,
                'licenseType': TEST_LICENSE_TYPE,
                'ssn': TEST_SSN,
                'licenseStatus': 'inactive',
                'compactEligibility': 'ineligible',
            },
        )

        # Step 4: Validate that the privilege is automatically deactivated
        logger.info('Step 4: Validating automatic privilege deactivation...')

        validate_privilege_deactivation(
            staff_headers=staff_headers,
            provider_id=provider_id,
            compact=TEST_COMPACT,
            license_jurisdiction=TEST_JURISDICTION,
            license_type=TEST_LICENSE_TYPE,
            max_wait_time=660,  # 11 minutes (to account for message batch windows)
            check_interval=15,
        )

        logger.info('✅ Privilege was automatically deactivated with status "inactive"')
        logger.info('✅ License deactivation privilege workflow test completed successfully!')

    finally:
        # Step 5: Clean up all test data
        logger.info('Step 5: Cleaning up test data...')

        if provider_id:
            cleanup_test_provider_records(provider_id, TEST_COMPACT)

        if staff_email and staff_user_sub:
            delete_test_staff_user(staff_email, staff_user_sub, TEST_COMPACT)

        logger.info('✅ Test cleanup completed')


def run_license_deactivation_privilege_smoke_tests():
    """
    Run the complete suite of license deactivation privilege smoke tests.
    """
    logger.info('Starting license deactivation privilege smoke tests...')

    try:
        test_license_deactivation_privilege_workflow()
        logger.info('All license deactivation privilege smoke tests completed successfully!')

    except Exception as e:
        logger.error(f'License deactivation privilege smoke tests failed: {str(e)}')
        raise


if __name__ == '__main__':
    # Load environment variables from smoke_tests_env.json
    load_smoke_test_env()

    # Run the complete test suite
    run_license_deactivation_privilege_smoke_tests()
