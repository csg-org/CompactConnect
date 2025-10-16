#!/usr/bin/env python3
"""
Smoke tests for investigation functionality.

This script tests the end-to-end investigation workflow for both licenses and privileges,
including creating investigations and closing them through the API endpoints.
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


def clean_investigation_records():
    """
    Clean up any existing investigation records for the provider to start in a clean state.
    """
    logger.info('Cleaning up existing investigation records...')

    # Get all provider database records
    all_records = get_all_provider_database_records()

    # Filter for investigation records
    investigation_records = [record for record in all_records if record.get('type') == 'investigation']

    if not investigation_records:
        logger.info('No investigation records found to clean up')
        return

    # Delete each investigation record
    dynamodb_table = get_provider_user_dynamodb_table()
    for record in investigation_records:
        pk = record['pk']
        sk = record['sk']
        logger.info(f'Deleting investigation record: {pk} / {sk}')
        dynamodb_table.delete_item(Key={'pk': pk, 'sk': sk})

    logger.info(f'Cleaned up {len(investigation_records)} investigation records')


def _remove_investigation_status_from_license_and_privilege():
    """Remove investigation status from license and privilege records."""
    # Get all provider database records
    all_records = get_all_provider_database_records()

    for record in all_records:
        if record.get('type') == 'license' or record.get('type') == 'privilege':
            if record.get('investigationStatus') == 'underInvestigation':
                logger.info(
                    f'Removing investigation status from {record.get("type")} {record.get("pk")} / {record.get("sk")}'
                )
                dynamodb_table = get_provider_user_dynamodb_table()
                dynamodb_table.update_item(
                    Key={'pk': record['pk'], 'sk': record['sk']},
                    UpdateExpression='REMOVE investigationStatus',
                )


def setup_test_environment():
    """
    Set up the test environment by cleaning investigations and purchasing a privilege.
    """
    logger.info('Setting up test environment...')

    # Clean up any existing investigations
    clean_investigation_records()

    # Remove investigation status from license and privilege if present
    _remove_investigation_status_from_license_and_privilege()

    # Purchase a privilege to ensure we have one to test with
    logger.info('Purchasing a privilege for testing...')
    test_purchasing_privilege()

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


def test_create_privilege_investigation():
    """Test creating a privilege investigation."""
    logger.info('Testing privilege investigation creation...')

    # Get provider data
    provider_data = call_provider_users_me_endpoint()
    provider_id = provider_data['providerId']
    compact = provider_data['compact']
    jurisdiction = provider_data['licenseJurisdiction']
    license_type = provider_data['licenses'][0]['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(compact, license_type)

    # Get staff user auth headers
    auth_headers = get_staff_user_auth_headers()

    # Create investigation
    investigation_data = {
        'investigationStartDate': '2024-01-01',
    }

    response = requests.post(
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}/privileges/jurisdiction/{jurisdiction}/licenseType/{license_type_abbreviation}/investigation',
        json=investigation_data,
        headers=auth_headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to create privilege investigation: {response.status_code} - {response.text}'
        )

    logger.info('Privilege investigation created successfully')

    # Wait for the investigation to be processed
    time.sleep(5)

    # Verify the privilege now has investigation status
    updated_provider_data = call_provider_users_me_endpoint()
    privilege_data = _get_privilege_data_from_provider_response(updated_provider_data, jurisdiction, license_type)

    if not privilege_data:
        raise SmokeTestFailureException('Privilege not found after investigation creation')

    if privilege_data.get('investigationStatus') != 'underInvestigation':
        status = privilege_data.get("investigationStatus")
        raise SmokeTestFailureException(
            f'Expected privilege to have investigation status "underInvestigation", but got: {status}'
        )

    logger.info('Privilege investigation status verified successfully')


def test_create_license_investigation():
    """Test creating a license investigation."""
    logger.info('Testing license investigation creation...')

    # Get provider data
    provider_data = call_provider_users_me_endpoint()
    provider_id = provider_data['providerId']
    compact = provider_data['compact']
    jurisdiction = provider_data['licenseJurisdiction']
    license_type = provider_data['licenses'][0]['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(compact, license_type)

    # Get staff user auth headers
    auth_headers = get_staff_user_auth_headers()

    # Create investigation
    investigation_data = {
        'investigationStartDate': '2024-01-01',
    }

    response = requests.post(
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}/licenses/jurisdiction/{jurisdiction}/licenseType/{license_type_abbreviation}/investigation',
        json=investigation_data,
        headers=auth_headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to create license investigation: {response.status_code} - {response.text}'
        )

    logger.info('License investigation created successfully')

    # Wait for the investigation to be processed
    time.sleep(5)

    # Verify the license now has investigation status
    updated_provider_data = call_provider_users_me_endpoint()
    license_data = _get_license_data_from_provider_response(updated_provider_data, jurisdiction, license_type)

    if not license_data:
        raise SmokeTestFailureException('License not found after investigation creation')

    if license_data.get('investigationStatus') != 'underInvestigation':
        status = license_data.get("investigationStatus")
        raise SmokeTestFailureException(
            f'Expected license to have investigation status "underInvestigation", but got: {status}'
        )

    logger.info('License investigation status verified successfully')


def test_close_privilege_investigation():
    """Test closing a privilege investigation."""
    logger.info('Testing privilege investigation closing...')

    # Get provider data
    provider_data = call_provider_users_me_endpoint()
    provider_id = provider_data['providerId']
    compact = provider_data['compact']
    jurisdiction = provider_data['licenseJurisdiction']
    license_type = provider_data['licenses'][0]['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(compact, license_type)

    # Get staff user auth headers
    auth_headers = get_staff_user_auth_headers()

    # Get investigation ID from database
    all_records = get_all_provider_database_records()
    investigation_records = [
        record
        for record in all_records
        if record.get('type') == 'investigation'
        and record.get('investigationAgainst') == 'privilege'
        and record.get('jurisdiction') == jurisdiction
        and record.get('licenseType') == license_type
    ]

    if not investigation_records:
        raise SmokeTestFailureException('No privilege investigation found to close')

    investigation_id = investigation_records[0]['investigationId']

    # Close investigation
    close_data = {
        'investigationCloseDate': '2024-01-15',
    }

    response = requests.patch(
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}/privileges/jurisdiction/{jurisdiction}/licenseType/{license_type_abbreviation}/investigation/{investigation_id}',
        json=close_data,
        headers=auth_headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to close privilege investigation: {response.status_code} - {response.text}'
        )

    logger.info('Privilege investigation closed successfully')

    # Wait for the investigation to be processed
    time.sleep(5)

    # Verify the privilege no longer has investigation status
    updated_provider_data = call_provider_users_me_endpoint()
    privilege_data = _get_privilege_data_from_provider_response(updated_provider_data, jurisdiction, license_type)

    if not privilege_data:
        raise SmokeTestFailureException('Privilege not found after investigation closing')

    if privilege_data.get('investigationStatus') is not None:
        raise SmokeTestFailureException(
            f'Expected privilege to not have investigation status, but got: {privilege_data.get("investigationStatus")}'
        )

    logger.info('Privilege investigation closing verified successfully')


def test_close_license_investigation():
    """Test closing a license investigation."""
    logger.info('Testing license investigation closing...')

    # Get provider data
    provider_data = call_provider_users_me_endpoint()
    provider_id = provider_data['providerId']
    compact = provider_data['compact']
    jurisdiction = provider_data['licenseJurisdiction']
    license_type = provider_data['licenses'][0]['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(compact, license_type)

    # Get staff user auth headers
    auth_headers = get_staff_user_auth_headers()

    # Get investigation ID from database
    all_records = get_all_provider_database_records()
    investigation_records = [
        record
        for record in all_records
        if record.get('type') == 'investigation'
        and record.get('investigationAgainst') == 'license'
        and record.get('jurisdiction') == jurisdiction
        and record.get('licenseType') == license_type
    ]

    if not investigation_records:
        raise SmokeTestFailureException('No license investigation found to close')

    investigation_id = investigation_records[0]['investigationId']

    # Close investigation
    close_data = {
        'investigationCloseDate': '2024-01-15',
    }

    response = requests.patch(
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}/licenses/jurisdiction/{jurisdiction}/licenseType/{license_type_abbreviation}/investigation/{investigation_id}',
        json=close_data,
        headers=auth_headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to close license investigation: {response.status_code} - {response.text}'
        )

    logger.info('License investigation closed successfully')

    # Wait for the investigation to be processed
    time.sleep(5)

    # Verify the license no longer has investigation status
    updated_provider_data = call_provider_users_me_endpoint()
    license_data = _get_license_data_from_provider_response(updated_provider_data, jurisdiction, license_type)

    if not license_data:
        raise SmokeTestFailureException('License not found after investigation closing')

    if license_data.get('investigationStatus') is not None:
        raise SmokeTestFailureException(
            f'Expected license to not have investigation status, but got: {license_data.get("investigationStatus")}'
        )

    logger.info('License investigation closing verified successfully')


def test_close_privilege_investigation_with_encumbrance():
    """Test closing a privilege investigation with encumbrance creation."""
    logger.info('Testing privilege investigation closing with encumbrance...')

    # Get provider data
    provider_data = call_provider_users_me_endpoint()
    provider_id = provider_data['providerId']
    compact = provider_data['compact']
    jurisdiction = provider_data['licenseJurisdiction']
    license_type = provider_data['licenses'][0]['licenseType']
    license_type_abbreviation = get_license_type_abbreviation(compact, license_type)

    # Get staff user auth headers
    auth_headers = get_staff_user_auth_headers()

    # Create a new investigation first
    investigation_data = {
        'investigationStartDate': '2024-01-01',
    }

    response = requests.post(
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}/privileges/jurisdiction/{jurisdiction}/licenseType/{license_type_abbreviation}/investigation',
        json=investigation_data,
        headers=auth_headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to create privilege investigation: {response.status_code} - {response.text}'
        )

    # Wait for the investigation to be processed
    time.sleep(5)

    # Get investigation ID from database
    all_records = get_all_provider_database_records()
    investigation_records = [
        record
        for record in all_records
        if record.get('type') == 'investigation'
        and record.get('investigationAgainst') == 'privilege'
        and record.get('jurisdiction') == jurisdiction
        and record.get('licenseType') == license_type
        and record.get('investigationCloseDate') is None
    ]

    if not investigation_records:
        raise SmokeTestFailureException('No open privilege investigation found to close')

    investigation_id = investigation_records[0]['investigationId']

    # Close investigation with encumbrance
    close_data = {
        'investigationCloseDate': '2024-01-15',
        'encumbrance': {
            'encumbranceEffectiveDate': '2024-01-15',
            'encumbranceType': 'fine',
            'clinicalPrivilegeActionCategory': 'restriction',
        },
    }

    response = requests.patch(
        f'{config.api_base_url}/v1/compacts/{compact}/providers/{provider_id}/privileges/jurisdiction/{jurisdiction}/licenseType/{license_type_abbreviation}/investigation/{investigation_id}',
        json=close_data,
        headers=auth_headers,
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to close privilege investigation with encumbrance: {response.status_code} - {response.text}'
        )

    logger.info('Privilege investigation closed with encumbrance successfully')

    # Wait for the investigation to be processed
    time.sleep(5)

    # Verify the privilege no longer has investigation status
    updated_provider_data = call_provider_users_me_endpoint()
    privilege_data = _get_privilege_data_from_provider_response(updated_provider_data, jurisdiction, license_type)

    if not privilege_data:
        raise SmokeTestFailureException('Privilege not found after investigation closing')

    if privilege_data.get('investigationStatus') is not None:
        raise SmokeTestFailureException(
            f'Expected privilege to not have investigation status, but got: {privilege_data.get("investigationStatus")}'
        )

    # Verify encumbrance was created
    if privilege_data.get('encumberedStatus') != 'encumbered':
        raise SmokeTestFailureException(
            f'Expected privilege to be encumbered, but got: {privilege_data.get("encumberedStatus")}'
        )

    logger.info('Privilege investigation closing with encumbrance verified successfully')


def main():
    """Run all investigation smoke tests."""
    logger.info('Starting investigation smoke tests...')

    try:
        # Load test environment
        load_smoke_test_env()

        # Set up test environment
        setup_test_environment()

        # Create test staff user
        create_test_staff_user()

        # Run tests
        test_create_privilege_investigation()
        test_close_privilege_investigation()

        # Set up for license investigation tests
        setup_test_environment()
        test_create_license_investigation()
        test_close_license_investigation()

        # Test closing with encumbrance
        setup_test_environment()
        test_close_privilege_investigation_with_encumbrance()

        logger.info('All investigation smoke tests passed!')

    except Exception as e:
        logger.error(f'Investigation smoke tests failed: {str(e)}')
        raise
    finally:
        # Clean up test staff user
        delete_test_staff_user()


if __name__ == '__main__':
    main()
