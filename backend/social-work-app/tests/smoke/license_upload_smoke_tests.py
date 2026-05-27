# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
import time
from datetime import UTC, datetime, timedelta

import requests
from boto3.dynamodb.conditions import Key
from compact_configuration_smoke_tests import test_jurisdiction_configuration
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    call_provider_details_endpoint,
    create_test_app_client,
    create_test_staff_user,
    delete_test_app_client,
    delete_test_staff_user,
    get_client_auth_headers,
    get_data_events_dynamodb_table,
    get_provider_user_dynamodb_table,
    get_staff_user_auth_headers,
    load_smoke_test_env,
    wait_for_provider_creation,
)

COMPACT = 'socw'

# This script can be run locally to test the license upload/ingest flow against a sandbox environment.
# License POST uses the state API (CC_TEST_STATE_API_BASE_URL) with a short-lived Cognito app client
# (CC_TEST_STATE_AUTH_URL, CC_TEST_COGNITO_STATE_AUTH_USER_POOL_ID); provider query/GET use the internal API
# (CC_TEST_API_BASE_URL) with a staff user. Configure smoke_tests_env.json from smoke_tests_env_example.json.

# Developer note: this smoke test intentionally polls up to 12 minutes (60s interval) because the
# preprocess and ingest SQS event source mappings currently use 5-minute max batching windows.
# If faster runtime is needed, manually lower those event source mapping batching windows in the
# target environment before running this test.

# Note that by design, developers do not have the ability to delete records from the SSN DynamoDB table,
# so this script does not delete the created SSN records as part of cleanup.

TEST_STAFF_USER_EMAIL = 'testStaffUserLicenseUploader@smokeTestFakeEmail.com'
TEST_APP_CLIENT_NAME = 'test-license-upload-smoke-client'
HOME_STATE_CHANGE_MOCK_SSN = '999-88-8888'
HOME_STATE_CHANGE_PROVIDER_GIVEN_NAME = 'Jane'
HOME_STATE_CHANGE_PROVIDER_FAMILY_NAME = 'TestSmith'
HOME_STATE_CHANGE_LICENSE_TYPE = 'cosmetologist'
HOME_STATE_CHANGE_FORMER_JURISDICTION = 'az'
HOME_STATE_CHANGE_NEW_JURISDICTION = 'oh'


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


def _build_home_state_change_license_post_body(jurisdiction: str, date_of_issuance: str):
    return [
        {
            'licenseNumber': f'{jurisdiction.upper()}-HOME-STATE-TEST',
            'homeAddressPostalCode': '68001',
            'givenName': HOME_STATE_CHANGE_PROVIDER_GIVEN_NAME,
            'familyName': HOME_STATE_CHANGE_PROVIDER_FAMILY_NAME,
            'homeAddressStreet1': '123 Home State Test Street',
            'dateOfBirth': '1991-12-10',
            'dateOfIssuance': date_of_issuance,
            'ssn': HOME_STATE_CHANGE_MOCK_SSN,
            'licenseType': HOME_STATE_CHANGE_LICENSE_TYPE,
            'licenseScope': 'single-state',
            'dateOfExpiration': '2050-12-10',
            'homeAddressState': jurisdiction.upper(),
            'homeAddressCity': 'Omaha',
            'compactEligibility': 'eligible',
            'licenseStatus': 'active',
        }
    ]


def _post_license_to_state_api(client_id: str, client_secret: str, jurisdiction: str, post_body: list[dict]):
    # Access tokens are short lived, so regenerate before each upload call.
    license_upload_auth_headers = get_client_auth_headers(client_id, client_secret, COMPACT, jurisdiction)
    post_response = requests.post(
        url=f'{config.state_api_base_url}/v1/compacts/{COMPACT}/jurisdictions/{jurisdiction}/licenses',
        headers=license_upload_auth_headers,
        json=post_body,
        timeout=60,
    )

    if post_response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to POST home state change license record for {jurisdiction}. Response: {post_response.json()}'
        )

    logger.info(f'Home state change license record successfully uploaded for {jurisdiction}: {post_response.json()}')


def _wait_for_home_state_change_event(provider_id: str, max_wait_seconds: int = 720, poll_interval_seconds: int = 60):
    data_events_table = get_data_events_dynamodb_table()
    max_attempts = max_wait_seconds // poll_interval_seconds
    event_pk = f'COMPACT#{COMPACT}#JURISDICTION#{HOME_STATE_CHANGE_NEW_JURISDICTION}'

    for attempt in range(1, max_attempts + 1):
        response = data_events_table.query(
            KeyConditionExpression=Key('pk').eq(event_pk)
            & Key('sk').begins_with('TYPE#provider.homeStateChange#TIME#'),
            FilterExpression='providerId = :provider_id',
            ExpressionAttributeValues={':provider_id': provider_id},
            ConsistentRead=True,
        )
        matching_event = next(iter(response.get('Items', [])), None)
        if matching_event:
            logger.info(f'Found provider.homeStateChange data event for provider {provider_id}')
            return matching_event

        if attempt < max_attempts:
            logger.info(
                f'provider.homeStateChange event not found yet for provider {provider_id}. '
                f'Attempt {attempt}/{max_attempts}. Retrying in {poll_interval_seconds} seconds.'
            )
            time.sleep(poll_interval_seconds)

    return None


def _query_license_ingest_events_for_jurisdiction(
    jurisdiction: str, provider_id: str, start_time: datetime, end_time: datetime
):
    data_events_table = get_data_events_dynamodb_table()
    return data_events_table.query(
        KeyConditionExpression='pk = :pk AND sk BETWEEN :start_time AND :end_time',
        FilterExpression='providerId = :provider_id',
        ExpressionAttributeValues={
            ':pk': f'COMPACT#{COMPACT}#JURISDICTION#{jurisdiction}',
            ':start_time': f'TYPE#license.ingest#TIME#{int(start_time.timestamp())}',
            ':end_time': f'TYPE#license.ingest#TIME#{int(end_time.timestamp())}',
            ':provider_id': provider_id,
        },
        ConsistentRead=True,
    )


def test_home_state_change_notification(staff_headers: dict, client_id: str, client_secret: str):
    start_time = datetime.now(tz=UTC) - timedelta(minutes=2)
    provider_id = None
    try:
        _post_license_to_state_api(
            client_id=client_id,
            client_secret=client_secret,
            jurisdiction=HOME_STATE_CHANGE_FORMER_JURISDICTION,
            post_body=_build_home_state_change_license_post_body(
                jurisdiction=HOME_STATE_CHANGE_FORMER_JURISDICTION, date_of_issuance='2024-01-15'
            ),
        )

        provider_id = wait_for_provider_creation(
            staff_headers=staff_headers,
            compact=COMPACT,
            given_name=HOME_STATE_CHANGE_PROVIDER_GIVEN_NAME,
            family_name=HOME_STATE_CHANGE_PROVIDER_FAMILY_NAME,
            max_wait_time=750,
            staff_user_email=TEST_STAFF_USER_EMAIL,
            poll_interval_seconds=60,
        )
        logger.info(f'Found home state change test provider id {provider_id}')

        refreshed_staff_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
        az_provider_details = call_provider_details_endpoint(
            headers=refreshed_staff_headers, compact=COMPACT, provider_id=provider_id
        )
        az_social_work_licenses = [
            license_record
            for license_record in az_provider_details.get('licenses', [])
            if license_record.get('licenseType') == HOME_STATE_CHANGE_LICENSE_TYPE
        ]

        if len(az_social_work_licenses) != 1:
            raise SmokeTestFailureException(
                f'Expected one {HOME_STATE_CHANGE_LICENSE_TYPE} license after AZ upload, '
                f'found {len(az_social_work_licenses)}'
            )

        if az_social_work_licenses[0].get('jurisdiction') != HOME_STATE_CHANGE_FORMER_JURISDICTION:
            raise SmokeTestFailureException(
                'Expected first home state license jurisdiction to be '
                f'{HOME_STATE_CHANGE_FORMER_JURISDICTION}, found {az_social_work_licenses[0].get("jurisdiction")}'
            )

        if az_provider_details.get('licenseJurisdiction') != HOME_STATE_CHANGE_FORMER_JURISDICTION:
            raise SmokeTestFailureException(
                'Expected licenseJurisdiction to be '
                f'{HOME_STATE_CHANGE_FORMER_JURISDICTION} after first upload, '
                f'found {az_provider_details.get("licenseJurisdiction")}'
            )

        _post_license_to_state_api(
            client_id=client_id,
            client_secret=client_secret,
            jurisdiction=HOME_STATE_CHANGE_NEW_JURISDICTION,
            post_body=_build_home_state_change_license_post_body(
                # upload license that was issued at a later date to trigger home state change
                jurisdiction=HOME_STATE_CHANGE_NEW_JURISDICTION,
                date_of_issuance='2025-06-15',
            ),
        )

        home_state_change_event = _wait_for_home_state_change_event(
            provider_id=provider_id, max_wait_seconds=750, poll_interval_seconds=60
        )
        if not home_state_change_event:
            raise SmokeTestFailureException(
                'Failed to find provider.homeStateChange data event for the home state change smoke test.'
            )

        refreshed_staff_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
        updated_provider_details = call_provider_details_endpoint(
            headers=refreshed_staff_headers, compact=COMPACT, provider_id=provider_id
        )
        updated_social_work_licenses = [
            license_record
            for license_record in updated_provider_details.get('licenses', [])
            if license_record.get('licenseType') == HOME_STATE_CHANGE_LICENSE_TYPE
        ]
        updated_jurisdictions = {license_record.get('jurisdiction') for license_record in updated_social_work_licenses}
        if updated_jurisdictions != {HOME_STATE_CHANGE_FORMER_JURISDICTION, HOME_STATE_CHANGE_NEW_JURISDICTION}:
            raise SmokeTestFailureException(
                f'ExpectedSocial Worklicenses for both {HOME_STATE_CHANGE_FORMER_JURISDICTION} and '
                f'{HOME_STATE_CHANGE_NEW_JURISDICTION}, found {sorted(updated_jurisdictions)}'
            )

        if updated_provider_details.get('licenseJurisdiction') != HOME_STATE_CHANGE_NEW_JURISDICTION:
            raise SmokeTestFailureException(
                'Expected licenseJurisdiction to change to '
                f'{HOME_STATE_CHANGE_NEW_JURISDICTION}, found {updated_provider_details.get("licenseJurisdiction")}'
            )

        logger.info(
            'MANUAL VERIFICATION REQUIRED: check inbox for '
            f'{config.smoke_test_notification_email}. Verify a provider home state change email was sent to '
            f'the former home jurisdiction {HOME_STATE_CHANGE_FORMER_JURISDICTION.upper()} after upload from '
            f'{HOME_STATE_CHANGE_NEW_JURISDICTION.upper()} for provider '
            f'{HOME_STATE_CHANGE_PROVIDER_GIVEN_NAME} {HOME_STATE_CHANGE_PROVIDER_FAMILY_NAME} ({provider_id}).'
        )
    finally:
        if provider_id:
            logger.info('cleaning up test provider records', provider_id=provider_id)
            end_time = datetime.now(tz=UTC)
            az_license_ingest_events = _query_license_ingest_events_for_jurisdiction(
                jurisdiction=HOME_STATE_CHANGE_FORMER_JURISDICTION,
                provider_id=provider_id,
                start_time=start_time,
                end_time=end_time,
            )
            oh_license_ingest_events = _query_license_ingest_events_for_jurisdiction(
                jurisdiction=HOME_STATE_CHANGE_NEW_JURISDICTION,
                provider_id=provider_id,
                start_time=start_time,
                end_time=end_time,
            )
            home_state_change_events = _query_home_state_change_events_for_provider(provider_id)
            _cleanup_home_state_change_generated_records(
                provider_id=provider_id,
                az_license_ingest_events=az_license_ingest_events,
                oh_license_ingest_events=oh_license_ingest_events,
                home_state_change_events=home_state_change_events,
            )
        else:
            logger.info('Skipping provider cleanup because provider id was never discovered.')


def _cleanup_home_state_change_generated_records(
    provider_id: str,
    az_license_ingest_events: dict,
    oh_license_ingest_events: dict,
    home_state_change_events: list[dict] | None = None,
):
    merged_items = [
        *az_license_ingest_events.get('Items', []),
        *oh_license_ingest_events.get('Items', []),
    ]
    _cleanup_test_generated_records(provider_id, {'Items': merged_items})

    if home_state_change_events:
        data_events_table = get_data_events_dynamodb_table()
        for home_state_change_event in home_state_change_events:
            data_events_table.delete_item(
                Key={'pk': home_state_change_event['pk'], 'sk': home_state_change_event['sk']}
            )
        logger.info('Successfully deleted provider.homeStateChange event(s) from data events table')


def _query_home_state_change_events_for_provider(provider_id: str):
    data_events_table = get_data_events_dynamodb_table()
    event_pk = f'COMPACT#{COMPACT}#JURISDICTION#{HOME_STATE_CHANGE_NEW_JURISDICTION}'
    response = data_events_table.query(
        KeyConditionExpression=Key('pk').eq(event_pk) & Key('sk').begins_with('TYPE#provider.homeStateChange#TIME#'),
        ConsistentRead=True,
    )
    return [item for item in response.get('Items', []) if item.get('providerId') == provider_id]


if __name__ == '__main__':
    load_smoke_test_env()

    test_jurisdiction_configuration(HOME_STATE_CHANGE_FORMER_JURISDICTION, recreate_compact_config=True)
    test_jurisdiction_configuration(HOME_STATE_CHANGE_NEW_JURISDICTION)

    test_user_sub = None
    client_id = None
    try:
        # Create staff user with permission to query providers (internal API)
        test_user_sub = create_test_staff_user(
            email=TEST_STAFF_USER_EMAIL,
            compact=COMPACT,
            jurisdiction=HOME_STATE_CHANGE_FORMER_JURISDICTION,
            permissions={
                'actions': {'admin'},
                'jurisdictions': {
                    HOME_STATE_CHANGE_FORMER_JURISDICTION: {'write', 'admin'},
                    HOME_STATE_CHANGE_NEW_JURISDICTION: {'write', 'admin'},
                },
            },
        )

        client_credentials = create_test_app_client(
            TEST_APP_CLIENT_NAME,
            COMPACT,
            jurisdictions=[HOME_STATE_CHANGE_FORMER_JURISDICTION, HOME_STATE_CHANGE_NEW_JURISDICTION],
        )
        client_id = client_credentials['client_id']
        client_secret = client_credentials['client_secret']
        home_state_change_staff_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
        test_home_state_change_notification(
            staff_headers=home_state_change_staff_headers,
            client_id=client_id,
            client_secret=client_secret,
        )
        logger.info('Home state change notification smoke test passed')
    except SmokeTestFailureException as e:
        logger.error(f'License record upload smoke test failed: {str(e)}')
    finally:
        if client_id:
            delete_test_app_client(client_id)
        if test_user_sub:
            # Clean up the test staff user
            delete_test_staff_user(TEST_STAFF_USER_EMAIL, user_sub=test_user_sub, compact=COMPACT)
