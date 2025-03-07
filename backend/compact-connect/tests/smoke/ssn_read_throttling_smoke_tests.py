# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
import time
import uuid

import requests
from config import logger
from smoke_common import (
    SmokeTestFailureException,
    create_test_staff_user,
    delete_test_staff_user,
    get_api_base_url,
    get_lambda_client,
    get_provider_ssn_lambda_name,
    get_rate_limiting_dynamodb_table,
    get_staff_user_auth_headers,
    load_smoke_test_env,
)

COMPACT = 'aslp'
JURISDICTION = 'ne'
TEST_PROVIDER_GIVEN_NAME = 'Joe'
TEST_PROVIDER_FAMILY_NAME = 'Dokes'

# This script can be run locally against a sandbox environment to test the throttling functionality of the
# GET provider SSN endpoint of the Compact Connect API.
# Your sandbox account must be deployed with the "security_profile": "VULNERABLE" setting in your cdk.context.json
# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.

# By design, this sensitive endpoint should throttle users that make more than 5 requests within a 24 period, and the
# endpoint should deactivate itself after 15 requests within 24 hours. This is to limit risk of compromised admin
# credentials resulting in large numbers of SSNs being leaked.
# This test spins up three test staff users and calls the endpoint 6 times each for each user.


def _cleanup_test_generated_records():
    """
    Cleanup all test records from the rate limiting table, so that this test can be run again if needed
    """
    # Now clean up the records we added
    # First, get all provider records to delete
    rate_limiting_dynamo_table = get_rate_limiting_dynamodb_table()
    read_ssn_requests_query_response = rate_limiting_dynamo_table.query(
        KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': 'READ_SSN_REQUESTS'}
    )

    items = read_ssn_requests_query_response.get('Items', [])

    logger.info('Read SSN request count', request_count=len(items))

    # Delete all read records
    for record in items:
        rate_limiting_dynamo_table.delete_item(Key={'pk': record['pk'], 'sk': record['sk']})
    logger.info('Successfully deleted read ssn request records from rate limiting table')


def _make_ssn_request(email, provider_id):
    """
    Makes a request to the SSN endpoint and returns the response
    """
    headers = get_staff_user_auth_headers(email)
    return requests.get(
        url=get_api_base_url() + f'/v1/compacts/{COMPACT}/providers/{provider_id}/ssn',
        headers=headers,
        timeout=10,
    )


def _staff_user_is_enabled(email):
    """
    Checks if a user is enabled or disabled in Cognito
    Returns True if enabled, False if disabled
    """
    from config import config

    user_data = config.cognito_client.admin_get_user(UserPoolId=config.cognito_staff_user_pool_id, Username=email)
    return user_data.get('Enabled', True)


def trigger_get_provider_ssn_endpoint_throttling():
    """
    Verifies that the GET provider SSN endpoint will throttle and deactivate users that call the
    endpoint too frequently.

    Step 1: Create three test staff users with the aslp/readSSN scope.
    Step 2: Have each user call the endpoint until throttled (6 requests each). The first two should be disabled
    (asserted with the AdminGetUser api), and the last one should cause the lambda to throttle itself with a set
    reserved concurrency limit of 0 (asserted using the boto3 lambda client
    Step 3: Ensure that all test staff users are cleaned up and all request record in the rate limiting table
    are cleared.
    """
    # Generate a random provider ID - we don't need a real one since we'll get 404s or 429s
    # but the endpoint will still record the access attempt
    test_provider_id = str(uuid.uuid4())

    # Create three test staff users
    test_emails = [
        f'test-staff-user-1-{uuid.uuid4()}@example.com',
        f'test-staff-user-2-{uuid.uuid4()}@example.com',
        f'test-staff-user-3-{uuid.uuid4()}@example.com',
    ]

    test_user_subs = []

    # Create staff users with permission to read SSNs
    for email in test_emails:
        user_sub = create_test_staff_user(
            email=email,
            compact=COMPACT,
            jurisdiction=JURISDICTION,
            permissions={'actions': {'readSSN'}},
        )
        test_user_subs.append(user_sub)
        logger.info(f'Created test staff user: {email}')

    try:
        # Test the first two users - each should be able to make 5 requests successfully,
        # get throttled on the 6th, and disabled on the 7th
        for i, email in enumerate(test_emails[:2]):
            logger.info(f'Testing user {i + 1}: {email}')

            # Make 5 successful requests
            for j in range(5):
                response = _make_ssn_request(email, test_provider_id)
                # We expect a 404 since the provider ID doesn't exist, but that's fine
                # The important thing is that it's not a 429
                if response.status_code == 429:
                    raise SmokeTestFailureException(
                        f'User {email} was throttled on request {j + 1}, expected to succeed'
                    )
                logger.info(f'Request {j + 1} successful with status code {response.status_code}')
                # Small delay to ensure requests are recorded properly
                time.sleep(0.5)

            # 6th request should be throttled but user should still be enabled
            response = _make_ssn_request(email, test_provider_id)
            if response.status_code != 429:
                raise SmokeTestFailureException(
                    f'Expected 429 on 6th request for user {email}, got {response.status_code}'
                )
            logger.info('Request 6 correctly throttled with 429 status code')

            # Check that user is still enabled
            if not _staff_user_is_enabled(email):
                raise SmokeTestFailureException(
                    f'User {email} was disabled after 6th request, expected to still be enabled'
                )
            logger.info(f'User {email} still enabled after 6th request as expected')

            # 7th request should be throttled and user should be disabled
            response = _make_ssn_request(email, test_provider_id)
            if response.status_code != 429:
                raise SmokeTestFailureException(
                    f'Expected 429 on 7th request for user {email}, got {response.status_code}'
                )
            logger.info('Request 7 correctly throttled with 429 status code')

            # Check that user is now disabled
            if _staff_user_is_enabled(email):
                raise SmokeTestFailureException(f'User {email} was not disabled after 7th request as expected')
            logger.info(f'User {email} correctly disabled after 7th request')

        # Test the third user - this should trigger the global throttling after 16 total requests
        # (14 from first two users, plus 6 from this user)
        logger.info(f'Testing user 3: {test_emails[2]}')

        # First request should succeed
        response = _make_ssn_request(test_emails[2], test_provider_id)
        if response.status_code == 429:
            raise SmokeTestFailureException(
                f'User {test_emails[2]} was throttled on first request, expected to succeed'
            )
        logger.info(f'First request for user 3 successful with status code {response.status_code}')

        # Second request should trigger global throttling (16th request overall)
        response = _make_ssn_request(test_emails[2], test_provider_id)
        if response.status_code != 429:
            raise SmokeTestFailureException(
                f'Expected 429 on 2nd request for user {test_emails[2]}, got {response.status_code}'
            )
        logger.info('Second request correctly throttled with 429 status code')

        # Verify that lambda's reserved concurrency is set to 0
        # Give the lambda a moment to update its concurrency
        time.sleep(2)

        lambda_concurrency_resp = get_lambda_client().get_function_concurrency(
            FunctionName=get_provider_ssn_lambda_name()
        )

        reserved_concurrency = lambda_concurrency_resp.get('ReservedConcurrentExecutions')

        if reserved_concurrency != 0:
            raise SmokeTestFailureException(f'Lambda reserved concurrency not set to zero. {reserved_concurrency}')

        logger.info('Lambda reserved concurrency correctly set to 0')
        # Reset lambda concurrency
        get_lambda_client().delete_function_concurrency(FunctionName=get_provider_ssn_lambda_name())
        logger.info('Reset lambda concurrency')

    except Exception as e:
        logger.error('Smoke test failure', failure=str(e))
        raise
    finally:
        # Step 3: delete test staff users and cleanup items from the rate limiting table
        logger.info('Cleaning up resources...')

        # Delete test staff users
        for i, email in enumerate(test_emails):
            try:
                delete_test_staff_user(email, test_user_subs[i], COMPACT)
                logger.info(f'Deleted test staff user: {email}')
            except Exception as e:  # noqa: BLE001
                logger.error(f'Failed to delete test staff user {email}: {str(e)}')

        # Clean up rate limiting records
        _cleanup_test_generated_records()
        logger.info('Cleanup complete')


if __name__ == '__main__':
    load_smoke_test_env()
    trigger_get_provider_ssn_endpoint_throttling()
