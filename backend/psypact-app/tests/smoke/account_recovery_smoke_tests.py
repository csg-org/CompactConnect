# ruff: noqa: S101 T201  we use asserts and print statements for smoke testing
#!/usr/bin/env python3
import urllib.parse

import requests
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
    load_smoke_test_env,
)

# This script tests the practitioner account recovery functionality against a sandbox environment.
# IMPORTANT: This smoke test requires manual input from the developer since it sends recovery emails
# and requires the developer to extract the recovery link from the email. It is intended to run in environments
# where MFA is not required for provider accounts.

# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.


def test_account_recovery_flow():
    """
    Test the complete account recovery flow for a practitioner user.
    This test requires manual input from the developer for recovery link extraction.
    """
    logger.info('Starting practitioner account recovery smoke test')

    # Step 1: Get current provider data to know the provider details
    provider_data = call_provider_users_me_endpoint()
    provider_email = provider_data.get('compactConnectRegisteredEmailAddress')
    provider_id = provider_data.get('providerId')
    compact = provider_data.get('compact')

    # Extract license data from the provider response
    licenses = provider_data.get('licenses', [])
    if not licenses:
        raise SmokeTestFailureException('No license data found in provider record')

    # Use the first license for recovery data
    license_record = licenses[0]
    given_name = license_record['givenName']
    family_name = license_record['familyName']
    date_of_birth = license_record['dateOfBirth']
    license_type = license_record['licenseType']
    jurisdiction = license_record['jurisdiction']
    partial_ssn = license_record['ssnLastFour']

    logger.info(f'Provider email: {provider_email}')
    logger.info(f'Provider ID: {provider_id}')
    logger.info(f'Compact: {compact}')
    logger.info(
        f'License: {given_name} {family_name}, DOB: {date_of_birth}, Type: {license_type}, Jurisdiction: {jurisdiction}'
    )

    print('\nPRACTITIONER ACCOUNT RECOVERY SMOKE TEST')
    print('=' * 60)
    print(f'Testing account recovery for provider: {provider_email}')

    # Step 2: Call POST /v1/provider-users/initiateRecovery endpoint
    logger.info('Initiating account recovery request')
    current_password = config.test_provider_user_password

    initiate_request_body = {
        'username': provider_email,
        'password': current_password,
        'compact': compact,
        'jurisdiction': jurisdiction,
        'givenName': given_name,
        'familyName': family_name,
        'dob': date_of_birth,
        'partialSocial': partial_ssn,
        'licenseType': license_type,
        'recaptchaToken': 'test-recaptcha-token',  # Hardcoded for sandbox environments
    }

    initiate_response = requests.post(
        url=f'{config.api_base_url}/v1/provider-users/initiateRecovery',
        json=initiate_request_body,
        timeout=30,
    )

    if initiate_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to initiate account recovery. Response: {initiate_response.json()}')

    initiate_response_body = initiate_response.json()
    expected_message = 'request processed'
    if initiate_response_body.get('message') != expected_message:
        raise SmokeTestFailureException(
            f'Unexpected response message. Expected: "{expected_message}", '
            f'Got: "{initiate_response_body.get("message")}"'
        )

    logger.info('Account recovery initiated successfully')

    # Step 3: Ask developer for the recovery link from the email
    print(f'\nA recovery email has been sent to {provider_email}')
    print('The email should contain a recovery link.')
    recovery_link = input('\nPaste the complete recovery link from the email: ').strip()

    if not recovery_link:
        raise SmokeTestFailureException('Recovery link is required')

    # Step 4: Parse the recovery link to extract query parameters
    logger.info('Parsing recovery link to extract parameters')

    try:
        parsed_url = urllib.parse.urlparse(recovery_link)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Extract required parameters
        link_compact = query_params.get('compact', [None])[0]
        link_provider_id = query_params.get('providerId', [None])[0]
        recovery_token = query_params.get('recoveryId', [None])[0]

        if not all([link_compact, link_provider_id, recovery_token]):
            raise SmokeTestFailureException(
                f'Missing required parameters in recovery link. '
                f'Parsed: compact={link_compact}, providerId={link_provider_id}, recoveryId={recovery_token}'
            )

        # Validate that the link parameters match our provider
        if link_compact != compact:
            raise SmokeTestFailureException(f'Compact mismatch. Expected: {compact}, Got: {link_compact}')

        if link_provider_id != provider_id:
            raise SmokeTestFailureException(f'Provider ID mismatch. Expected: {provider_id}, Got: {link_provider_id}')

        logger.info(f'Successfully parsed recovery link - Token: {recovery_token}')

    except Exception as e:
        raise SmokeTestFailureException(f'Failed to parse recovery link: {str(e)}') from e

    # Step 5: Call POST /v1/provider-users/verifyRecovery endpoint with valid token
    logger.info('Verifying account recovery with valid token')

    verify_request_body = {
        'compact': compact,
        'providerId': provider_id,
        'recoveryToken': recovery_token,
        'recaptchaToken': 'test-recaptcha-token',
    }

    verify_response = requests.post(
        url=f'{config.api_base_url}/v1/provider-users/verifyRecovery',
        json=verify_request_body,
        timeout=30,
    )

    if verify_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to verify account recovery. Response: {verify_response.json()}')

    verify_response_body = verify_response.json()
    expected_message = 'request processed'
    if verify_response_body.get('message') != expected_message:
        raise SmokeTestFailureException(
            f'Unexpected response message. Expected: "{expected_message}", Got: "{verify_response_body.get("message")}"'
        )

    logger.info('Account recovery verification completed successfully')

    # Step 6: Verify that the recovery token cannot be reused
    logger.info('Testing that recovery token cannot be reused')

    reuse_response = requests.post(
        url=f'{config.api_base_url}/v1/provider-users/verifyRecovery',
        json=verify_request_body,
        timeout=30,
    )

    # This should fail since the token should be invalidated
    if reuse_response.status_code != 400:
        raise SmokeTestFailureException(
            f'Expected 400 for reused recovery token, got {reuse_response.status_code}. {reuse_response.json()}'
        )

    logger.info('Recovery token reuse prevention test passed')

    # Step 7: Test rate limiting
    logger.info('Testing invalid recovery token to trigger rate limiting')

    invalid_verify_request_body = {
        'compact': compact,
        'providerId': provider_id,
        'recoveryToken': 'invalid-token-12345',
        'recaptchaToken': 'test-recaptcha-token',
    }

    invalid_verify_response = requests.post(
        url=f'{config.api_base_url}/v1/provider-users/verifyRecovery',
        json=invalid_verify_request_body,
        timeout=30,
    )

    # This should fail with 429
    if invalid_verify_response.status_code != 429:
        raise SmokeTestFailureException(
            f'Expected 400 for invalid recovery token, got {invalid_verify_response.status_code}. '
            f'{invalid_verify_response.json()}'
        )

    logger.info('Invalid recovery token test passed')

    print('\n' + '=' * 60)
    print('✅ PRACTITIONER ACCOUNT RECOVERY SMOKE TEST PASSED')
    print('=' * 60)
    print('The Cognito user account has been recreated.')
    print('The practitioner should receive a temporary password email to complete the recovery.')
    print('=' * 60)
    logger.info('Practitioner account recovery smoke test completed successfully')


def test_account_recovery_wrong_password():
    """
    Test error scenarios for account recovery functionality.
    """
    logger.info('Testing account recovery error scenarios')

    # Get provider data for constructing test requests
    provider_data = call_provider_users_me_endpoint()
    provider_email = provider_data['compactConnectRegisteredEmailAddress']
    compact = provider_data['compact']
    licenses = provider_data.get('licenses', [])

    if not licenses:
        raise SmokeTestFailureException('No license data found for error scenario testing')

    # Use the first license for recovery data
    license_record = licenses[0]
    given_name = license_record['givenName']
    family_name = license_record['familyName']
    date_of_birth = license_record['dateOfBirth']
    license_type = license_record['licenseType']
    jurisdiction = license_record['jurisdiction']
    partial_ssn = license_record['ssnLastFour']

    # Test 1: Invalid password in initiate request
    logger.info('Testing initiate recovery with invalid password')

    invalid_password_request = {
        'username': provider_email,
        'password': 'wrongPassword!000',
        'compact': compact,
        'jurisdiction': jurisdiction,
        'givenName': given_name,
        'familyName': family_name,
        'dob': date_of_birth,
        'partialSocial': partial_ssn,
        'licenseType': license_type,
        'recaptchaToken': 'test-recaptcha-token',  # Hardcoded for sandbox environments
    }

    invalid_password_response = requests.post(
        url=f'{config.api_base_url}/v1/provider-users/initiateRecovery',
        json=invalid_password_request,
        timeout=30,
    )

    # Should still return 200 (generic response to prevent enumeration)
    if invalid_password_response.status_code != 200:
        raise SmokeTestFailureException(
            f'Expected 200 for invalid password (generic response), got {invalid_password_response.status_code}'
            f'response body: {invalid_password_response.json()}'
        )

    logger.info('Invalid password test passed (generic 200 response)')

    logger.info('Developer must verify no confirmation email was sent')


if __name__ == '__main__':
    # Load environment variables from smoke_tests_env.json
    load_smoke_test_env()

    # Run tests
    test_account_recovery_wrong_password()
    test_account_recovery_flow()
