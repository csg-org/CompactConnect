# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
import time
from datetime import UTC, datetime, timedelta

import requests
from config import logger
from smoke_common import (
    SmokeTestFailureException,
    create_test_staff_user,
    delete_test_staff_user,
    get_api_base_url,
    get_data_events_dynamodb_table,
    get_provider_user_dynamodb_table,
    get_staff_user_auth_headers,
    load_smoke_test_env,
)

MOCK_SSN = '999-99-9999'
COMPACT = 'cosm'
JURISDICTION = 'ne'
TEST_PROVIDER_GIVEN_NAME = 'Joe'
TEST_PROVIDER_FAMILY_NAME = 'Dokes'

# This script can be run locally to test the license upload/ingest flow against a sandbox environment
# of the Compact Connect API.
# Your sandbox account must be deployed with the "security_profile": "VULNERABLE" setting in your cdk.context.json
# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.

# Note that by design, developers do not have the ability to delete records from the SSN DynamoDB table,
# so this script does not delete the created SSN records as part of cleanup.

TEST_STAFF_USER_EMAIL = 'testStaffUserLicenseUploader@smokeTestFakeEmail.com'


def _cleanup_test_generated_records(provider_id: str, license_ingest_record_response: dict):
    """
    Cleanup all test records except the SSN record, which developers do not have the ability to delete
    """
    # Now clean up the records we added
    # First, get all provider records to delete
    provider_dynamo_table = get_provider_user_dynamodb_table()
    provider_record_query_response = provider_dynamo_table.query(
        KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': f'{COMPACT}#PROVIDER#{provider_id}'}
    )

    # Delete all provider records
    for record in provider_record_query_response.get('Items', []):
        provider_dynamo_table.delete_item(Key={'pk': record['pk'], 'sk': record['sk']})
    logger.info('Successfully deleted provider records from provider table')

    # Delete data event records
    data_events_table = get_data_events_dynamodb_table()
    for record in license_ingest_record_response.get('Items', []):
        data_events_table.delete_item(Key={'pk': record['pk'], 'sk': record['sk']})
    logger.info('Successfully deleted license ingest record from data events table')


def upload_licenses_record():
    """
    Verifies that a license record can be uploaded to the Compact Connect API and the appropriate
    records are created in the provider table as well as the data events table.

    Step 1: Upload a license record through the POST '/v1/compacts/cosm/jurisdictions/ne/licenses' endpoint.
    Step 2: Verify the provider records are added by querying the API.
    Step 3: Verify the license record is recorded in the data events table.
    """

    headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)

    # Step 1: Upload a license record through the POST '/v1/compacts/cosm/jurisdictions/ne/licenses' endpoint.
    post_body = [
        {
            'licenseNumber': 'A0608337260',
            'homeAddressPostalCode': '68001',
            'givenName': TEST_PROVIDER_GIVEN_NAME,
            'familyName': TEST_PROVIDER_FAMILY_NAME,
            'homeAddressStreet1': '123 Fake Street',
            'dateOfBirth': '1991-12-10',
            'dateOfIssuance': '2024-12-10',
            'ssn': MOCK_SSN,
            'licenseType': 'cosmetologist',
            'dateOfExpiration': '2050-12-10',
            'homeAddressState': 'AZ',
            'homeAddressCity': 'Omaha',
            'compactEligibility': 'eligible',
            'licenseStatus': 'active',
        }
    ]

    post_response = requests.post(
        url=get_api_base_url() + f'/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/licenses',
        headers=headers,
        json=post_body,
        timeout=10,
    )

    if post_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to POST license record. Response: {post_response.json()}')

    logger.info(f'License record successfully uploaded {post_response.json()}')

    # Step 2: Verify the provider records are added by querying the API
    provider_id = None

    # The preprocessing and ingest SQS queues have a visibility timeout of 5 minutes each
    # so we will need to poll until the record is available
    for _ in range(30):
        # Query the provider API to find the provider by name
        query_body = {'query': {'familyName': TEST_PROVIDER_FAMILY_NAME, 'givenName': TEST_PROVIDER_GIVEN_NAME}}

        query_response = requests.post(
            url=get_api_base_url() + f'/v1/compacts/{COMPACT}/providers/query',
            headers=headers,
            json=query_body,
            timeout=10,
        )

        if query_response.status_code != 200:
            logger.info(f'Query failed with status {query_response.status_code}. Retrying...')
            time.sleep(30)
            continue

        providers = query_response.json().get('providers', [])
        if providers:
            # Find our test provider in the results
            for provider in providers:
                if (
                    provider.get('givenName') == TEST_PROVIDER_GIVEN_NAME
                    and provider.get('familyName') == TEST_PROVIDER_FAMILY_NAME
                ):
                    provider_id = provider.get('providerId')
                    break

        if provider_id:
            break

        logger.info('Provider record not found via API query. Retrying...')
        time.sleep(30)

    if not provider_id:
        raise SmokeTestFailureException('Failed to find provider record via API query.')

    logger.info(f'Provider record successfully found via API query. Provider ID: {provider_id}')

    # Now get the provider details to verify the license record
    provider_details_response = requests.get(
        url=get_api_base_url() + f'/v1/compacts/{COMPACT}/providers/{provider_id}',
        headers=headers,
        timeout=10,
    )

    if provider_details_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to get provider details. Response: {provider_details_response.json()}')

    provider_details = provider_details_response.json()
    licenses = provider_details.get('licenses', [])

    if not licenses:
        raise SmokeTestFailureException('Failed to find license record in provider details.')

    license_record = next(
        (license_record for license_record in licenses if license_record.get('licenseType') == 'cosmetologist'), None
    )

    if not license_record:
        raise SmokeTestFailureException('Failed to find cosmetologist license record in provider details.')

    logger.info(f'License record successfully found in provider details: {license_record}')

    # Step 3: Verify the license record is recorded in the data events table.
    # we don't loop here because the record should be available in the data events table by the time the
    # provider table record is available
    data_events_table = get_data_events_dynamodb_table()
    event_time = datetime.now(tz=UTC)
    start_time = event_time - timedelta(minutes=15)
    logger.info('searching for license in data event')
    license_ingest_record_response = data_events_table.query(
        KeyConditionExpression='pk = :pk AND sk BETWEEN :start_time AND :end_time',
        ExpressionAttributeValues={
            ':pk': 'COMPACT#cosm#JURISDICTION#ne',
            ':start_time': f'TYPE#license.ingest#TIME#{int(start_time.timestamp())}',
            ':end_time': f'TYPE#license.ingest#TIME#{int(event_time.timestamp())}',
        },
    )

    if not license_ingest_record_response.get('Items'):
        logger.error(
            f'Failed to find license ingest record in data events table. Response: {license_ingest_record_response}'
        )
        _cleanup_test_generated_records(provider_id, license_ingest_record_response)
        raise SmokeTestFailureException('Failed to find license ingest records in data event table.')

    logger.info(
        f'License ingest data event successfully added to data events table {license_ingest_record_response["Items"]}'
    )
    _cleanup_test_generated_records(provider_id, license_ingest_record_response)


if __name__ == '__main__':
    load_smoke_test_env()
    # Create staff user with permission to upload licenses
    test_user_sub = create_test_staff_user(
        email=TEST_STAFF_USER_EMAIL,
        compact=COMPACT,
        jurisdiction=JURISDICTION,
        permissions={'actions': {'admin'}, 'jurisdictions': {JURISDICTION: {'write', 'admin'}}},
    )
    try:
        upload_licenses_record()
        logger.info('License record upload smoke test passed')
    except SmokeTestFailureException as e:
        logger.error(f'License record upload smoke test failed: {str(e)}')
    finally:
        # Clean up the test staff user
        delete_test_staff_user(TEST_STAFF_USER_EMAIL, user_sub=test_user_sub, compact=COMPACT)
