# ruff: noqa: T201 we use print statements for smoke testing
#!/usr/bin/env python3
import json

import requests
from botocore.exceptions import ClientError
from config import config
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


def cleanup_compact_configuration(compact: str):
    """
    Clean up compact configuration record for testing using direct DynamoDB calls.

    :param compact: The compact abbreviation
    """
    try:
        # Delete the compact configuration record directly from DynamoDB
        pk = f'{compact}#CONFIGURATION'
        sk = f'{compact}#CONFIGURATION'

        config.compact_configuration_dynamodb_table.delete_item(Key={'pk': pk, 'sk': sk})
        print(f'Cleaned up compact configuration for {compact}')

    except ClientError as e:
        print(f'Warning: Error cleaning up compact configuration for {compact}: {e}')


def cleanup_jurisdiction_configuration(compact: str, jurisdiction: str):
    """
    Clean up jurisdiction configuration record for testing using direct DynamoDB calls.

    :param compact: The compact abbreviation
    :param jurisdiction: The jurisdiction postal abbreviation
    """
    try:
        # Delete the jurisdiction configuration record directly from DynamoDB
        pk = f'{compact}#CONFIGURATION'
        sk = f'{compact}#JURISDICTION#{jurisdiction.lower()}'

        config.compact_configuration_dynamodb_table.delete_item(Key={'pk': pk, 'sk': sk})
        print(f'Cleaned up jurisdiction configuration for {jurisdiction} in {compact}')

    except ClientError as e:
        print(f'Warning: Error cleaning up jurisdiction configuration for {jurisdiction} in {compact}: {e}')


def test_active_member_jurisdictions():
    """
    Test that the active member jurisdictions from cdk.json match the jurisdictions returned by the API.

    :raises SmokeTestFailureException: If the test fails
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

    :return: The compact configuration response for use in other tests
    :raises SmokeTestFailureException: If the test fails
    """
    print('Testing compact configuration...')

    # Create a test compact admin user
    compact = COMPACTS[0]  # Use the first compact for testing
    test_email = f'test-compact-admin-{compact}@ccSmokeTestFakeEmail.com'
    permissions = {'actions': {'admin'}, 'jurisdictions': {}}

    user_sub = None
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

        # Clean up any existing compact configuration from previous test runs
        cleanup_compact_configuration(compact)

        # Create test compact configuration data
        compact_config = {
            'compactCommissionFee': {'feeAmount': 15.00, 'feeType': 'FLAT_RATE'},
            'licenseeRegistrationEnabled': True,
            'compactOperationsTeamEmails': ['ops-test@ccSmokeTestFakeEmail.com'],
            'compactAdverseActionsNotificationEmails': ['adverse-test@ccSmokeTestFakeEmail.com'],
            'compactSummaryReportNotificationEmails': ['summary-test@ccSmokeTestFakeEmail.com'],
            'configuredStates': [],
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
        if user_sub:
            delete_test_staff_user(test_email, user_sub, compact)


def test_jurisdiction_configuration():
    """
    Test that a state admin can update and retrieve jurisdiction configuration.

    :return: The jurisdiction configuration response for use in other tests
    :raises SmokeTestFailureException: If the test fails
    """
    print('Testing jurisdiction configuration...')

    # Create a test state admin user with compact admin permissions for simplicity
    compact = COMPACTS[0]  # Use the first compact for testing
    jurisdiction = 'ne'  # Use Nebraska for testing
    test_email = f'test-state-admin-{jurisdiction}@ccSmokeTestFakeEmail.com'
    permissions = {'actions': {'admin'}, 'jurisdictions': {'ne': {'admin'}}}

    user_sub = None
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

        # Clean up any existing configurations from previous test runs
        cleanup_jurisdiction_configuration(compact, jurisdiction)

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

        # Verify that the jurisdiction was automatically added to the compact's configuredStates
        # since we set licenseeRegistrationEnabled: True
        print(f'Verifying that {jurisdiction} was added to compact configuredStates...')

        # Use the same user (which also has compact admin permissions) to check the compact configuration
        compact_get_response = requests.get(
            url=f'{get_api_base_url()}/v1/compacts/{compact}', headers=headers, timeout=10
        )

        if compact_get_response.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to GET compact configuration for verification. Response: {compact_get_response.json()}'
            )

        compact_config_data = compact_get_response.json()
        configured_states = compact_config_data.get('configuredStates', [])

        # Check if our jurisdiction was added with isLive: False
        jurisdiction_found = False
        for state in configured_states:
            if state.get('postalAbbreviation') == jurisdiction.lower():
                jurisdiction_found = True
                if state.get('isLive') is not False:
                    raise SmokeTestFailureException(
                        f'Expected jurisdiction {jurisdiction} to have isLive: false in configuredStates, '
                        f'but got isLive: {state.get("isLive")}'
                    )
                break

        if not jurisdiction_found:
            raise SmokeTestFailureException(
                f'Expected jurisdiction {jurisdiction} to be automatically added to configuredStates '
                f'when licenseeRegistrationEnabled was set to true, but it was not found. '
                f'configuredStates: {configured_states}'
            )

        print(f'Successfully verified that {jurisdiction} was added to configuredStates with isLive: false')

        # Now set the jurisdiction to live for use by other smoke tests
        print(f'Setting {jurisdiction} to live in configuredStates...')

        # Update the configuredStates to set our jurisdiction to live
        updated_configured_states = []
        for state in configured_states:
            if state.get('postalAbbreviation') == jurisdiction.lower():
                # Set this jurisdiction to live
                updated_state = state.copy()
                updated_state['isLive'] = True
                updated_configured_states.append(updated_state)
            else:
                updated_configured_states.append(state)

        # Prepare the compact configuration update with the jurisdiction set to live
        compact_config_data['configuredStates'] = updated_configured_states

        # remove fields not expected by PUT endpoint
        del compact_config_data['compactName']
        del compact_config_data['compactAbbr']

        # PUT the updated compact configuration
        compact_put_response = requests.put(
            url=f'{get_api_base_url()}/v1/compacts/{compact}',
            headers=headers,
            json=compact_config_data,
            timeout=10,
        )

        if compact_put_response.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to PUT compact configuration to set {jurisdiction} to live. '
                f'Response: {compact_put_response.json()}'
            )

        print(f'Successfully updated compact configuration to set {jurisdiction} to live')

        # return the config response to be used in other tests
        return config_response
    finally:
        # Clean up the test user
        if user_sub:
            delete_test_staff_user(test_email, user_sub, compact)


def test_upload_payment_processor_credentials():
    """
    Test that a compact admin can upload payment processor credentials.

    :raises SmokeTestFailureException: If the test fails
    """
    print('Testing upload payment processor credentials...')

    # Create a test compact admin user
    compact = COMPACTS[0]  # Use the first compact for testing
    test_email = f'test-compact-admin-credentials-{compact}@ccSmokeTestFakeEmail.com'
    permissions = {'actions': {'admin'}, 'jurisdictions': {}}

    user_sub = None
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

        # Create test payment processor credentials
        credentials = {
            'processor': 'authorize.net',
            'apiLoginId': config.sandbox_authorize_net_api_login_id,
            'transactionKey': config.sandbox_authorize_net_transaction_key,
        }

        # POST the payment processor credentials
        response = requests.post(
            url=f'{get_api_base_url()}/v1/compacts/{compact}/credentials/payment-processor',
            headers=headers,
            json=credentials,
            timeout=30,  # Give this more time as it makes external API calls to authorize.net
        )

        if response.status_code != 200:
            raise SmokeTestFailureException(
                f'Failed to POST payment processor credentials for compact {compact}. '
                f'Status: {response.status_code}, Response: {response.text}'
            )

        # Verify the response contains a success message
        response_data = response.json()
        if 'message' not in response_data or 'Successfully verified credentials' not in response_data['message']:
            raise SmokeTestFailureException(
                f'Unexpected response when uploading payment processor credentials: {response_data}'
            )

        print(f'Successfully uploaded and verified payment processor credentials for {compact}')

    finally:
        # Clean up the test user
        if user_sub:
            delete_test_staff_user(test_email, user_sub, compact)


if __name__ == '__main__':
    load_smoke_test_env()
    test_active_member_jurisdictions()
    test_compact_configuration()
    test_jurisdiction_configuration()
    test_upload_payment_processor_credentials()
