# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
import requests
from config import logger
from smoke_common import (
    SmokeTestFailureException,
    create_test_staff_user,
    delete_test_staff_user,
    get_api_base_url,
    get_staff_user_auth_headers,
    get_lambda_client,
    get_provider_ssn_lambda_name,
    load_smoke_test_env,
)

from tests.smoke.smoke_common import get_rate_limiting_dynamodb_table

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

    # TODO - create three test staff users
    # Create staff user with permission to upload licenses
    # test_user_sub = create_test_staff_user(
    #     email='generated test email here',
    #     compact=COMPACT,
    #     jurisdiction=JURISDICTION,
    #     permissions={'actions': {'readSSN'}}},
    # )

    try:
        # TODO for the first two staff users, call this endpoint 7 times, assert the first 5 are successful with 200 response
        #   the 6th attempt results in a throttle (429) but does not disable the user,
        #   the 7th attempt throttles and disables the user
        #   For the third user, the first request should be successful, but the next request will trigger the 16th attempt
        #   which should shut down the lambda entirely and result in throttling.

        # headers = get_staff_user_auth_headers(staff user email)
        # get_response = requests.get(
        #     url=get_api_base_url() + f'/v1/compacts/{COMPACT}/providers/some-bogus-id/ssn',
        #     headers=headers,
        #     timeout=10,
        # )

        # if get_response.status_code != 200:
        #     raise SmokeTestFailureException(f'Expected successful response')


        # TODO assert that lambda's reserved concurrency is 0 after being invoked over 15 times
        lambda_concurrency_resp = get_lambda_client().get_function_concurrency(
        FunctionName=get_provider_ssn_lambda_name()
        )

        reserved_concurrency = lambda_concurrency_resp['ReservedConcurrentExecutions']

        if reserved_concurrency != 0:
            raise SmokeTestFailureException(f'Lambda reserved concurrency not set to zero. {reserved_concurrency}')

    except Exception as e:  # noqa: BLE001
        logger.error("Smoke test failure", failure=str(e))



    # Step 3: delete test staff users and cleanup items from the rate limiting table
    get_lambda_client().delete_function_concurrency(
        FunctionName=get_provider_ssn_lambda_name()
    )
    # TODO - delete test staff users here
    # some code here
    _cleanup_test_generated_records()





if __name__ == '__main__':
    load_smoke_test_env()
    trigger_get_provider_ssn_endpoint_throttling()
