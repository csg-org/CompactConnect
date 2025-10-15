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
    get_provider_user_records,
    get_staff_user_auth_headers,
    load_smoke_test_env,
    logger,
)


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


class EncumbranceTestHelper:
    """Helper class to manage encumbrance test operations with pre-configured staff users and URLs."""

    def __init__(self, provider_data: dict):
        """
        Initialize the helper with provider data and set up all necessary resources.

        :param provider_data: Result from call_provider_users_me_endpoint()
        """
        self.provider_data = provider_data
        self.compact = provider_data['compact']
        self.provider_id = provider_data['providerId']

        # Get jurisdiction information from Nebraska privilege (smoke tests purchase privilege in NE)
        # Query database directly for privilege records
        provider_user_records = get_provider_user_records(self.compact, self.provider_id)

        # Find the Nebraska privilege
        ne_privileges = provider_user_records.get_privilege_records(
            filter_condition=lambda priv: priv.jurisdiction == 'ne'
        )

        if not ne_privileges:
            raise SmokeTestFailureException('Nebraska privilege not found for provider')

        privilege_record = ne_privileges[0]
        self.privilege_jurisdiction = privilege_record.jurisdiction
        self.license_jurisdiction = privilege_record.licenseJurisdiction
        self.license_type = privilege_record.licenseType
        self.license_type_abbreviation = privilege_record.licenseTypeAbbreviation

        # Track created users for cleanup
        self.created_staff_users = []

        # Create staff users for both jurisdictions
        self.privilege_jurisdiction_staff_user = self._create_privilege_jurisdiction_staff_user()
        self.license_jurisdiction_staff_user = self._create_license_jurisdiction_staff_user()

    def _create_privilege_jurisdiction_staff_user(self) -> dict:
        """Create and return privilege jurisdiction staff user info."""
        email, user_sub = self._create_test_staff_user_for_encumbrance(self.compact, self.privilege_jurisdiction)
        headers = get_staff_user_auth_headers(email)

        # Track for cleanup
        self.created_staff_users.append((email, user_sub, self.compact))

        return {'email': email, 'user_sub': user_sub, 'headers': headers}

    def _create_license_jurisdiction_staff_user(self) -> dict:
        """Create and return license jurisdiction staff user info."""
        email, user_sub = self._create_test_staff_user_for_encumbrance(self.compact, self.license_jurisdiction)
        headers = get_staff_user_auth_headers(email)

        # Track for cleanup
        self.created_staff_users.append((email, user_sub, self.compact))

        return {'email': email, 'user_sub': user_sub, 'headers': headers}

    def get_privilege_staff_admin_headers(self) -> dict:
        """Get authentication headers for privilege jurisdiction staff user."""
        return self.privilege_jurisdiction_staff_user['headers']

    def get_license_staff_admin_headers(self) -> dict:
        """Get authentication headers for license jurisdiction staff user."""
        return self.license_jurisdiction_staff_user['headers']

    def encumber_license(self, request_body: dict) -> dict:
        """
        Encumber the license.
        """
        return self._call_license_encumbrance_endpoint(request_body)

    def encumber_privilege(self, request_body: dict) -> dict:
        """
        Encumber the privilege.
        """
        return self._call_privilege_encumbrance_endpoint(request_body)

    def lift_license_encumbrance(self, request_body: dict, encumbrance_id: str) -> dict:
        """
        Lift the license.
        """
        return self._call_license_encumbrance_endpoint(request_body, encumbrance_id)

    def lift_privilege_encumbrance(self, request_body: dict, encumbrance_id: str) -> dict:
        """
        Lift the privilege.
        """
        return self._call_privilege_encumbrance_endpoint(request_body, encumbrance_id)

    def _call_license_encumbrance_endpoint(self, request_body: dict, encumbrance_id: str = None) -> dict:
        """
        Call the license encumbrance endpoint and verify 200 status.

        :param request_body: The request body for the API call
        :param encumbrance_id: Optional encumbrance ID for PATCH operations (lifting)

        :returns: The response JSON

        :raises: SmokeTestFailureException`: If the API call fails
        """
        url = self._generate_license_encumbrance_url(encumbrance_id)

        if encumbrance_id:
            # PATCH operation for lifting encumbrance
            response = requests.patch(
                url, headers=self.get_license_staff_admin_headers(), json=request_body, timeout=10
            )
        else:
            # POST operation for creating encumbrance
            response = requests.post(url, headers=self.get_license_staff_admin_headers(), json=request_body, timeout=10)

        if response.status_code != 200:
            operation = 'lift' if encumbrance_id else 'create'
            raise SmokeTestFailureException(f'Failed to {operation} license encumbrance. Response: {response.json()}')

        return response.json()

    def _call_privilege_encumbrance_endpoint(self, request_body: dict, encumbrance_id: str = None) -> dict:
        """
        Call the privilege encumbrance endpoint and verify 200 status.

        :param request_body: The request body for the API call
        :param encumbrance_id: Optional encumbrance ID for PATCH operations (lifting)

        :returns: The response JSON

        :raises: SmokeTestFailureException`: If the API call fails
        """
        url = self._generate_privilege_encumbrance_url(encumbrance_id)

        if encumbrance_id:
            # PATCH operation for lifting encumbrance
            response = requests.patch(
                url, headers=self.get_privilege_staff_admin_headers(), json=request_body, timeout=10
            )
        else:
            # POST operation for creating encumbrance
            response = requests.post(
                url, headers=self.get_privilege_staff_admin_headers(), json=request_body, timeout=10
            )

        if response.status_code != 200:
            operation = 'lift' if encumbrance_id else 'create'
            raise SmokeTestFailureException(f'Failed to {operation} privilege encumbrance. Response: {response.json()}')

        return response.json()

    def validate_license_encumbered_state(self, expected_status: str = 'encumbered'):
        """Validate license encumbered status and related fields."""
        # Get all provider records directly from DynamoDB
        provider_user_records = get_provider_user_records(self.compact, self.provider_id)

        # Get the specific license record
        license_record = provider_user_records.get_specific_license_record(
            self.license_jurisdiction, self.license_type_abbreviation
        )

        if not license_record:
            raise SmokeTestFailureException('License not found after encumbrance operation')

        actual_status = license_record.encumberedStatus
        if actual_status != expected_status:
            raise SmokeTestFailureException(
                f"License encumberedStatus should be '{expected_status}', got: {actual_status}"
            )

        return license_record

    def validate_privilege_encumbered_state(
        self, expected_status: str = 'encumbered', max_wait_time: int = 60, check_interval: int = 10
    ):
        """
        Validate that the privilege encumberedStatus matches the expected value.

        This method will poll the provider records every check_interval seconds
        for up to max_wait_time seconds, checking if the privilege has the expected
        encumberedStatus. This accounts for eventual consistency in downstream processing.

        :param expected_status: The expected encumberedStatus value ('licenseEncumbered', 'unencumbered', etc.)
        :param max_wait_time: Maximum time to wait in seconds (default: 60)
        :param check_interval: Time between checks in seconds (default: 10)

        :raises:
            :class:`~smoke_common.SmokeTestFailureException`: If the privilege status doesn't match within max_wait_time
        """
        logger.info(
            f'Validating privilege encumbered status is "{expected_status}" '
            f'for jurisdiction "{self.privilege_jurisdiction}"...'
        )

        start_time = time.time()
        attempts = 0
        max_attempts = max_wait_time // check_interval

        while attempts < max_attempts:
            attempts += 1

            try:
                # Get current provider records directly from DynamoDB
                provider_user_records = get_provider_user_records(self.compact, self.provider_id)

                # Find the privilege that matches the license jurisdiction and type
                matching_privilege = provider_user_records.get_specific_privilege_record(
                    self.privilege_jurisdiction, self.license_type_abbreviation
                )

                if not matching_privilege:
                    logger.warning(
                        f'Attempt {attempts}/{max_attempts}: No privilege found matching jurisdiction '
                        f'"{self.privilege_jurisdiction}" and license type "{self.license_type_abbreviation}"'
                    )
                else:
                    logger.info('matching privilege found', matching_privilege=matching_privilege)
                    actual_status = matching_privilege.encumberedStatus
                    logger.info(
                        f'Attempt {attempts}/{max_attempts}: Privilege encumberedStatus is "{actual_status}", '
                        f'expecting "{expected_status}"'
                    )

                    if actual_status == expected_status:
                        elapsed_time = time.time() - start_time
                        logger.info(
                            f'✅ Privilege encumbered status validation successful after {elapsed_time:.1f} seconds'
                        )
                        return matching_privilege

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

    def validate_provider_encumbered_state(self, expected_status: str = 'encumbered'):
        """Validate provider encumbered status."""
        # Get all provider records directly from DynamoDB
        provider_user_records = get_provider_user_records(self.compact, self.provider_id)
        provider_record = provider_user_records.get_provider_record()

        if provider_record.encumberedStatus != expected_status:
            raise SmokeTestFailureException(
                f"Provider encumberedStatus should be '{expected_status}', got: {provider_record.encumberedStatus}"
            )

    def get_license_adverse_actions(self):
        """Get all license adverse actions for this provider."""
        # Get all provider records directly from DynamoDB
        provider_user_records = get_provider_user_records(self.compact, self.provider_id)

        # Get adverse actions for this specific license
        adverse_actions = provider_user_records.get_adverse_action_records_for_license(
            self.license_jurisdiction, self.license_type_abbreviation
        )

        # Convert to dict format for compatibility with existing code
        return [aa.to_dict() for aa in adverse_actions]

    def get_privilege_adverse_actions(self):
        """Get all privilege adverse actions for this provider."""
        # Get all provider records directly from DynamoDB
        provider_user_records = get_provider_user_records(self.compact, self.provider_id)

        # Get adverse actions for this specific privilege
        adverse_actions = provider_user_records.get_adverse_action_records_for_privilege(
            self.privilege_jurisdiction, self.license_type_abbreviation
        )

        # Convert to dict format for compatibility with existing code
        return [aa.to_dict() for aa in adverse_actions]

    @staticmethod
    def verify_adverse_action_matches_request(adverse_actions: list[dict], request_payload: dict) -> dict:
        """
        Verify that at least one adverse action matches the request payload.

        :param adverse_actions: List of adverse action records
        :param request_payload: The request payload that was sent (containing encumbranceType and
                                clinicalPrivilegeActionCategories)
        :return: The matching adverse action record
        :raises SmokeTestFailureException: If no matching adverse action is found
        """
        expected_encumbrance_type = request_payload.get('encumbranceType')
        expected_categories = set(request_payload.get('clinicalPrivilegeActionCategories', []))

        logger.info(
            f'Verifying adverse action matches request: encumbranceType={expected_encumbrance_type}, '
            f'categories={expected_categories}'
        )

        matching_actions = []
        for adverse_action in adverse_actions:
            action_type = adverse_action.get('encumbranceType')
            action_categories = set(adverse_action.get('clinicalPrivilegeActionCategories', []))

            if action_type == expected_encumbrance_type and action_categories == expected_categories:
                matching_actions.append(adverse_action)

        if not matching_actions:
            raise SmokeTestFailureException(
                f'No adverse action found matching request payload. '
                f'Expected encumbranceType="{expected_encumbrance_type}" and '
                f'categories={expected_categories}. '
                f'Found adverse actions: {adverse_actions}'
            )

        logger.info(f'✅ Found {len(matching_actions)} matching adverse action(s)')
        return matching_actions[0]

    def verify_license_adverse_action_matches_request(self, request_payload: dict) -> dict:
        """
        Verify that a license adverse action matches the request payload.

        :param request_payload: The request payload that was sent
        :return: The matching adverse action record
        """
        license_adverse_actions = self.get_license_adverse_actions()
        return self.verify_adverse_action_matches_request(license_adverse_actions, request_payload)

    def verify_privilege_adverse_action_matches_request(self, request_payload: dict) -> dict:
        """
        Verify that a privilege adverse action matches the request payload.

        :param request_payload: The request payload that was sent
        :return: The matching adverse action record
        """
        privilege_adverse_actions = self.get_privilege_adverse_actions()
        return self.verify_adverse_action_matches_request(privilege_adverse_actions, request_payload)

    def _generate_license_encumbrance_url(self, encumbrance_id: str = None):
        """Generate license encumbrance URL."""
        base_url = (
            f'{config.api_base_url}/v1/compacts/{self.compact}/providers/{self.provider_id}'
            f'/licenses/jurisdiction/{self.license_jurisdiction}/licenseType/{self.license_type_abbreviation}/encumbrance'
        )
        if encumbrance_id:
            return f'{base_url}/{encumbrance_id}'
        return base_url

    def _generate_privilege_encumbrance_url(self, encumbrance_id: str = None):
        """Generate privilege encumbrance URL."""
        base_url = (
            f'{config.api_base_url}/v1/compacts/{self.compact}/providers/{self.provider_id}'
            f'/privileges/jurisdiction/{self.privilege_jurisdiction}/licenseType/{self.license_type_abbreviation}/encumbrance'
        )
        if encumbrance_id:
            return f'{base_url}/{encumbrance_id}'
        return base_url

    def _create_test_staff_user_for_encumbrance(self, compact: str, jurisdiction: str):
        """Create a test staff user with permissions to create and lift encumbrances."""
        email = f'test-encumbrance-admin-{jurisdiction}@ccSmokeTestFakeEmail.com'
        user_sub = create_test_staff_user(
            email=email,
            compact=compact,
            jurisdiction=jurisdiction,
            permissions={'actions': {}, 'jurisdictions': {jurisdiction: {'admin'}}},
        )
        return email, user_sub

    def wait_for_downstream_processing(self, total_periods: int = 6, period_length: int = 10):
        """Wait for downstream processing to complete between operations."""
        for i in range(total_periods):
            logger.info(f'pausing for downstream processing to complete: {i + 1}/{total_periods}')
            time.sleep(period_length)

    def cleanup_staff_users(self):
        """Clean up all created staff users."""
        for email, user_sub, compact in self.created_staff_users:
            try:
                delete_test_staff_user(email, user_sub, compact)
            except Exception as e:  # noqa: BLE001
                logger.warning(f'Failed to clean up staff user {email}: {e}')
        self.created_staff_users.clear()


def test_license_encumbrance_workflow():
    """
    Test the complete license encumbrance workflow:
    1. Encumber a license twice
    2. Verify that the associated privilege is also encumbered with a 'licenseEncumbered' encumberedStatus
    3. Encumber privilege and ensure it is updated to an 'encumbered' encumberedStatus
    4. Lift one encumbrance (license should remain encumbered)
    5. Lift the final encumbrance (license should become unencumbered)
    6. Verify that the associated privilege is still encumbered (has an 'encumbered' encumberedStatus)
    7. Lift encumbrance from privilege
    8. Verify privilege is unencumbered
    """
    logger.info('Starting license encumbrance workflow test...')
    # remove adverse action records from previous tests
    clean_adverse_actions()
    # Get provider data and create helper
    provider_data = call_provider_users_me_endpoint()
    helper = EncumbranceTestHelper(provider_data)

    try:
        # Step 1: Encumber the license twice
        logger.info('Step 1: Encumbering license two times...')

        encumbrance_body = {
            'encumbranceEffectiveDate': '2024-11-11',
            'encumbranceType': 'surrender of license',
            'clinicalPrivilegeActionCategories': ['Fraud, Deception, or Misrepresentation'],
        }

        # First encumbrance
        helper.encumber_license(encumbrance_body)
        logger.info('First license encumbrance created successfully')

        # Verify provider state after first encumbrance
        provider_user_records = get_provider_user_records(helper.compact, helper.provider_id)
        updated_license = provider_user_records.get_specific_license_record(
            helper.license_jurisdiction, helper.license_type_abbreviation
        )
        if not updated_license:
            raise SmokeTestFailureException('License not found after encumbrance')

        if updated_license.encumberedStatus != 'encumbered':
            raise SmokeTestFailureException(
                f"License encumberedStatus should be 'encumbered', got: {updated_license.encumberedStatus}"
            )

        if updated_license.compactEligibility != 'ineligible':
            raise SmokeTestFailureException(
                f"License compactEligibility should be 'ineligible', got: {updated_license.compactEligibility}"
            )

        if updated_license.licenseStatus != 'inactive':
            raise SmokeTestFailureException(
                f"License licenseStatus should be 'inactive', got: {updated_license.licenseStatus}"
            )

        # Check provider status
        provider_record = provider_user_records.get_provider_record()
        if provider_record.encumberedStatus != 'encumbered':
            raise SmokeTestFailureException(
                f"Provider encumberedStatus should be 'encumbered', got: {provider_record.encumberedStatus}"
            )

        if provider_record.compactEligibility != 'ineligible':
            raise SmokeTestFailureException(
                f"Provider compactEligibility should be 'ineligible', got: {provider_record.compactEligibility}"
            )

        # Verify adverse action exists
        license_adverse_actions = helper.get_license_adverse_actions()
        if len(license_adverse_actions) != 1:
            raise SmokeTestFailureException(f'Expected 1 license adverse action, found: {len(license_adverse_actions)}')

        first_adverse_action_id = license_adverse_actions[0]['adverseActionId']

        # Verify the adverse action matches the request payload
        helper.verify_license_adverse_action_matches_request(encumbrance_body)
        logger.info('First license encumbrance verified successfully')

        # Step 2: Verify that the associated privilege is also encumbered with 'licenseEncumbered' status
        logger.info('Verifying associated privilege is encumbered...')
        helper.validate_privilege_encumbered_state('licenseEncumbered')
        logger.info('Verified privilege is encumbered with licenseEncumbered status')

        # Second encumbrance
        second_encumbrance_body = {
            'encumbranceEffectiveDate': '2025-01-01',
            'encumbranceType': 'denial',
            'clinicalPrivilegeActionCategories': ['Unsafe Practice or Substandard Care'],
        }
        helper.encumber_license(second_encumbrance_body)
        logger.info('Second license encumbrance created successfully')

        # Verify we now have two adverse actions
        license_adverse_actions = helper.get_license_adverse_actions()
        if len(license_adverse_actions) != 2:
            raise SmokeTestFailureException(
                f'Expected 2 license adverse actions, found: {len(license_adverse_actions)}'
            )

        second_adverse_action_id = next(
            aa['adverseActionId'] for aa in license_adverse_actions if aa['adverseActionId'] != first_adverse_action_id
        )

        # Verify the second adverse action matches the request payload
        helper.verify_license_adverse_action_matches_request(second_encumbrance_body)
        logger.info('Second license encumbrance verified successfully')

        # Step 3: Encumber Privilege
        privilege_encumbrance_body = {
            'encumbranceEffectiveDate': '2025-05-09',
            'encumbranceType': 'reprimand',
            'clinicalPrivilegeActionCategories': ['Unsafe Practice or Substandard Care', 'Misconduct or Abuse'],
        }

        helper.encumber_privilege(privilege_encumbrance_body)
        logger.info('Privilege encumbrance created successfully')

        # privilege should now be encumbered
        helper.validate_privilege_encumbered_state(
            expected_status='encumbered',
            # only need to check once
            max_wait_time=1,
            check_interval=1,
        )

        # Verify the privilege adverse action matches the request payload
        helper.verify_privilege_adverse_action_matches_request(privilege_encumbrance_body)
        logger.info('Privilege encumbrance verified successfully')

        # Step 4: Lift first encumbrance (license should remain encumbered)
        logger.info('Step 4: Lifting first license encumbrance...')

        lift_body = {
            'effectiveLiftDate': '2025-05-05',
        }

        helper.lift_license_encumbrance(lift_body, first_adverse_action_id)
        logger.info('First license encumbrance lifted successfully')

        # Verify license is still encumbered
        helper.validate_license_encumbered_state('encumbered')

        logger.info('Verified license remains encumbered after lifting first encumbrance')

        # Also verify the provider record is still encumbered
        helper.validate_provider_encumbered_state('encumbered')

        logger.info('Verified provider remains encumbered after lifting first encumbrance')

        # wait 1 minute for downstream processing to complete
        # this keeps the lifting events isolated from each other
        helper.wait_for_downstream_processing()

        # Step 5: Lift final encumbrance (license should become unencumbered)
        logger.info('Step 5: Lifting final license encumbrance...')

        lift_body = {
            'effectiveLiftDate': '2025-05-25',
        }

        helper.lift_license_encumbrance(lift_body, second_adverse_action_id)
        logger.info('Final license encumbrance lifted successfully')

        # Verify license is now unencumbered
        helper.validate_license_encumbered_state('unencumbered')

        # Verify provider is still encumbered (due to privilege encumbrance)
        helper.validate_provider_encumbered_state('encumbered')

        # Step 6: Verify that the associated privilege is still encumbered
        logger.info('Verifying associated privilege is still encumbered...')
        helper.validate_privilege_encumbered_state(
            expected_status='encumbered',
            # only check once
            max_wait_time=1,
            check_interval=1,
        )
        logger.info('Verified privilege is still encumbered after lifting all license encumbrances')

        privilege_adverse_actions = helper.get_privilege_adverse_actions()

        if len(privilege_adverse_actions) != 1:
            raise SmokeTestFailureException(
                f'Expected 1 privilege adverse action, found: {len(privilege_adverse_actions)}'
            )

        privilege_adverse_action_id = privilege_adverse_actions[0]['adverseActionId']

        # Step 7: Lift the privilege encumbrance
        logger.info('Step 7: Lifting privilege encumbrance...')
        lift_body = {'effectiveLiftDate': '2023-01-25'}
        helper.lift_privilege_encumbrance(lift_body, privilege_adverse_action_id)
        logger.info('Privilege encumbrance lifted successfully')

        # Step 8: Verify privilege becomes 'unencumbered'
        logger.info('Step 8: Verifying privilege becomes unencumbered...')
        helper.validate_privilege_encumbered_state(
            expected_status='unencumbered',
            # should be instantly set to unencumbered
            max_wait_time=1,
            check_interval=1,
        )
        logger.info('Verified privilege is now unencumbered')

        logger.info('License encumbrance workflow test completed successfully')

    finally:
        # Clean up all created staff users
        helper.cleanup_staff_users()


def test_privilege_encumbrance_workflow():
    """
    Test the complete privilege encumbrance workflow:
    1. Encumber a privilege twice
    2. Lift one encumbrance (privilege should remain encumbered)
    3. Lift the final encumbrance (privilege should become unencumbered)
    """
    logger.info('Starting privilege encumbrance workflow test...')
    # clean adverse actions from previous test
    clean_adverse_actions()
    # Get provider data and create helper
    provider_data = call_provider_users_me_endpoint()
    helper = EncumbranceTestHelper(provider_data)

    try:
        # Step 1: Encumber the privilege twice
        logger.info('Step 1: Encumbering privilege twice...')

        encumbrance_body = {
            'encumbranceEffectiveDate': '2024-12-12',
            'encumbranceType': 'fine',
            'clinicalPrivilegeActionCategories': ['Fraud, Deception, or Misrepresentation'],
        }

        # First encumbrance
        helper.encumber_privilege(encumbrance_body)
        logger.info('First privilege encumbrance created successfully')

        # Verify provider state after first encumbrance
        helper.validate_privilege_encumbered_state(
            expected_status='encumbered',
            # only need to check once
            max_wait_time=1,
            check_interval=1,
        )

        # Check provider status to ensure it is encumbered as well
        helper.validate_provider_encumbered_state('encumbered')

        # Verify adverse action exists
        privilege_adverse_actions = helper.get_privilege_adverse_actions()
        if len(privilege_adverse_actions) != 1:
            raise SmokeTestFailureException(
                f'Expected 1 privilege adverse action, found: {len(privilege_adverse_actions)}'
            )

        first_adverse_action_id = privilege_adverse_actions[0]['adverseActionId']

        # Verify the adverse action matches the request payload
        helper.verify_privilege_adverse_action_matches_request(encumbrance_body)
        logger.info('First privilege encumbrance verified successfully')

        # Second encumbrance
        second_encumbrance_body = {
            'encumbranceEffectiveDate': '2025-02-02',
            'encumbranceType': 'completion of continuing education',
            'clinicalPrivilegeActionCategories': ['Unsafe Practice or Substandard Care'],
        }
        helper.encumber_privilege(second_encumbrance_body)
        logger.info('Second privilege encumbrance created successfully')

        # Verify we now have two adverse actions
        privilege_adverse_actions = helper.get_privilege_adverse_actions()
        if len(privilege_adverse_actions) != 2:
            raise SmokeTestFailureException(
                f'Expected 2 privilege adverse actions, found: {len(privilege_adverse_actions)}'
            )

        second_adverse_action_id = next(
            aa['adverseActionId']
            for aa in privilege_adverse_actions
            if aa['adverseActionId'] != first_adverse_action_id
        )

        # Verify the second adverse action matches the request payload
        helper.verify_privilege_adverse_action_matches_request(second_encumbrance_body)
        logger.info('Second privilege encumbrance verified successfully')

        # Step 2: Lift first encumbrance (privilege should remain encumbered)
        logger.info('Step 2: Lifting first privilege encumbrance...')

        lift_body = {
            'effectiveLiftDate': '2025-03-03',
        }

        helper.lift_privilege_encumbrance(lift_body, first_adverse_action_id)
        logger.info('First privilege encumbrance lifted successfully')

        # Verify privilege is still encumbered
        helper.validate_privilege_encumbered_state('encumbered')

        # Also verify the provider record is still encumbered
        helper.validate_provider_encumbered_state('encumbered')

        logger.info('Verified privilege remains encumbered after lifting first encumbrance')

        # wait 1 minute for downstream processing to complete
        # this keeps the lifting events isolated from each other
        helper.wait_for_downstream_processing()

        # Step 3: Lift final encumbrance (privilege should become unencumbered)
        logger.info('Step 3: Lifting final privilege encumbrance...')

        lift_body = {
            'effectiveLiftDate': '2025-04-04',
        }

        helper.lift_privilege_encumbrance(lift_body, second_adverse_action_id)
        logger.info('Final privilege encumbrance lifted successfully')

        # Verify privilege is now unencumbered
        helper.validate_privilege_encumbered_state('unencumbered')

        # Also verify the provider record is now unencumbered
        helper.validate_provider_encumbered_state('unencumbered')

        logger.info('Privilege encumbrance workflow test completed successfully')

    finally:
        # Clean up all created staff users
        helper.cleanup_staff_users()


def test_privilege_encumbrance_status_changes_with_license_encumbrance_workflow():
    """
    Test privilege encumbrance status values that can occur in the various encumbrance scenarios:
    1. Encumber a privilege directly
    2. Encumber the associated license
    3. Verify privilege remains 'encumbered' (not 'licenseEncumbered')
    4. Lift the privilege encumbrance
    5. Verify privilege becomes 'licenseEncumbered'
    6. Lift license encumbrance and verify privilege encumbrance is lifted automatically and set to 'unencumbered'
    """
    logger.info('Starting complex privilege and license encumbrance workflow test...')

    # Get provider data and create helper
    provider_data = call_provider_users_me_endpoint()
    helper = EncumbranceTestHelper(provider_data)

    try:
        # Step 1: Encumber the privilege directly
        logger.info('Step 1: Creating privilege encumbrance...')
        privilege_encumbrance_body = {
            'encumbranceEffectiveDate': '2024-01-15',
            'encumbranceType': 'probation',
            'clinicalPrivilegeActionCategories': [
                'Unsafe Practice or Substandard Care',
                'Non-compliance With Requirements',
                'Fraud, Deception, or Misrepresentation',
            ],
        }

        helper.encumber_privilege(privilege_encumbrance_body)
        logger.info('Privilege encumbrance created successfully')

        # Verify privilege is encumbered
        helper.validate_privilege_encumbered_state(
            expected_status='encumbered',
            # should be instantly set to encumbered
            max_wait_time=1,
            check_interval=1,
        )

        # Verify the privilege adverse action matches the request payload
        helper.verify_privilege_adverse_action_matches_request(privilege_encumbrance_body)
        logger.info('Verified privilege is directly encumbered')

        # Step 2: Encumber the associated license
        logger.info('Step 2: Creating license encumbrance...')
        license_encumbrance_body = {
            'encumbranceEffectiveDate': '2024-01-20',
            'encumbranceType': 'suspension',
            'clinicalPrivilegeActionCategories': [
                'Criminal Conviction or Adjudication',
                'Improper Supervision or Allowing Unlicensed Practice',
                'Other',
            ],
        }

        helper.encumber_license(license_encumbrance_body)
        logger.info('License encumbrance created successfully')

        # Verify the license adverse action matches the request payload
        helper.verify_license_adverse_action_matches_request(license_encumbrance_body)

        # wait 1 minute for downstream processing to complete
        # to ensure it doesn't change the privilege record
        helper.wait_for_downstream_processing()

        # Step 3: Verify privilege remains 'encumbered' (not 'licenseEncumbered')
        logger.info('Step 3: Verifying privilege remains directly encumbered...')
        helper.validate_privilege_encumbered_state(
            expected_status='encumbered',
            # only need to check once
            max_wait_time=1,
            check_interval=1,
        )
        logger.info('Verified privilege remains directly encumbered (not licenseEncumbered)')

        # Get the privilege adverse action ID for lifting
        privilege_adverse_actions = helper.get_privilege_adverse_actions()

        if len(privilege_adverse_actions) != 1:
            raise SmokeTestFailureException(
                f'Expected 1 privilege adverse action, found: {len(privilege_adverse_actions)}'
            )

        privilege_adverse_action_id = privilege_adverse_actions[0]['adverseActionId']

        # Step 4: Lift the privilege encumbrance
        logger.info('Step 4: Lifting privilege encumbrance...')
        lift_body = {'effectiveLiftDate': '2024-01-25'}
        helper.lift_privilege_encumbrance(lift_body, privilege_adverse_action_id)
        logger.info('Privilege encumbrance lifted successfully')

        # Step 5: Verify privilege becomes 'licenseEncumbered'
        logger.info('Step 5: Verifying privilege becomes licenseEncumbered...')
        helper.validate_privilege_encumbered_state(
            expected_status='licenseEncumbered',
            # should be instantly set to licenseEncumbered
            max_wait_time=1,
            check_interval=1,
        )
        logger.info('Verified privilege is now licenseEncumbered')

        # Get the license adverse action ID for lifting
        license_adverse_actions = helper.get_license_adverse_actions()

        if len(license_adverse_actions) != 1:
            raise SmokeTestFailureException(f'Expected 1 license adverse action, found: {len(license_adverse_actions)}')

        license_adverse_action_id = license_adverse_actions[0]['adverseActionId']

        # Step 6: Lift the license encumbrance
        logger.info('Step 6: Lifting license encumbrance...')
        lift_body = {'effectiveLiftDate': '2024-01-30'}
        helper.lift_license_encumbrance(lift_body, license_adverse_action_id)
        logger.info('License encumbrance lifted successfully')

        # Step 7: Verify privilege becomes 'unencumbered'
        logger.info('Step 7: Verifying privilege becomes unencumbered...')
        helper.validate_privilege_encumbered_state(expected_status='unencumbered')
        logger.info('Verified privilege is now fully unencumbered')

        # Final verification: Check that provider is also unencumbered
        provider_user_records = get_provider_user_records(helper.compact, helper.provider_id)
        provider_record = provider_user_records.get_provider_record()

        if provider_record.encumberedStatus != 'unencumbered':
            raise SmokeTestFailureException(
                f"Provider encumberedStatus should be 'unencumbered', got: {provider_record.encumberedStatus}"
            )

        if provider_record.compactEligibility != 'eligible':
            raise SmokeTestFailureException(
                f"Provider compactEligibility should be 'eligible', got: {provider_record.compactEligibility}"
            )

        logger.info('Complex privilege and license encumbrance workflow test completed successfully')

    finally:
        # Clean up all created staff users
        helper.cleanup_staff_users()


def run_encumbrance_smoke_tests():
    """
    Run the complete suite of encumbrance smoke tests.
    """
    logger.info('Starting encumbrance smoke tests...')

    try:
        # Setup test environment
        setup_test_environment()

        # Run privilege and license encumbrance tests
        test_privilege_encumbrance_status_changes_with_license_encumbrance_workflow()

        # Run license encumbrance tests
        test_license_encumbrance_workflow()

        # Run privilege encumbrance tests
        test_privilege_encumbrance_workflow()

        logger.info('All encumbrance smoke tests completed successfully!')

    except Exception as e:
        logger.error(f'Encumbrance smoke tests failed: {str(e)}')
        raise


if __name__ == '__main__':
    # Load environment variables from smoke_tests_env.json
    load_smoke_test_env()

    # Run the complete test suite
    run_encumbrance_smoke_tests()
