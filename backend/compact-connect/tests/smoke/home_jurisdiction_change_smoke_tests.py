#!/usr/bin/env python3
import json
import time

import requests
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


def test_home_jurisdiction_change_inactivates_privileges_when_no_license_in_new_jurisdiction():
    """
    Test that when a provider changes their home jurisdiction to a jurisdiction where they don't have a license:
    1. All their privileges are set to inactive
    2. Their compactEligibility on the provider record is set to ineligible

    We then reset their home jurisdiction back to its original location, which should make them eligible to
    purchase privileges again. The test purchases the same privilege and then verifies it is active again.

    This test assumes that you have a provider user in the test environment that is able to purchase privileges
    for a valid license.
    """
    logger.info('Running home jurisdiction change test - changing to jurisdiction with no license')

    # Get the provider's information before making any changes
    provider_info_before = call_provider_users_me_endpoint()

    original_jurisdiction = provider_info_before.get('currentHomeJurisdiction')
    logger.info(f'Original home jurisdiction: {original_jurisdiction}')

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
    new_jurisdiction = 'al'  # Alabama - assuming the provider doesn't have a license here

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

    # now purchase privilege again to reactivate it
    # we do not delete the record so we ensure the existing record was updated as expected.

    # we've set a duplicate transaction window to prevent double charges on their cards
    # wait until processing the charge a second time
    time.sleep(5)
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


if __name__ == '__main__':
    # Load environment variables from smoke_tests_env.json
    load_smoke_test_env()

    # Run test
    test_home_jurisdiction_change_inactivates_privileges_when_no_license_in_new_jurisdiction()
