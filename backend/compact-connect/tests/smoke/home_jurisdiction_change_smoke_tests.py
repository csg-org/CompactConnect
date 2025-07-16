#!/usr/bin/env python3
import json
import time

import requests
from compact_configuration_smoke_tests import test_jurisdiction_configuration
from config import config, logger
from purchasing_privileges_smoke_tests import test_purchasing_privilege
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
    get_provider_user_auth_headers_cached,
    load_smoke_test_env,
)

# This script can be run locally to test the home jurisdiction change flow against a sandbox environment
# of the Compact Connect API.
# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.


TEST_EXPIRATION_DATE = '2050-04-04'


def test_home_jurisdiction_change_inactivates_privileges_when_no_license_in_new_jurisdiction():
    """
    Test that when a provider changes their home jurisdiction to a jurisdiction where they don't have a license:
    1. All their privileges are set to inactive
    2. Their compactEligibility on the provider record is set to ineligible

    We then reset their home jurisdiction back to its original location, which should make them eligible to
    purchase privileges again. The test then purchases the privilege in the same jurisdiction as the one that was
    deactivated and then verifies it is active again.

    This test assumes that you have a provider user in the test environment that is able to purchase privileges
    for a valid license.
    """
    logger.info('Running home jurisdiction change test - changing to jurisdiction with no license')

    # Get the provider's information before making any changes
    provider_info_before = call_provider_users_me_endpoint()

    original_jurisdiction = provider_info_before.get('currentHomeJurisdiction')
    logger.info(f'Original home jurisdiction: {original_jurisdiction}')
    new_jurisdiction = 'al'  # Alabama - assuming the provider doesn't have a license here


    # we must ensure we have a valid live jurisdiction configuration in place for the current, new, and privilege
    # states so the privilege can be moved over successfully
    test_jurisdiction_configuration(jurisdiction=original_jurisdiction, recreate_compact_config=True)
    test_jurisdiction_configuration(jurisdiction=new_jurisdiction, recreate_compact_config=False)
    # privilege jurisdiction
    test_jurisdiction_configuration(jurisdiction='ne', recreate_compact_config=False)

    # Purchase a privilege for the provider
    # This uses the same test_purchasing_privilege function from purchasing_privileges_smoke_tests.py
    # We delete the current privilege if present to start in a clean state
    test_purchasing_privilege(delete_current_privilege=True)

    # Get the provider's information after purchasing privilege
    provider_info_after_purchase = call_provider_users_me_endpoint()

    # Verify provider is eligible
    if provider_info_after_purchase.get('compactEligibility') != 'eligible':
        raise SmokeTestFailureException(
            f"Provider should be 'eligible' before home jurisdiction change, "
            f"but got '{provider_info_after_purchase.get('compactEligibility')}'"
        )

    # Now change the home jurisdiction to one where the provider doesn't have a license
    logger.info(f'Changing home jurisdiction to {new_jurisdiction}')

    response = requests.put(
        f'{config.api_base_url}/v1/provider-users/me/home-jurisdiction',
        headers=get_provider_user_auth_headers_cached(),
        json={'jurisdiction': new_jurisdiction},
        timeout=30,
    )

    # Verify the response status code
    if response.status_code != 200:
        raise SmokeTestFailureException(f'Expected 200 status code, got {response.status_code}: {response.text}')

    logger.info(f'Home jurisdiction change response: {response.text}')

    # Wait a moment for changes to propagate
    time.sleep(2)

    # Get the provider's information after home jurisdiction change
    provider_info_after_change = call_provider_users_me_endpoint()
    logger.info(f'Provider info after home jurisdiction change: {json.dumps(provider_info_after_change)}')

    # Verify home jurisdiction was changed
    if provider_info_after_change.get('currentHomeJurisdiction') != new_jurisdiction:
        raise SmokeTestFailureException(
            f"Expected home jurisdiction to be changed to '{new_jurisdiction}', "
            f"but got '{provider_info_after_change.get('currentHomeJurisdiction')}'"
        )

    # Verify provider is now ineligible
    if provider_info_after_change.get('compactEligibility') != 'ineligible':
        raise SmokeTestFailureException(
            f"Provider should be 'ineligible' after changing to jurisdiction with no license, "
            f"but got '{provider_info_after_change.get('compactEligibility')}'"
        )

    # Verify all privileges now have homeJurisdictionChangeStatus as inactive
    privileges_after_change = provider_info_after_change.get('privileges', [])
    ne_privilege_after_change = next(
        (privilege for privilege in privileges_after_change if privilege['jurisdiction'] == 'ne'), None
    )

    if not ne_privilege_after_change:
        raise SmokeTestFailureException('Nebraska privilege not found after home jurisdiction change')

    if ne_privilege_after_change.get('homeJurisdictionChangeStatus') != 'inactive':
        raise SmokeTestFailureException(
            f"Privilege homeJurisdictionChangeStatus should be 'inactive', "
            f"but got '{ne_privilege_after_change.get('homeJurisdictionChangeStatus')}'"
        )

    if ne_privilege_after_change.get('status') != 'inactive':
        raise SmokeTestFailureException(
            f"Privilege status should be 'inactive', but got '{ne_privilege_after_change.get('status')}'"
        )

    # change home jurisdiction back to original
    logger.info(f'Restoring original home jurisdiction: {original_jurisdiction}')
    response = requests.put(
        f'{config.api_base_url}/v1/provider-users/me/home-jurisdiction',
        headers=get_provider_user_auth_headers_cached(),
        json={'jurisdiction': original_jurisdiction},
        timeout=30,
    )

    if response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to restore original home jurisdiction: {response.status_code}: {response.text}'
        )

    # verify provider is compact eligible again
    provider_info_after_restore = call_provider_users_me_endpoint()
    if provider_info_after_restore.get('compactEligibility') != 'eligible':
        raise SmokeTestFailureException(
            f"Provider should be 'eligible' after restoring original home jurisdiction, "
            f"but got '{provider_info_after_restore.get('compactEligibility')}'"
        )

    # Now purchase the privilege again to reactivate it.

    # we've set a duplicate transaction window to prevent double charges on their cards, so
    # we wait for that period before processing the charge a second time
    time.sleep(35)
    test_purchasing_privilege(delete_current_privilege=False)

    # verify privilege is active
    provider_info_after_reactivation = call_provider_users_me_endpoint()
    privileges_after_reactivation = provider_info_after_reactivation.get('privileges', [])
    ne_privilege_after_reactivation = next(
        (privilege for privilege in privileges_after_reactivation if privilege['jurisdiction'] == 'ne'), None
    )
    if not ne_privilege_after_reactivation:
        raise SmokeTestFailureException('Nebraska privilege not found after reactivation')
    if (
        ne_privilege_after_reactivation.get('status') != 'active'
        or ne_privilege_after_reactivation.get('homeJurisdictionChangeStatus') is not None
    ):
        raise SmokeTestFailureException(
            f"Privilege should be 'active' and have no homeJurisdictionChangeStatus after reactivation, "
            f"but got '{ne_privilege_after_reactivation.get('status')}' "
            f"and '{ne_privilege_after_reactivation.get('homeJurisdictionChangeStatus')}'"
        )

    logger.info('Successfully completed home jurisdiction change test')


def add_license_for_provider(provider_record: dict, jurisdiction: str):
    """
    Add a license for a provider in a given jurisdiction
    """
    license_type = provider_record['licenses'][0]['licenseType']
    provider_id = provider_record['providerId']
    compact = provider_record['compact']
    license_record = {
        'pk': f'{compact}#PROVIDER#{provider_id}',
        'sk': f'{compact}#PROVIDER#license/{jurisdiction}/{license_type}#',
        'type': 'license',
        'providerId': provider_id,
        'compact': compact,
        'jurisdiction': jurisdiction,
        'ssnLastFour': '1234',
        'npi': '0608337260',
        'licenseNumber': 'A0608337260',
        'licenseType': 'speech-language pathologist',
        'givenName': 'Björk',
        'middleName': 'Gunnar',
        'familyName': 'Guðmundsdóttir',
        'dateOfIssuance': '2010-06-06',
        'dateOfRenewal': '2020-04-04',
        'dateOfExpiration': TEST_EXPIRATION_DATE,
        'dateOfBirth': '1985-06-06',
        'dateOfUpdate': '2024-06-06T12:59:59+00:00',
        'homeAddressStreet1': '123 A St.',
        'homeAddressStreet2': 'Apt 321',
        'homeAddressCity': 'Columbus',
        'homeAddressState': 'oh',
        'homeAddressPostalCode': '43004',
        'emailAddress': 'björk@example.com',
        'phoneNumber': '+13213214321',
        'jurisdictionUploadedLicenseStatus': 'active',
        'licenseStatusName': 'DEFINITELY_A_HUMAN',
        'jurisdictionUploadedCompactEligibility': 'eligible',
        'licenseGSIPK': 'C#aslp#J#oh',
        'licenseGSISK': 'FN#gu%C3%B0mundsd%C3%B3ttir#GN#bj%C3%B6rk',
    }
    # put the license in for the new jurisdiction
    logger.info('Adding temp license record', pk=license_record['pk'], sk=license_record['sk'])
    config.provider_user_dynamodb_table.put_item(Item=license_record)
    # give dynamodb time to propagate
    time.sleep(1)

    return license_record

def test_home_jurisdiction_change_moves_privileges_when_valid_license_in_new_jurisdiction():
    """
    Test that when a provider changes their home jurisdiction to a jurisdiction where they have a valid license:
    1. All their privileges are set to active
    2. Their compactEligibility on the provider record is set to eligible
    """
    logger.info('Running home jurisdiction change test - changing to jurisdiction with valid license')

    # Get the provider's information before making any changes
    provider_info_before = call_provider_users_me_endpoint()

    original_jurisdiction = provider_info_before.get('currentHomeJurisdiction')
    original_expiration_date = provider_info_before['licenses'][0]['dateOfExpiration']
    new_jurisdiction = 'al'  # Alabama - assuming the provider doesn't have a license here
    logger.info(f'Original home jurisdiction: {original_jurisdiction}')

    # In this test, we temporarily add a valid license for the provider in the new jurisdiction,
    # then move the user to the new jurisdiction
    # and verify that the privilege is moved to the new jurisdiction
    new_license_record = add_license_for_provider(provider_info_before, new_jurisdiction)
    try:
        # we've set a duplicate transaction window to prevent double charges on their cards, so
        # we wait for that period before processing the charge a second time
        time.sleep(35)
        test_purchasing_privilege(delete_current_privilege=True)

        # Now change the home jurisdiction so the 'ne' privilege is moved over
        logger.info(f'Changing home jurisdiction to {new_jurisdiction}')
        response = requests.put(
            f'{config.api_base_url}/v1/provider-users/me/home-jurisdiction',
            headers=get_provider_user_auth_headers_cached(),
            json={'jurisdiction': new_jurisdiction},
            timeout=30,
        )

        # Verify the response status code
        if response.status_code != 200:
            raise SmokeTestFailureException(f'Expected 200 status code, got {response.status_code}: {response.text}')

        logger.info(f'Home jurisdiction change response: {response.text}')

        # get the provider's information after the home jurisdiction change
        provider_info_after_change = call_provider_users_me_endpoint()

        # verify the privilege is moved to the new jurisdiction
        privileges_after_change = provider_info_after_change.get('privileges', [])
        ne_privilege_after_change = next(
            (privilege for privilege in privileges_after_change if privilege['jurisdiction'] == 'ne'), None
        )
        if not ne_privilege_after_change:
            raise SmokeTestFailureException('Nebraska privilege not found after home jurisdiction change')
        if ne_privilege_after_change.get('status') != 'active':
            raise SmokeTestFailureException(
                f"Privilege should be 'active', but got '{ne_privilege_after_change.get('status')}'"
            )
        logger.info('privilege is active after home jurisdiction change')

        if ne_privilege_after_change.get('homeJurisdictionChangeStatus') is not None:
            raise SmokeTestFailureException(
                f"Privilege should not have 'homeJurisdictionChangeStatus' field but found"
                f" '{ne_privilege_after_change.get('homeJurisdictionChangeStatus')}'"
            )

        # verify the privilege licenseJurisdiction is the new jurisdiction
        if ne_privilege_after_change.get('licenseJurisdiction') != new_jurisdiction:
            raise SmokeTestFailureException(
                f"Privilege licenseJurisdiction should be '{new_jurisdiction}', "
                f"but got '{ne_privilege_after_change.get('licenseJurisdiction')}'"
            )
        logger.info('privilege licenseJurisdiction is the new jurisdiction')

        # verify the expiration date is the same as the license expiration date
        if ne_privilege_after_change.get('dateOfExpiration') != TEST_EXPIRATION_DATE:
            raise SmokeTestFailureException(
                f"Privilege dateOfExpiration should be '{TEST_EXPIRATION_DATE}', "
                f"but got '{ne_privilege_after_change.get('dateOfExpiration')}'"
            )
        logger.info('privilege dateOfExpiration is the new expiration date')
        # now move the home jurisdiction back to the original jurisdiction and verify the privilege is moved back
        logger.info(f'Restoring original home jurisdiction: {original_jurisdiction}')
        response = requests.put(
            f'{config.api_base_url}/v1/provider-users/me/home-jurisdiction',
            headers=get_provider_user_auth_headers_cached(),
            json={'jurisdiction': original_jurisdiction},
            timeout=30,
        )

        if response.status_code != 200:
            raise SmokeTestFailureException(f'Expected 200 status code, got {response.status_code}: {response.text}')

        logger.info(f'Home jurisdiction change response: {response.text}')

        # get the provider's information after the home jurisdiction change
        provider_info_after_restore = call_provider_users_me_endpoint()

        # verify the privilege is moved back to the original jurisdiction
        privileges_after_restore = provider_info_after_restore.get('privileges', [])
        ne_privilege_after_restore = next(
            (privilege for privilege in privileges_after_restore if privilege['jurisdiction'] == 'ne'), None
        )
        if not ne_privilege_after_restore:
            raise SmokeTestFailureException('Nebraska privilege not found after home jurisdiction change')
        if ne_privilege_after_restore.get('status') != 'active':
            raise SmokeTestFailureException(
                f"Privilege should be 'active', but got '{ne_privilege_after_restore.get('status')}'"
            )
        logger.info('privilege still has active status')

        if ne_privilege_after_restore.get('homeJurisdictionChangeStatus') is not None:
            raise SmokeTestFailureException(
                f"Privilege should not have 'homeJurisdictionChangeStatus' field but found"
                f" '{ne_privilege_after_restore.get('homeJurisdictionChangeStatus')}'"
            )

        # verify the privilege licenseJurisdiction is the original jurisdiction
        if ne_privilege_after_restore.get('licenseJurisdiction') != original_jurisdiction:
            raise SmokeTestFailureException(
                f"Privilege licenseJurisdiction should be '{original_jurisdiction}', "
                f"but got '{ne_privilege_after_restore.get('licenseJurisdiction')}'"
            )
        logger.info('privilege licenseJurisdiction is the original jurisdiction')

        # verify the expiration date is the same as the license expiration date
        if ne_privilege_after_restore.get('dateOfExpiration') != original_expiration_date:
            raise SmokeTestFailureException(
                f"Privilege dateOfExpiration should be '{original_expiration_date}', "
                f"but got '{ne_privilege_after_restore.get('dateOfExpiration')}'"
            )
        logger.info('privilege dateOfExpiration is the original expiration date')

        logger.info('Successfully completed home jurisdiction change test')
    except Exception as e:  # noqa: BLE001
        raise SmokeTestFailureException(f'Unexpected exception occurred: {str(e)}') from e
    finally:
        # Now delete the new license record
        logger.info('Deleting temp license record', pk=new_license_record['pk'], sk=new_license_record['sk'])
        config.provider_user_dynamodb_table.delete_item(
            Key={'pk': new_license_record['pk'], 'sk': new_license_record['sk']}
        )


if __name__ == '__main__':
    # Load environment variables from smoke_tests_env.json
    load_smoke_test_env()

    # Run test
    test_home_jurisdiction_change_inactivates_privileges_when_no_license_in_new_jurisdiction()
    test_home_jurisdiction_change_moves_privileges_when_valid_license_in_new_jurisdiction()
