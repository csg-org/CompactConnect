# ruff: noqa: S101 T201  we use asserts and print statements for smoke testing
#!/usr/bin/env python3

import requests
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
    get_provider_user_auth_headers_cached,
    get_user_tokens,
    load_smoke_test_env,
)

# This script tests the practitioner email update functionality against a sandbox environment.
# IMPORTANT: This smoke tests requires manual input from the developer since it sends email verification codes
# via email.

# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.


def test_practitioner_email_update():
    """
    Test the complete email update flow for a practitioner user.
    This test requires manual input from the developer for email verification codes.
    """
    logger.info('Starting practitioner email update smoke test')

    # Step 1: Get current provider data to know the original email
    original_provider_data = call_provider_users_me_endpoint()
    original_email = original_provider_data.get('compactConnectRegisteredEmailAddress')
    provider_id = original_provider_data.get('providerId')
    compact = original_provider_data.get('compact')

    if not original_email:
        raise SmokeTestFailureException('No registered email address found in provider data')

    logger.info(f'Current provider email: {original_email}')
    logger.info(f'Provider ID: {provider_id}, Compact: {compact}')

    # Step 2: Ask developer for new email address
    print('\nPRACTITIONER EMAIL UPDATE SMOKE TEST')
    print('=' * 60)
    new_email = input(f'Enter a valid email address to update the practitioner to (current: {original_email}): ')

    if not new_email or new_email == original_email:
        raise SmokeTestFailureException('New email address must be provided and different from current email')

    # Step 3: Call PATCH /v1/provider-users/me/email endpoint
    logger.info(f'Attempting to update email from {original_email} to {new_email}')

    headers = get_provider_user_auth_headers_cached()
    patch_response = requests.patch(
        url=f'{config.api_base_url}/v1/provider-users/me/email',
        headers=headers,
        json={'newEmailAddress': new_email},
        timeout=10,
    )

    if patch_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to initiate email update. Response: {patch_response.json()}')

    patch_response_body = patch_response.json()
    expected_message = 'Verification code sent to new email address'
    if patch_response_body.get('message') != expected_message:
        raise SmokeTestFailureException(
            f'Unexpected response message. Expected: "{expected_message}", Got: "{patch_response_body.get("message")}"'
        )

    logger.info('Email update initiated successfully')

    # Step 4: Ask developer for verification code from email
    print(f'\nA verification code has been sent to {new_email}')
    verification_code = input('Enter the 4-digit verification code from the email: ').strip()

    if not verification_code or len(verification_code) != 4 or not verification_code.isdigit():
        raise SmokeTestFailureException('Verification code must be exactly 4 digits')

    # Step 5: Call POST /v1/provider-users/me/email/verify endpoint
    logger.info('Attempting to verify email update with provided code')

    verify_response = requests.post(
        url=f'{config.api_base_url}/v1/provider-users/me/email/verify',
        headers=headers,
        json={'verificationCode': verification_code},
        timeout=10,
    )

    if verify_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to verify email update. Response: {verify_response.json()}')

    verify_response_body = verify_response.json()
    expected_message = 'Email address updated successfully'
    if verify_response_body.get('message') != expected_message:
        raise SmokeTestFailureException(
            f'Unexpected response message. Expected: "{expected_message}", Got: "{verify_response_body.get("message")}"'
        )

    logger.info('Email verification completed successfully')

    # Step 6: Test authentication with new email address
    logger.info('Testing authentication with new email address')

    try:
        # Get new tokens using the new email address and existing password
        new_tokens = get_user_tokens(new_email, config.test_provider_user_password, is_staff=False)
        new_headers = {
            'Authorization': 'Bearer ' + new_tokens['IdToken'],
        }

        # Test the new authentication by calling the provider endpoint
        test_response = requests.get(url=f'{config.api_base_url}/v1/provider-users/me', headers=new_headers, timeout=10)

        if test_response.status_code != 200:
            raise SmokeTestFailureException(f'Failed to authenticate with new email. Response: {test_response.json()}')

        # Verify the email was updated in the provider data
        updated_provider_data = test_response.json()
        if updated_provider_data.get('compactConnectRegisteredEmailAddress') != new_email:
            raise SmokeTestFailureException(
                f'Provider data shows incorrect email. Expected: {new_email}, '
                f'Got: {updated_provider_data.get("compactConnectRegisteredEmailAddress")}'
            )

        logger.info('Authentication with new email successful')

    except Exception as e:  # noqa: BLE001
        logger.error(f'Failed to authenticate with new email: {str(e)}')
        raise SmokeTestFailureException(f'Authentication with new email failed: {str(e)}') from e

    # Step 7: Restore original email address (reverse the process)
    logger.info(f'Restoring original email address: {original_email}')

    # Use the new authentication headers for the restore process
    restore_patch_response = requests.patch(
        url=f'{config.api_base_url}/v1/provider-users/me/email',
        headers=new_headers,
        json={'newEmailAddress': original_email},
        timeout=10,
    )

    if restore_patch_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to initiate email restore. Response: {restore_patch_response.json()}')

    logger.info('Email restore initiated successfully')

    # Step 8: Ask developer for verification code sent to original email
    print(f'\nA verification code has been sent to {original_email} to restore the original email address')
    restore_verification_code = input('Enter the 4-digit verification code from the email: ').strip()

    if not restore_verification_code or len(restore_verification_code) != 4 or not restore_verification_code.isdigit():
        raise SmokeTestFailureException('Restore verification code must be exactly 4 digits')

    # Step 9: Complete the restore process
    logger.info('Attempting to verify email restore with provided code')

    restore_verify_response = requests.post(
        url=f'{config.api_base_url}/v1/provider-users/me/email/verify',
        headers=new_headers,
        json={'verificationCode': restore_verification_code},
        timeout=10,
    )

    if restore_verify_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to verify email restore. Response: {restore_verify_response.json()}')

    logger.info('Email restore completed successfully')

    # Step 10: Verify the original email is restored
    logger.info('Verifying original email has been restored')

    try:
        # Test authentication with original email
        final_provider_data = call_provider_users_me_endpoint()

        if final_provider_data.get('compactConnectRegisteredEmailAddress') != original_email:
            raise SmokeTestFailureException(
                f'Provider data shows incorrect restored email. Expected: {original_email}, '
                f'Got: {final_provider_data.get("compactConnectRegisteredEmailAddress")}'
            )

        logger.info('Original email restored and verified successfully')

    except Exception as e:  # noqa: BLE001
        logger.error(f'Failed to authenticate with restored email: {str(e)}')
        raise SmokeTestFailureException(f'Authentication with restored email failed: {str(e)}') from e

    print('\n' + '=' * 60)
    print('✅ PRACTITIONER EMAIL UPDATE SMOKE TEST PASSED')
    print('=' * 60)
    logger.info('Practitioner email update smoke test completed successfully')


def test_email_update_error_scenarios():
    """
    Test error scenarios for email update functionality.
    """
    logger.info('Testing email update error scenarios')

    headers = get_provider_user_auth_headers_cached()

    # Test 1: Invalid email format
    logger.info('Testing invalid email format')
    invalid_email_response = requests.patch(
        url=f'{config.api_base_url}/v1/provider-users/me/email',
        headers=headers,
        json={'newEmailAddress': 'invalid-email-format'},
        timeout=10,
    )

    if invalid_email_response.status_code != 400:
        raise SmokeTestFailureException(f'Expected 400 for invalid email, got {invalid_email_response.status_code}')

    logger.info('Invalid email format test passed')

    # Test 2: Invalid verification code format
    logger.info('Testing invalid verification code format')
    invalid_code_response = requests.post(
        url=f'{config.api_base_url}/v1/provider-users/me/email/verify',
        headers=headers,
        json={'verificationCode': '123'},  # Too short
        timeout=10,
    )

    if invalid_code_response.status_code != 400:
        raise SmokeTestFailureException(
            f'Expected 400 for invalid verification code, got {invalid_code_response.status_code}'
        )

    logger.info('Invalid verification code format test passed')

    # Test 3: No pending verification
    logger.info('Testing verification without pending email update')
    no_pending_response = requests.post(
        url=f'{config.api_base_url}/v1/provider-users/me/email/verify',
        headers=headers,
        json={'verificationCode': '1234'},
        timeout=10,
    )

    if no_pending_response.status_code != 400:
        raise SmokeTestFailureException(
            f'Expected 400 for no pending verification, got {no_pending_response.status_code}'
        )

    expected_message = 'No email verification in progress. Please submit a new email address first.'
    response_body = no_pending_response.json()
    if response_body.get('message') != expected_message:
        raise SmokeTestFailureException(
            f'Unexpected error message. Expected: "{expected_message}", Got: "{response_body.get("message")}"'
        )

    logger.info('No pending verification test passed')
    logger.info('Email update error scenarios testing completed successfully')


if __name__ == '__main__':
    # Load environment variables from smoke_tests_env.json
    load_smoke_test_env()

    # Run tests
    test_email_update_error_scenarios()
    test_practitioner_email_update()
