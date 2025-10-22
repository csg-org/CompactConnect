#!/usr/bin/env python3
"""
Smoke tests for investigation functionality.

This script tests the end-to-end investigation workflow for both licenses and privileges,
including creating investigations and closing them through the API endpoints.
"""

import time

import requests
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


def clean_investigation_records():
    """
    Clean up any existing investigation and encumbrance records for the provider to start in a clean state.
    """
    logger.info('Cleaning up existing investigation and encumbrance records...')

    # Get all provider database records
    all_records = get_all_provider_database_records()

    for record in all_records:
        if record.get('type') == 'license' or record.get('type') == 'privilege':
            if record.get('investigationStatus') == 'underInvestigation':
                logger.info(
                    f'Removing investigation and encumbrance status from {record.get("type")} '
                    f'{record.get("pk")} / {record.get("sk")}'
                )
                dynamodb_table = get_provider_user_dynamodb_table()
                dynamodb_table.update_item(
                    Key={'pk': record['pk'], 'sk': record['sk']},
                    UpdateExpression='REMOVE investigationStatus, REMOVE encumbranceStatus',
                )

    # Filter for investigation and encumbrance records
    investigation_records = [record for record in all_records if record.get('type') == 'investigation']
    encumbrance_records = [record for record in all_records if record.get('type') == 'adverseAction']

    # Filter for investigation and encumbrance update records
    investigation_update_records = [
        record
        for record in all_records
        if record.get('type') in ['privilegeUpdate', 'licenseUpdate'] and record.get('updateType') == 'investigation'
    ]
    encumbrance_update_records = [
        record
        for record in all_records
        if record.get('type') in ['privilegeUpdate', 'licenseUpdate'] and record.get('updateType') == 'encumbrance'
    ]

    if (
        not investigation_records
        and not encumbrance_records
        and not investigation_update_records
        and not encumbrance_update_records
    ):
        logger.info('No investigation or encumbrance records found to clean up')
        return

    # Delete each investigation and encumbrance record
    dynamodb_table = get_provider_user_dynamodb_table()

    for record in investigation_records:
        pk = record['pk']
        sk = record['sk']
        logger.info(f'Deleting investigation record: {pk} / {sk}')
        dynamodb_table.delete_item(Key={'pk': pk, 'sk': sk})

    for record in encumbrance_records:
        pk = record['pk']
        sk = record['sk']
        logger.info(f'Deleting encumbrance record: {pk} / {sk}')
        dynamodb_table.delete_item(Key={'pk': pk, 'sk': sk})

    for record in investigation_update_records:
        pk = record['pk']
        sk = record['sk']
        logger.info(f'Deleting investigation update record: {pk} / {sk}')
        dynamodb_table.delete_item(Key={'pk': pk, 'sk': sk})

    for record in encumbrance_update_records:
        pk = record['pk']
        sk = record['sk']
        logger.info(f'Deleting encumbrance update record: {pk} / {sk}')
        dynamodb_table.delete_item(Key={'pk': pk, 'sk': sk})

    logger.info(
        f'Cleaned up {len(investigation_records)} investigation records, '
        f'{len(encumbrance_records)} encumbrance records, '
        f'{len(investigation_update_records)} investigation update records, and '
        f'{len(encumbrance_update_records)} encumbrance update records'
    )


def setup_test_environment():
    """
    Set up the test environment by cleaning investigations.
    """
    logger.info('Setting up test environment...')

    # Clean up any existing investigations
    clean_investigation_records()

    logger.info('Test environment setup complete')


def _get_license_data_from_provider_response(provider_data: dict, jurisdiction: str, license_type: str):
    """Get license data from provider response."""
    return next(
        (
            lic
            for lic in provider_data['licenses']
            if lic['jurisdiction'] == jurisdiction and lic['licenseType'] == license_type
        ),
        None,
    )


def _get_privilege_data_from_provider_response(provider_data: dict, jurisdiction: str, license_type: str):
    """Get privilege data from provider response."""
    return next(
        (
            priv
            for priv in provider_data['privileges']
            if priv['jurisdiction'] == jurisdiction and priv['licenseType'] == license_type
        ),
        None,
    )


def _verify_no_investigation_exists(record_type: str, jurisdiction: str, license_type: str):
    """
    Verify that no open investigation records exist in the database and no investigation status or objects on the
    record.

    :param record_type: 'privilege' or 'license'
    :param jurisdiction: The jurisdiction of the record
    :param license_type: The license type of the record
    """
    # Check database for open investigation records
    all_records = get_all_provider_database_records()
    existing_investigations = [
        record for record in all_records if record.get('type') == 'investigation' and record.get('closeDate') is None
    ]

    if existing_investigations:
        raise SmokeTestFailureException('Open investigation already exists before creation test')

    # Check API for investigation status
    provider_data = call_provider_users_me_endpoint()

    if record_type == 'privilege':
        record_data = _get_privilege_data_from_provider_response(provider_data, jurisdiction, license_type)
    else:
        record_data = _get_license_data_from_provider_response(provider_data, jurisdiction, license_type)

    if not record_data:
        raise SmokeTestFailureException(f'{record_type.title()} not found before investigation creation')

    if record_data.get('investigationStatus') is not None:
        raise SmokeTestFailureException(
            f'Expected {record_type} to not have investigation status, '
            f'but got: {record_data.get("investigationStatus")}'
        )

    if record_data.get('investigations'):
        raise SmokeTestFailureException('Investigation objects still exist in API response')


def _verify_investigation_exists(record_type: str, jurisdiction: str, license_type: str):
    """
    Verify that an open investigation exists and the record has investigation status.

    :param record_type: 'privilege' or 'license'
    :param jurisdiction: The jurisdiction of the record
    :param license_type: The license type of the record
    :return: The investigation ID
    """
    # Check database for investigation records
    all_records = get_all_provider_database_records()
    investigation_records = [
        record
        for record in all_records
        if record.get('type') == 'investigation'
        and record.get('investigationAgainst') == record_type
        and record.get('jurisdiction') == jurisdiction
        and record.get('licenseType') == license_type
        and record.get('closeDate') is None
    ]

    if not investigation_records:
        raise SmokeTestFailureException(f'No open {record_type} investigation found to close')

    # Check API for investigation status
    provider_data = call_provider_users_me_endpoint()

    if record_type == 'privilege':
        record_data = _get_privilege_data_from_provider_response(provider_data, jurisdiction, license_type)
    else:
        record_data = _get_license_data_from_provider_response(provider_data, jurisdiction, license_type)

    if not record_data:
        raise SmokeTestFailureException(f'{record_type.title()} not found before investigation closing')

    if record_data.get('investigationStatus') != 'underInvestigation':
        raise SmokeTestFailureException(
            f'Expected {record_type} to have investigation status "underInvestigation" before closing, '
            f'but got: {record_data.get("investigationStatus")}'
        )

    if not record_data.get('investigations'):
        raise SmokeTestFailureException('Investigation object not found in API response before closing')

    return investigation_records[0]['investigationId']


def test_create_privilege_investigation(auth_headers):
    """Test creating a privilege investigation."""
    logger.info('Testing privilege investigation creation...')

    provider_data = call_provider_users_me_endpoint()
    provider_id = provider_data['providerId']
    compact = provider_data['compact']
    jurisdiction = provider_data['privileges'][0]['jurisdiction']
    license_type = provider_data['privileges'][0]['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(license_type)

    _verify_no_investigation_exists('privilege', jurisdiction, license_type)

    # Create investigation (empty body required)
    response = requests.post(
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}/privileges/jurisdiction/{jurisdiction}'
        f'/licenseType/{license_type_abbreviation}/investigation',
        json={},
        headers=auth_headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to create privilege investigation: {response.status_code} - {response.text}'
        )

    logger.info('Privilege investigation created successfully')

    # Wait for the investigation to be processed and DynamoDB eventual consistency
    time.sleep(5)

    _verify_investigation_exists('privilege', jurisdiction, license_type)


def test_create_license_investigation(auth_headers):
    """Test creating a license investigation."""
    logger.info('Testing license investigation creation...')

    provider_data = call_provider_users_me_endpoint()
    provider_id = provider_data['providerId']
    compact = provider_data['compact']
    jurisdiction = provider_data['licenseJurisdiction']
    license_type = provider_data['licenses'][0]['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(license_type)

    _verify_no_investigation_exists('license', jurisdiction, license_type)

    # Create investigation (empty body required)
    response = requests.post(
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}/licenses/jurisdiction/{jurisdiction}'
        f'/licenseType/{license_type_abbreviation}/investigation',
        json={},
        headers=auth_headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to create license investigation: {response.status_code} - {response.text}'
        )

    logger.info('License investigation created successfully')

    # Wait for the investigation to be processed and DynamoDB eventual consistency
    time.sleep(5)

    _verify_investigation_exists('license', jurisdiction, license_type)


def test_close_privilege_investigation(auth_headers):
    """Test closing a privilege investigation."""
    logger.info('Testing privilege investigation closing...')

    provider_data = call_provider_users_me_endpoint()
    provider_id = provider_data['providerId']
    compact = provider_data['compact']
    jurisdiction = provider_data['privileges'][0]['jurisdiction']
    license_type = provider_data['privileges'][0]['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(license_type)

    investigation_id = _verify_investigation_exists('privilege', jurisdiction, license_type)

    # Close investigation (empty JSON body)
    response = requests.patch(
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}/privileges/jurisdiction/{jurisdiction}'
        f'/licenseType/{license_type_abbreviation}/investigation/{investigation_id}',
        json={},
        headers=auth_headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to close privilege investigation: {response.status_code} - {response.text}'
        )

    logger.info('Privilege investigation closed successfully')

    # Wait for the investigation to be processed and DynamoDB eventual consistency
    time.sleep(5)

    _verify_no_investigation_exists('privilege', jurisdiction, license_type)


def test_close_license_investigation(auth_headers):
    """Test closing a license investigation."""
    logger.info('Testing license investigation closing...')

    provider_data = call_provider_users_me_endpoint()
    provider_id = provider_data['providerId']
    compact = provider_data['compact']
    jurisdiction = provider_data['licenseJurisdiction']
    license_type = provider_data['licenses'][0]['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(license_type)

    investigation_id = _verify_investigation_exists('license', jurisdiction, license_type)

    # Close investigation (empty JSON body)
    response = requests.patch(
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}/licenses/jurisdiction/{jurisdiction}'
        f'/licenseType/{license_type_abbreviation}/investigation/{investigation_id}',
        headers=auth_headers,
        json={},
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to close license investigation: {response.status_code} - {response.text}'
        )

    logger.info('License investigation closed successfully')

    # Wait for the investigation to be processed and DynamoDB eventual consistency
    time.sleep(5)

    _verify_no_investigation_exists('license', jurisdiction, license_type)


def test_close_privilege_investigation_with_encumbrance(auth_headers):
    """Test closing a privilege investigation with encumbrance creation."""
    logger.info('Testing privilege investigation closing with encumbrance...')

    provider_data = call_provider_users_me_endpoint()
    provider_id = provider_data['providerId']
    compact = provider_data['compact']
    jurisdiction = provider_data['privileges'][0]['jurisdiction']
    license_type = provider_data['privileges'][0]['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(license_type)

    # Verify initial state: an open investigation should exist
    investigation_id = _verify_investigation_exists('privilege', jurisdiction, license_type)

    # Verify privilege is not already encumbered (no adverse actions)
    privilege_data = _get_privilege_data_from_provider_response(provider_data, jurisdiction, license_type)
    if privilege_data.get('adverseActions'):
        raise SmokeTestFailureException(
            f'Expected privilege to not have adverse actions before closing with encumbrance, '
            f'but got: {privilege_data.get("adverseActions")}'
        )

    # Close investigation with encumbrance
    close_data = {
        'encumbrance': {
            'encumbranceEffectiveDate': '2024-01-15',
            'encumbranceType': 'fine',
            'clinicalPrivilegeActionCategory': 'Unsafe Practice or Substandard Care',
        },
    }

    response = requests.patch(
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}/privileges/jurisdiction/{jurisdiction}'
        f'/licenseType/{license_type_abbreviation}/investigation/{investigation_id}',
        json=close_data,
        headers=auth_headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to close privilege investigation with encumbrance: {response.status_code} - {response.text}'
        )

    logger.info('Privilege investigation closed with encumbrance successfully')

    # Wait for the investigation to be processed and DynamoDB eventual consistency
    time.sleep(5)

    _verify_no_investigation_exists('privilege', jurisdiction, license_type)
    # Verify encumbrance was created (adverse action exists)
    provider_data = call_provider_users_me_endpoint()
    privilege_data = _get_privilege_data_from_provider_response(provider_data, jurisdiction, license_type)

    if not privilege_data.get('adverseActions'):
        raise SmokeTestFailureException(
            f'Expected privilege to have adverse actions after closing with encumbrance, '
            f'but got: {privilege_data.get("adverseActions")}'
        )

    logger.info('Privilege investigation closing with encumbrance verified successfully')


def main():
    """Run all investigation smoke tests."""
    logger.info('Starting investigation smoke tests...')

    # Initialize variables for cleanup
    staff_user_email = None
    staff_user_sub = None

    try:
        # Load test environment
        load_smoke_test_env()

        # Set up test environment
        setup_test_environment()

        # Create test staff user
        staff_user_email = 'test-investigation-admin@example.com'
        staff_user_sub = create_test_staff_user(
            email=staff_user_email,
            compact='aslp',
            jurisdiction='ne',
            permissions={'actions': {'admin'}, 'jurisdictions': {'ne': {'admin'}, 'co': {'admin'}, 'ky': {'admin'}}},
        )

        # Get staff user auth headers once for reuse
        auth_headers = get_staff_user_auth_headers(staff_user_email)

        # Run tests
        setup_test_environment()
        test_create_privilege_investigation(auth_headers)
        test_close_privilege_investigation(auth_headers)

        # Test closing with encumbrance
        setup_test_environment()
        test_create_privilege_investigation(auth_headers)
        test_close_privilege_investigation_with_encumbrance(auth_headers)

        # Test closing a license investigation
        setup_test_environment()
        test_create_license_investigation(auth_headers)
        test_close_license_investigation(auth_headers)

    except Exception as e:
        logger.error(f'Investigation smoke tests failed: {str(e)}')
        raise
    finally:
        # Clean up test staff user
        if staff_user_email and staff_user_sub:
            delete_test_staff_user(staff_user_email, staff_user_sub, 'aslp')
        clean_investigation_records()

    logger.info('All investigation smoke tests passed!')


if __name__ == '__main__':
    main()
