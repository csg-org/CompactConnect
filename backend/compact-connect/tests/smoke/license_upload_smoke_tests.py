# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
import time
from datetime import UTC, datetime, timedelta

import requests
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
COMPACT = 'aslp'
JURISDICTION = 'ne'

# This script can be run locally to test the license upload/ingest flow against a sandbox environment
# of the Compact Connect API.
# Your sandbox account must be deployed with the "security_profile": "VULNERABLE" setting in your cdk.context.json
# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.

TEST_STAFF_USER_EMAIL = 'testStaffUserLicenseUploader@smokeTestFakeEmail.com'


def upload_licenses_record():
    """
    Verifies that a license record can be uploaded to the Compact Connect API and the appropriate
    records are created in the provider table as well as the data events table.

    Step 1: Upload a license record through the POST '/v1/compacts/aslp/jurisdictions/ne/licenses' endpoint.
    Step 2: Verify the provider records are added to the provider's record.
    Step 3: Verify the license record is recorded in the data events table.
    """

    headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)

    # Step 1: Upload a license record through the POST '/v1/compacts/aslp/jurisdictions/ne/licenses' endpoint.
    post_body = [
        {
            'npi': '1111111111',
            'homeAddressPostalCode': '68001',
            'givenName': 'Joe',
            'familyName': 'Dokes',
            'homeAddressStreet1': '123 Fake Street',
            'militaryWaiver': False,
            'dateOfBirth': '1991-12-10',
            'dateOfIssuance': '2024-12-10',
            'ssn': MOCK_SSN,
            'licenseType': 'audiologist',
            'dateOfExpiration': '2050-12-10',
            'homeAddressState': 'AZ',
            'dateOfRenewal': '2051-12-10',
            'homeAddressCity': 'Omaha',
            'status': 'active',
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

    print(f'License record successfully uploaded {post_response.json()}')

    # Step 2: Verify the provider records are added to the provider's record.

    provider_dynamo_table = get_provider_user_dynamodb_table()

    # The ingest SQS queue has a visibility timeout of 5 minutes
    # so we will need to poll the provider table until the record is available
    for _ in range(15):
        ssn_record_response = provider_dynamo_table.get_item(
            Key={'pk': f'{COMPACT}#SSN#{MOCK_SSN}', 'sk': f'{COMPACT}#SSN#{MOCK_SSN}'}
        )
        if 'Item' in ssn_record_response:
            break
        print('License record not found in provider table. Retrying...')
        time.sleep(30)

    if 'Item' not in ssn_record_response:
        raise SmokeTestFailureException(
            f'Failed to find license record in provider table. Response: {ssn_record_response}'
        )
    print(f'SSN record successfully added to provider table {ssn_record_response["Item"]}')

    provider_id = ssn_record_response['Item']['providerId']
    # now get all the records for the provider and verify the license record is there
    provider_record_query_response = provider_dynamo_table.query(
        KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': f'{COMPACT}#PROVIDER#{provider_id}'}
    )

    if 'Items' not in provider_record_query_response:
        raise SmokeTestFailureException('Failed to find provider records in provider table.')
    # we expect to find a license record and a privilege record with the following sk pattern:
    # 'sk': f'{compact}#PROVIDER'
    license_record = next(
        (record for record in provider_record_query_response['Items'] if record['type'] == 'license'), None
    )
    if not license_record:
        raise SmokeTestFailureException('Failed to find license record in provider table.')
    print(f'License record successfully added to provider table {license_record}')
    provider_record = next(
        (record for record in provider_record_query_response['Items'] if record['type'] == 'provider'), None
    )
    if not provider_record:
        raise SmokeTestFailureException('Failed to find provider record in provider table.')
    print(f'Provider record successfully added to provider table {provider_record}')

    # Step 3: Verify the license record is recorded in the data events table.

    # we don't loop here because the record should be available in the data events table by the time the
    # provider table record is available
    data_events_table = get_data_events_dynamodb_table()
    event_time = datetime.now(tz=UTC)
    start_time = event_time - timedelta(minutes=10)
    license_ingest_record_response = data_events_table.query(
        KeyConditionExpression='pk = :pk AND sk BETWEEN :start_time AND :end_time',
        ExpressionAttributeValues={
            ':pk': 'COMPACT#aslp#JURISDICTION#ne',
            ':start_time': f'TYPE#license.ingest#TIME#{int(start_time.timestamp())}',
            ':end_time': f'TYPE#license.ingest#TIME#{int(event_time.timestamp())}',
        },
    )

    if not license_ingest_record_response.get('Items'):
        raise SmokeTestFailureException(
            f'Failed to find license ingest record in data events table. Response: {license_ingest_record_response}'
        )
    print(
        f'License ingest data event successfully added to data events table {license_ingest_record_response["Items"]}'
    )

    # now clear out the records we added
    provider_dynamo_table.delete_item(Key={'pk': f'{COMPACT}#SSN#{MOCK_SSN}', 'sk': f'{COMPACT}#SSN#{MOCK_SSN}'})
    print('Successfully deleted ssn record from provider table')
    for record in provider_record_query_response['Items']:
        provider_dynamo_table.delete_item(Key={'pk': record['pk'], 'sk': record['sk']})
    print('Successfully deleted provider records from provider table')
    for record in license_ingest_record_response['Items']:
        data_events_table.delete_item(Key={'pk': record['pk'], 'sk': record['sk']})
    print('Successfully deleted license ingest record from data events table')


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
        print('License record upload smoke test passed')
    except SmokeTestFailureException as e:
        print(f'License record upload smoke test failed: {str(e)}')
    finally:
        # Clean up the test staff user
        delete_test_staff_user(TEST_STAFF_USER_EMAIL, user_sub=test_user_sub, compact=COMPACT)
