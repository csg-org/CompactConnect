# ruff: noqa: S101 T201  we use asserts and print statements for smoke testing

import time
from datetime import UTC, datetime, timedelta

import requests
from smoke_common import (
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
# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.


def upload_licenses_record():
    """
    Verifies that a license record can be uploaded to the Compact Connect API and the appropriate
    records are created in the provider table as well as the data events table.

    Step 1: Upload a license record through the POST '/v1/compacts/aslp/jurisdictions/ne/licenses' endpoint.
    Step 2: Verify the provider records are added to the provider's record.
    Step 3: Verify the license record is recorded in the data events table.
    """

    headers = get_staff_user_auth_headers()

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

    assert post_response.status_code == 200, f'Failed to POST license record. Response: {post_response.json()}'
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

    assert 'Item' in ssn_record_response, (
        f'Failed to find license record in provider table. ' f'Response: {ssn_record_response}'
    )
    print(f'SSN record successfully added to provider table {ssn_record_response["Item"]}')

    provider_id = ssn_record_response['Item']['providerId']
    # now get all the records for the provider and verify the license record is there
    provider_record_query_response = provider_dynamo_table.query(
        KeyConditionExpression='pk = :pk', ExpressionAttributeValues={':pk': f'{COMPACT}#PROVIDER#{provider_id}'}
    )

    assert 'Items' in provider_record_query_response, 'Failed to find provider records in provider table.'
    # we expect to find a license record and a privilege record with the following sk pattern:
    # 'sk': f'{compact}#PROVIDER'
    license_record = next(
        (record for record in provider_record_query_response['Items'] if record['type'] == 'license'), None
    )
    assert license_record, 'Failed to find license record in provider table.'
    print(f'License record successfully added to provider table {license_record}')
    provider_record = next(
        (record for record in provider_record_query_response['Items'] if record['type'] == 'provider'), None
    )
    assert provider_record, 'Failed to find provider record in provider table.'
    print(f'Provider record successfully added to provider table {provider_record}')

    # Step 3: Verify the license record is recorded in the data events table.=

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

    assert license_ingest_record_response.get('Items'), (
        f'Failed to find license ingest record in data events table.' f' Response: {license_ingest_record_response}'
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
    upload_licenses_record()
    print('License record upload smoke test passed')
