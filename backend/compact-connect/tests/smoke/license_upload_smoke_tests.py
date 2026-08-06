# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
import time
from datetime import UTC, datetime, timedelta

import requests
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    create_test_app_client,
    create_test_staff_user,
    delete_test_app_client,
    delete_test_staff_user,
    get_api_base_url,
    get_client_auth_headers,
    get_data_events_dynamodb_table,
    get_provider_user_dynamodb_table,
    get_staff_user_auth_headers,
    load_smoke_test_env,
)

MOCK_SSN = '999-99-9999'
COMPACT = 'aslp'
JURISDICTION = 'ne'
TEST_PROVIDER_GIVEN_NAME = 'Joe'
TEST_PROVIDER_FAMILY_NAME = 'Dokes'
TEST_PROVIDER_UPDATED_FAMILY_NAME = 'Dokes-Smith'
TEST_LICENSE_NUMBER = 'A0608337260'
TEST_LICENSE_TYPE = 'audiologist'

# This script can be run locally to test the license upload/ingest flow against a sandbox environment
# of the Compact Connect API.
# Your sandbox account must be deployed with the "security_profile": "VULNERABLE" setting in your cdk.context.json
# To run this script, create a smoke_tests_env.json file in the same directory as this script using the
# 'smoke_tests_env_example.json' file as a template.

# Note that by design, developers do not have the ability to delete records from the SSN DynamoDB table,
# so this script does not delete the created SSN records as part of cleanup.

TEST_STAFF_USER_EMAIL = 'testStaffUserLicenseUploader@smokeTestFakeEmail.com'
TEST_APP_CLIENT_NAME = 'test-license-upload-smoke-client'


def _post_license_to_state_api(client_id: str, client_secret: str, post_body: list[dict]) -> requests.Response:
    """POST license records to the State API's synchronous license upload endpoint.

    This endpoint only exists on the State API (not the general API) and is authenticated with a state
    IT-system client-credentials token. Those tokens are short lived, so they are regenerated for each
    upload rather than reused across the long polls between them.
    """
    return requests.post(
        url=f'{config.state_api_base_url}/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/licenses',
        headers=get_client_auth_headers(client_id, client_secret, COMPACT, JURISDICTION),
        json=post_body,
        timeout=30,
    )


def _query_license_ingest_events(minutes_back: int = 30) -> dict:
    """Find this jurisdiction's recent license ingest events, so cleanup can remove them.

    Queried at cleanup time rather than captured earlier, so that events from every upload the run
    performed are removed, not just the first one's.
    """
    end_time = datetime.now(tz=UTC)
    start_time = end_time - timedelta(minutes=minutes_back)
    return get_data_events_dynamodb_table().query(
        KeyConditionExpression='pk = :pk AND sk BETWEEN :start_time AND :end_time',
        ExpressionAttributeValues={
            ':pk': f'COMPACT#{COMPACT}#JURISDICTION#{JURISDICTION}',
            ':start_time': f'TYPE#license.ingest#TIME#{int(start_time.timestamp())}',
            ':end_time': f'TYPE#license.ingest#TIME#{int(end_time.timestamp())}',
        },
    )


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


def upload_licenses_record(client_id: str, client_secret: str):
    """
    Verifies that a license record can be uploaded to the Compact Connect API and the appropriate
    records are created in the provider table as well as the data events table.

    Step 1: Upload a license record through the State API's POST licenses endpoint.
    Step 2: Verify the provider records are added by querying the API.
    Step 3: Verify the license record is recorded in the data events table.
    """

    headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)

    # Step 1: Upload a license record through the State API's POST licenses endpoint.
    post_body = [
        {
            'npi': '1111111111',
            'licenseNumber': TEST_LICENSE_NUMBER,
            'homeAddressPostalCode': '68001',
            'givenName': TEST_PROVIDER_GIVEN_NAME,
            'familyName': TEST_PROVIDER_FAMILY_NAME,
            'homeAddressStreet1': '123 Fake Street',
            'dateOfBirth': '1991-12-10',
            'dateOfIssuance': '2024-12-10',
            'ssn': MOCK_SSN,
            'licenseType': TEST_LICENSE_TYPE,
            'dateOfExpiration': '2050-12-10',
            'homeAddressState': 'AZ',
            'homeAddressCity': 'Omaha',
            'compactEligibility': 'eligible',
            'licenseStatus': 'active',
        }
    ]

    post_response = _post_license_to_state_api(client_id, client_secret, post_body)

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
        (license_record for license_record in licenses if license_record.get('licenseType') == TEST_LICENSE_TYPE), None
    )

    if not license_record:
        raise SmokeTestFailureException(f'Failed to find {TEST_LICENSE_TYPE} license record in provider details.')

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
            ':pk': 'COMPACT#aslp#JURISDICTION#ne',
            ':start_time': f'TYPE#license.ingest#TIME#{int(start_time.timestamp())}',
            ':end_time': f'TYPE#license.ingest#TIME#{int(event_time.timestamp())}',
        },
    )

    if not license_ingest_record_response.get('Items'):
        logger.error(
            f'Failed to find license ingest record in data events table. Response: {license_ingest_record_response}'
        )
        raise SmokeTestFailureException('Failed to find license ingest records in data event table.')

    logger.info(
        f'License ingest data event successfully added to data events table {license_ingest_record_response["Items"]}'
    )

    # Cleanup is performed by the caller, so that subsequent steps can run against this same provider
    return provider_id


def upload_license_record_without_ssn(provider_id: str, client_id: str, client_secret: str):
    """
    Verifies that a license record can be updated by a state without providing the practitioner's SSN,
    identifying them instead by the license number the previous upload stored for them.

    Step 1: Re-upload the same license, with no `ssn` field and a changed family name.
    Step 2: Poll the provider until the license record reflects the new family name.
    Step 3: Verify the record was updated in place rather than a new practitioner being created.
    """
    headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)

    # Step 1: Upload the same license without an SSN, changing the family name so we can prove the
    # update was applied to the existing record rather than silently ignored. The record can only be
    # matched by its license number, since the name we are sending no longer matches what is stored.
    post_body = [
        {
            'npi': '1111111111',
            'licenseNumber': TEST_LICENSE_NUMBER,
            'homeAddressPostalCode': '68001',
            'givenName': TEST_PROVIDER_GIVEN_NAME,
            'familyName': TEST_PROVIDER_UPDATED_FAMILY_NAME,
            'homeAddressStreet1': '123 Fake Street',
            'dateOfBirth': '1991-12-10',
            'dateOfIssuance': '2024-12-10',
            'licenseType': TEST_LICENSE_TYPE,
            'dateOfExpiration': '2050-12-10',
            'homeAddressState': 'AZ',
            'homeAddressCity': 'Omaha',
            'compactEligibility': 'eligible',
            'licenseStatus': 'active',
        }
    ]

    post_response = _post_license_to_state_api(client_id, client_secret, post_body)

    if post_response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to POST license record without an SSN. Response: {post_response.json()}'
        )

    logger.info('License record without SSN successfully uploaded')

    # Step 2: Poll the provider until the updated family name is reflected on the license record
    updated_license_record = None
    for _ in range(30):
        # Access tokens are only valid for 15 minutes, which this loop can outlast, so refresh on each
        # attempt rather than reusing the token from before the upload.
        headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
        provider_details_response = requests.get(
            url=get_api_base_url() + f'/v1/compacts/{COMPACT}/providers/{provider_id}',
            headers=headers,
            timeout=10,
        )

        if provider_details_response.status_code == 200:
            provider_details = provider_details_response.json()
            license_record = next(
                (
                    record
                    for record in provider_details.get('licenses', [])
                    if record.get('licenseType') == TEST_LICENSE_TYPE
                ),
                None,
            )
            if license_record and license_record.get('familyName') == TEST_PROVIDER_UPDATED_FAMILY_NAME:
                updated_license_record = license_record
                break

        logger.info('License record not yet updated from SSN-less upload. Retrying...')
        time.sleep(30)

    if not updated_license_record:
        raise SmokeTestFailureException('License record was not updated by the upload without an SSN.')

    # Step 3: Verify the existing record was updated, rather than a second practitioner being created
    if str(updated_license_record.get('providerId')) != str(provider_id):
        raise SmokeTestFailureException(
            'License record uploaded without an SSN was associated with a different provider id: '
            f'{updated_license_record.get("providerId")} instead of {provider_id}'
        )

    if updated_license_record.get('licenseNumber') != TEST_LICENSE_NUMBER:
        raise SmokeTestFailureException('License number changed on the record uploaded without an SSN.')

    # the provider's own name is derived from their best license, so it must reflect the update too
    provider_details = provider_details_response.json()
    if provider_details.get('familyName') != TEST_PROVIDER_UPDATED_FAMILY_NAME:
        raise SmokeTestFailureException(
            'Provider record family name was not updated by the license upload without an SSN: '
            f'{provider_details.get("familyName")}'
        )

    # Querying by the new name must find this same practitioner, and only them. This query reads the
    # provider name index, which is updated asynchronously from the record we just polled for, so allow a
    # few seconds for it to catch up rather than failing the whole run on a sub-second lag.
    matching_provider_ids = set()
    for _ in range(6):
        query_response = requests.post(
            url=get_api_base_url() + f'/v1/compacts/{COMPACT}/providers/query',
            headers=headers,
            json={
                'query': {
                    'familyName': TEST_PROVIDER_UPDATED_FAMILY_NAME,
                    'givenName': TEST_PROVIDER_GIVEN_NAME,
                }
            },
            timeout=10,
        )

        if query_response.status_code != 200:
            raise SmokeTestFailureException(f'Failed to query providers. Response: {query_response.json()}')

        matching_provider_ids = {
            provider.get('providerId')
            for provider in query_response.json().get('providers', [])
            if provider.get('familyName') == TEST_PROVIDER_UPDATED_FAMILY_NAME
            and provider.get('givenName') == TEST_PROVIDER_GIVEN_NAME
        }

        if matching_provider_ids:
            break

        logger.info('Updated name not yet reflected in the provider name index. Retrying...')
        time.sleep(5)

    if matching_provider_ids != {provider_id}:
        raise SmokeTestFailureException(
            'Expected the SSN-less upload to update the existing practitioner only, but found provider ids: '
            f'{matching_provider_ids}'
        )

    logger.info('License record successfully updated by an upload without an SSN')


if __name__ == '__main__':
    load_smoke_test_env()
    # Create staff user with permission to upload licenses
    test_user_sub = create_test_staff_user(
        email=TEST_STAFF_USER_EMAIL,
        compact=COMPACT,
        jurisdiction=JURISDICTION,
        permissions={'actions': {'admin'}, 'jurisdictions': {JURISDICTION: {'write', 'admin'}}},
    )
    # The license upload endpoint lives on the State API and authenticates a state IT system, so it needs
    # an app client. The staff user above is still needed for the provider query/detail calls, which are
    # on the general API.
    provider_id = None
    client_id = None
    try:
        client_credentials = create_test_app_client(TEST_APP_CLIENT_NAME, COMPACT, JURISDICTION)
        client_id = client_credentials['client_id']
        client_secret = client_credentials['client_secret']

        provider_id = upload_licenses_record(client_id, client_secret)
        logger.info('License record upload smoke test passed')

        upload_license_record_without_ssn(provider_id, client_id, client_secret)
        logger.info('License record upload without SSN smoke test passed')
    except SmokeTestFailureException as e:
        logger.error(f'License record upload smoke test failed: {str(e)}')
    finally:
        # Cleanup runs here, rather than at the end of the first step, so that both steps operate on the
        # same provider and the records are still removed if either step fails. The ingest events are
        # re-queried here so that both uploads' events are cleaned up.
        if provider_id:
            _cleanup_test_generated_records(provider_id, _query_license_ingest_events())
        if client_id:
            delete_test_app_client(client_id)
        # Clean up the test staff user
        delete_test_staff_user(TEST_STAFF_USER_EMAIL, user_sub=test_user_sub, compact=COMPACT)
