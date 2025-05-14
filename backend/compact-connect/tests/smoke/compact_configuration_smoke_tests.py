# ruff: noqa: T201 we use print statements for smoke testing
#!/usr/bin/env python3
import json

import requests
from smoke_common import (
    COMPACTS,
    SmokeTestFailureException,
    create_test_staff_user,
    delete_test_staff_user,
    get_api_base_url,
    get_staff_user_auth_headers,
    load_smoke_test_env,
)

# This script is used to test the compact configuration functionality against a sandbox environment
# of the Compact Connect API.

# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.


def test_active_member_jurisdictions():
    """
    Test that the active member jurisdictions from cdk.json match the jurisdictions returned by the API.
    """
    print('Testing active member jurisdictions...')

    # Get active_compact_member_jurisdictions from cdk.json
    with open('cdk.json') as context_file:
        cdk_context = json.load(context_file)['context']
        active_member_jurisdictions = cdk_context.get('active_compact_member_jurisdictions', {})

    if not active_member_jurisdictions:
        raise SmokeTestFailureException('No active_compact_member_jurisdictions found in cdk.json')

    for compact in COMPACTS:
        # Call the public endpoint to get active member jurisdictions
        response = requests.get(url=f'{get_api_base_url()}/v1/public/compacts/{compact}/jurisdictions', timeout=10)

        if response.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to GET active member jurisdictions for compact {compact}. Response: {response.json()}'
            )

        # Get the API response jurisdictions
        api_jurisdictions = response.json()
        api_jurisdiction_abbrs = [j['postalAbbreviation'].lower() for j in api_jurisdictions]

        # Get the expected jurisdictions from cdk.json
        expected_jurisdictions = active_member_jurisdictions.get(compact, [])
        expected_jurisdiction_abbrs = [j.lower() for j in expected_jurisdictions]

        # Verify that the active member jurisdictions match
        if sorted(api_jurisdiction_abbrs) != sorted(expected_jurisdiction_abbrs):
            raise SmokeTestFailureException(
                f'Active member jurisdictions mismatch for compact {compact}. '
                f'Expected: {sorted(expected_jurisdiction_abbrs)}, '
                f'Got: {sorted(api_jurisdiction_abbrs)}'
            )

        print(f'Successfully verified active member jurisdictions for compact {compact}')


def test_compact_configuration():
    """
    Test that a compact admin can update and retrieve compact configuration.
    """
    print('Testing compact configuration...')

    # Create a test compact admin user
    compact = COMPACTS[0]  # Use the first compact for testing
    test_email = f'test-compact-admin-{compact}@ccSmokeTestFakeEmail.com'
    permissions = {'actions': {'admin'}, 'jurisdictions': {}}

    try:
        # Create the test user
        user_sub = create_test_staff_user(
            email=test_email,
            compact=compact,
            jurisdiction=None,
            permissions=permissions,
        )

        # Get auth headers for the test user
        headers = get_staff_user_auth_headers(test_email)

        # Create test compact configuration data
        compact_config = {
            'compactCommissionFee': {'feeAmount': 15.00, 'feeType': 'FLAT_RATE'},
            'licenseeRegistrationEnabled': True,
            'compactOperationsTeamEmails': ['ops-test@ccSmokeTestFakeEmail.com'],
            'compactAdverseActionsNotificationEmails': ['adverse-test@ccSmokeTestFakeEmail.com'],
            'compactSummaryReportNotificationEmails': ['summary-test@ccSmokeTestFakeEmail.com'],
            'transactionFeeConfiguration': {
                'licenseeCharges': {'chargeAmount': 10.00, 'chargeType': 'FLAT_FEE_PER_PRIVILEGE', 'active': True}
            },
        }

        # PUT the compact configuration
        put_response = requests.put(
            url=f'{get_api_base_url()}/v1/compacts/{compact}', headers=headers, json=compact_config, timeout=10
        )

        if put_response.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to PUT compact configuration for compact {compact}. Response: {put_response.json()}'
            )

        print(f'Successfully PUT compact configuration for {compact}')

        # GET the compact configuration
        get_response = requests.get(url=f'{get_api_base_url()}/v1/compacts/{compact}', headers=headers, timeout=10)

        if get_response.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to GET compact configuration for compact {compact}. Response: {get_response.json()}'
            )

        # Verify that the configuration matches what we set
        config_response = get_response.json()

        # the only fields not present in the original put are the compactAbbr and compactName
        # which are set by the path parameters in the request and returned by the API
        compact_config['compactAbbr'] = config_response['compactAbbr']
        compact_config['compactName'] = config_response['compactName']

        # Compare the entire configuration at once
        # Check if there are any differences between expected and actual configuration
        differences = []
        for key, expected_value in compact_config.items():
            if key not in config_response:
                differences.append(f'Missing key in response: {key}')
            elif config_response[key] != expected_value:
                differences.append(f'Value mismatch for {key}: Expected {expected_value}, Got {config_response[key]}')

        # Check for extra keys in the response
        for key in config_response:
            if key not in compact_config:
                differences.append(f'Extra key in response: {key}')

        if differences:
            raise SmokeTestFailureException('Configuration mismatch:\n' + '\n'.join(differences))

        print(f'Successfully verified compact configuration for {compact}')

        # return the config response to be used in other tests
        return config_response

    finally:
        # Clean up the test user
        delete_test_staff_user(test_email, user_sub, compact)


def test_jurisdiction_configuration():
    """
    Test that a state admin can update and retrieve jurisdiction configuration.
    """
    print('Testing jurisdiction configuration...')

    # Create a test state admin user
    compact = COMPACTS[0]  # Use the first compact for testing
    jurisdiction = 'ky'  # Use Kentucky for testing
    test_email = f'test-state-admin-{jurisdiction}@ccSmokeTestFakeEmail.com'
    permissions = {'actions': {}, 'jurisdictions': {'ky': {'admin'}}}

    try:
        # Create the test user
        user_sub = create_test_staff_user(
            email=test_email,
            compact=compact,
            jurisdiction=jurisdiction,
            permissions=permissions,
        )

        # Get auth headers for the test user
        headers = get_staff_user_auth_headers(test_email)

        # Get license types for the compact
        with open('cdk.json') as context_file:
            cdk_context = json.load(context_file)['context']
            license_types = cdk_context.get('license_types', {}).get(compact, [])

        if not license_types:
            raise SmokeTestFailureException(f'No license types found for compact {compact}')

        # Create privilege fees for all license types with military rates
        privilege_fees = []
        for lt in license_types:
            privilege_fees.append(
                {'licenseTypeAbbreviation': lt['abbreviation'], 'amount': 75.00, 'militaryRate': 50.00}
            )

        # Create test jurisdiction configuration data
        jurisdiction_config = {
            'jurisdictionOperationsTeamEmails': ['state-ops-test@ccSmokeTestFakeEmail.com'],
            'jurisdictionAdverseActionsNotificationEmails': ['state-adverse-test@ccSmokeTestFakeEmail.com'],
            'jurisdictionSummaryReportNotificationEmails': ['state-summary-test@ccSmokeTestFakeEmail.com'],
            'licenseeRegistrationEnabled': True,
            'jurisprudenceRequirements': {
                'required': True,
                'linkToDocumentation': 'https://example.com/jurisprudence-docs',
            },
            'privilegeFees': privilege_fees,
        }

        # PUT the jurisdiction configuration
        put_response = requests.put(
            url=f'{get_api_base_url()}/v1/compacts/{compact}/jurisdictions/{jurisdiction}',
            headers=headers,
            json=jurisdiction_config,
            timeout=10,
        )

        if put_response.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to PUT jurisdiction configuration for {jurisdiction} in {compact}. '
                f'Response: {put_response.json()}'
            )

        print(f'Successfully PUT jurisdiction configuration for {jurisdiction} in {compact}')

        # GET the jurisdiction configuration
        get_response = requests.get(
            url=f'{get_api_base_url()}/v1/compacts/{compact}/jurisdictions/{jurisdiction}', headers=headers, timeout=10
        )

        if get_response.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to GET jurisdiction configuration for {jurisdiction} in {compact}. '
                f'Response: {get_response.json()}'
            )

        # Verify that the configuration matches what we set
        config_response = get_response.json()

        # Add the fields that are returned by the API but not set in our request
        jurisdiction_config['jurisdictionName'] = config_response['jurisdictionName']
        jurisdiction_config['compact'] = config_response['compact']
        jurisdiction_config['postalAbbreviation'] = config_response['postalAbbreviation']

        # Compare the entire configuration objects
        if jurisdiction_config != config_response:
            # Find differences for better error reporting
            differences = []
            for key in set(jurisdiction_config.keys()) | set(config_response.keys()):
                if key not in jurisdiction_config:
                    differences.append(f"Key '{key}' missing in request but present in response")
                elif key not in config_response:
                    differences.append(f"Key '{key}' present in request but missing in response")
                elif jurisdiction_config[key] != config_response[key]:
                    differences.append(
                        f"Value mismatch for '{key}': Expected: {jurisdiction_config[key]}, Got: {config_response[key]}"
                    )

            raise SmokeTestFailureException(
                f'Jurisdiction configuration mismatch for {jurisdiction} in {compact}. '
                f'Differences: {", ".join(differences)}'
            )

        print(f'Successfully verified jurisdiction configuration for {jurisdiction} in {compact}')
        # return the config response to be used in other tests
        return config_response
    finally:
        # Clean up the test user
        delete_test_staff_user(test_email, user_sub, compact)


if __name__ == '__main__':
    load_smoke_test_env()
    test_active_member_jurisdictions()
    test_compact_configuration()
    test_jurisdiction_configuration()
