# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
import time
from datetime import UTC, datetime

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

TEST_STAFF_USER_EMAIL = 'testStaffUserSocwLicenseUploader@smokeTestFakeEmail.com'
TEST_APP_CLIENT_NAME = 'test-license-upload-smoke-client'
HOME_STATE_CHANGE_MOCK_SSN = '999-88-8888'
HOME_STATE_CHANGE_PROVIDER_GIVEN_NAME = 'Jane'
HOME_STATE_CHANGE_PROVIDER_FAMILY_NAME = 'TestSmith'
HOME_STATE_CHANGE_LICENSE_TYPE = 'licensed bachelors social worker'
HOME_STATE_CHANGE_FORMER_JURISDICTION = 'az'
HOME_STATE_CHANGE_NEW_JURISDICTION = 'oh'
UNRECOGNIZED_LICENSE_TYPE_JURISDICTION = 'co'
UNRECOGNIZED_LICENSE_TYPE_MOCK_SSN = '999-77-7777'
# three states, co does not recognize license type, oh is home state, so only az should be returned in
# list of privileges
EXPECTED_PRIVILEGE_JURISDICTIONS = {'az'}


class PractitionerTestState:
    """Mutable holder so callers can clean up practitioner records even if the test fails mid-run."""

    provider_id: str | None = None
    start_time: datetime | None = None


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


def _build_home_state_change_license_post_body(
    jurisdiction: str,
    date_of_issuance: str,
    license_scope: str = 'single-state',
):
    license_number_suffix = 'SS' if license_scope == 'single-state' else 'MS'
    return [
        {
            'licenseNumber': f'{jurisdiction.upper()}-{license_number_suffix}-HOME-STATE-TEST',
            'homeAddressPostalCode': '68001',
            'givenName': HOME_STATE_CHANGE_PROVIDER_GIVEN_NAME,
            'familyName': HOME_STATE_CHANGE_PROVIDER_FAMILY_NAME,
            'homeAddressStreet1': '123 Home State Test Street',
            'dateOfBirth': '1991-12-10',
            'dateOfIssuance': date_of_issuance,
            'ssn': HOME_STATE_CHANGE_MOCK_SSN,
            'licenseType': HOME_STATE_CHANGE_LICENSE_TYPE,
            'licenseScope': license_scope,
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

    logger.info(
        f'Home state change license record successfully uploaded for {jurisdiction} '
        f'and scope {post_body[0].get("licenseScope")}: {post_response.json()}'
    )


def _build_invalid_license_type_post_body():
    return [
        {
            'licenseNumber': 'CO-INVALID-LICENSE-TYPE-TEST',
            'homeAddressPostalCode': '80202',
            'givenName': 'InvalidLicenseType',
            'familyName': 'SmokeTest',
            'homeAddressStreet1': '123 Invalid License Type Street',
            'dateOfBirth': '1990-01-01',
            'dateOfIssuance': '2024-01-01',
            'ssn': UNRECOGNIZED_LICENSE_TYPE_MOCK_SSN,
            'licenseType': HOME_STATE_CHANGE_LICENSE_TYPE,
            'licenseScope': 'single-state',
            'dateOfExpiration': '2050-12-10',
            'homeAddressState': UNRECOGNIZED_LICENSE_TYPE_JURISDICTION.upper(),
            'homeAddressCity': 'Denver',
            'compactEligibility': 'eligible',
            'licenseStatus': 'active',
        }
    ]


def test_license_type_not_recognized_in_jurisdiction_rejected(client_id: str, client_secret: str):
    """Verify POST rejects license types that the uploading jurisdiction does not recognize."""
    post_body = _build_invalid_license_type_post_body()
    auth_headers = get_client_auth_headers(client_id, client_secret, COMPACT, UNRECOGNIZED_LICENSE_TYPE_JURISDICTION)
    post_response = requests.post(
        url=(
            f'{config.state_api_base_url}/v1/compacts/{COMPACT}/jurisdictions/'
            f'{UNRECOGNIZED_LICENSE_TYPE_JURISDICTION}/licenses'
        ),
        headers=auth_headers,
        json=post_body,
        timeout=60,
    )

    if post_response.status_code != 400:
        raise SmokeTestFailureException(
            'Expected 400 when posting an unrecognized license type for the jurisdiction. '
            f'Response status: {post_response.status_code}, body: {post_response.json()}'
        )

    expected_response = {
        'message': 'Invalid license records in request. See errors for more detail.',
        'errors': {
            '0': {
                'licenseType': [
                    f'License type {HOME_STATE_CHANGE_LICENSE_TYPE} is not recognized in '
                    f'jurisdiction {UNRECOGNIZED_LICENSE_TYPE_JURISDICTION}.'
                ]
            }
        },
    }
    if post_response.json() != expected_response:
        raise SmokeTestFailureException(
            'Unexpected validation error response for unrecognized license type. '
            f'Expected: {expected_response}, got: {post_response.json()}'
        )

    logger.info(
        f'Successfully rejected {HOME_STATE_CHANGE_LICENSE_TYPE} license upload '
        f'for jurisdiction {UNRECOGNIZED_LICENSE_TYPE_JURISDICTION}'
    )


def _wait_for_oh_license_scope(
    provider_id: str,
    license_scope: str,
    *,
    max_wait_seconds: int = 720,
    poll_interval_seconds: int = 60,
):
    """Wait until OH license with the given scope is visible before uploading the paired scope."""
    max_attempts = max_wait_seconds // poll_interval_seconds
    for attempt in range(1, max_attempts + 1):
        staff_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
        provider_details = call_provider_details_endpoint(
            headers=staff_headers, compact=COMPACT, provider_id=provider_id
        )
        matching_licenses = [
            license_record
            for license_record in provider_details.get('licenses', [])
            if license_record.get('jurisdiction') == HOME_STATE_CHANGE_NEW_JURISDICTION
            and license_record.get('licenseType') == HOME_STATE_CHANGE_LICENSE_TYPE
            and license_record.get('licenseScope') == license_scope
        ]
        if matching_licenses:
            logger.info(f'Found OH {HOME_STATE_CHANGE_LICENSE_TYPE} {license_scope} license for provider {provider_id}')
            return

        if attempt < max_attempts:
            logger.info(
                f'OH {license_scope} license not visible yet for provider {provider_id}. '
                f'Attempt {attempt}/{max_attempts}. Retrying in {poll_interval_seconds} seconds.'
            )
            time.sleep(poll_interval_seconds)

    raise SmokeTestFailureException(
        f'Timed out waiting for OH {license_scope} {HOME_STATE_CHANGE_LICENSE_TYPE} license for provider {provider_id}'
    )


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


def test_home_state_change_notification(
    staff_headers: dict,
    client_id: str,
    client_secret: str,
    practitioner_state: PractitionerTestState,
) -> None:
    practitioner_state.start_time = datetime.now(tz=UTC)
    _post_license_to_state_api(
        client_id=client_id,
        client_secret=client_secret,
        jurisdiction=HOME_STATE_CHANGE_FORMER_JURISDICTION,
        post_body=_build_home_state_change_license_post_body(
            jurisdiction=HOME_STATE_CHANGE_FORMER_JURISDICTION,
            date_of_issuance='2024-01-15',
        ),
    )

    practitioner_state.provider_id = wait_for_provider_creation(
        staff_headers=staff_headers,
        compact=COMPACT,
        given_name=HOME_STATE_CHANGE_PROVIDER_GIVEN_NAME,
        family_name=HOME_STATE_CHANGE_PROVIDER_FAMILY_NAME,
        max_wait_time=750,
        staff_user_email=TEST_STAFF_USER_EMAIL,
        poll_interval_seconds=60,
    )
    provider_id = practitioner_state.provider_id
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

    # Social-work home jurisdiction change requires a paired OH single-state before OH multi-state.
    _post_license_to_state_api(
        client_id=client_id,
        client_secret=client_secret,
        jurisdiction=HOME_STATE_CHANGE_NEW_JURISDICTION,
        post_body=_build_home_state_change_license_post_body(
            jurisdiction=HOME_STATE_CHANGE_NEW_JURISDICTION,
            date_of_issuance='2025-06-01',
            license_scope='single-state',
        ),
    )

    _wait_for_oh_license_scope(
        provider_id=provider_id,
        license_scope='single-state',
        max_wait_seconds=750,
        poll_interval_seconds=60,
    )

    if _query_home_state_change_events_for_provider(provider_id):
        raise SmokeTestFailureException(
            'provider.homeStateChange must not fire after OH single-state upload without a paired multi-state license.'
        )

    _post_license_to_state_api(
        client_id=client_id,
        client_secret=client_secret,
        jurisdiction=HOME_STATE_CHANGE_NEW_JURISDICTION,
        post_body=_build_home_state_change_license_post_body(
            jurisdiction=HOME_STATE_CHANGE_NEW_JURISDICTION,
            date_of_issuance='2025-06-15',
            license_scope='multi-state',
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
            f'Expected Social Work licenses for both {HOME_STATE_CHANGE_FORMER_JURISDICTION} and '
            f'{HOME_STATE_CHANGE_NEW_JURISDICTION}, found {sorted(updated_jurisdictions)}'
        )

    if len(updated_social_work_licenses) != 3:
        raise SmokeTestFailureException(
            f'Expected three {HOME_STATE_CHANGE_LICENSE_TYPE} licenses (AZ single-state, OH single-state, '
            f'OH multi-state), found {len(updated_social_work_licenses)}'
        )

    oh_license_scopes = {
        license_record.get('licenseScope')
        for license_record in updated_social_work_licenses
        if license_record.get('jurisdiction') == HOME_STATE_CHANGE_NEW_JURISDICTION
    }
    if oh_license_scopes != {'single-state', 'multi-state'}:
        raise SmokeTestFailureException(
            f'Expected OH licenses in both single-state and multi-state scopes, found {sorted(oh_license_scopes)}'
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


def cleanup_home_state_change_generated_records(
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


def cleanup_practitioner_records(provider_id: str, start_time: datetime):
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
    cleanup_home_state_change_generated_records(
        provider_id=provider_id,
        az_license_ingest_events=az_license_ingest_events,
        oh_license_ingest_events=oh_license_ingest_events,
        home_state_change_events=home_state_change_events,
    )


def test_provider_privileges_exclude_unrecognized_license_type_jurisdictions(provider_id: str | None):
    """Verify GET provider privileges exclude live jurisdictions that do not recognize the license type."""
    if not provider_id:
        raise SmokeTestFailureException('Provider id was not returned from practitioner setup.')

    staff_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
    provider_details = call_provider_details_endpoint(headers=staff_headers, compact=COMPACT, provider_id=provider_id)

    privileges = provider_details.get('privileges', [])
    privilege_jurisdictions = {privilege.get('jurisdiction') for privilege in privileges}

    if len(privileges) != 1:
        raise SmokeTestFailureException(
            f'Expected exactly one privilege, found {len(privileges)}: {privilege_jurisdictions}'
        )

    if privilege_jurisdictions != EXPECTED_PRIVILEGE_JURISDICTIONS:
        raise SmokeTestFailureException(
            f'Expected privilege jurisdictions {sorted(EXPECTED_PRIVILEGE_JURISDICTIONS)}, '
            f'found {sorted(privilege_jurisdictions)}'
        )

    if UNRECOGNIZED_LICENSE_TYPE_JURISDICTION in privilege_jurisdictions:
        raise SmokeTestFailureException(
            f'Expected no privilege in {UNRECOGNIZED_LICENSE_TYPE_JURISDICTION}, '
            f'but found jurisdictions {sorted(privilege_jurisdictions)}'
        )

    privilege = privileges[0]
    if privilege.get('licenseType') != HOME_STATE_CHANGE_LICENSE_TYPE:
        raise SmokeTestFailureException(
            f'Expected privilege licenseType {HOME_STATE_CHANGE_LICENSE_TYPE}, found {privilege.get("licenseType")}'
        )

    if provider_details.get('licenseJurisdiction') != HOME_STATE_CHANGE_NEW_JURISDICTION:
        raise SmokeTestFailureException(
            f'Expected licenseJurisdiction {HOME_STATE_CHANGE_NEW_JURISDICTION}, '
            f'found {provider_details.get("licenseJurisdiction")}'
        )

    logger.info(
        f'Successfully verified privileges for provider {provider_id}: '
        f'{sorted(privilege_jurisdictions)} (excludes {UNRECOGNIZED_LICENSE_TYPE_JURISDICTION})'
    )


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
    test_jurisdiction_configuration(UNRECOGNIZED_LICENSE_TYPE_JURISDICTION)

    test_user_sub = None
    client_id = None
    practitioner_state = PractitionerTestState()
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
                    UNRECOGNIZED_LICENSE_TYPE_JURISDICTION: {'write', 'admin'},
                },
            },
        )

        client_credentials = create_test_app_client(
            TEST_APP_CLIENT_NAME,
            COMPACT,
            jurisdictions=[
                HOME_STATE_CHANGE_FORMER_JURISDICTION,
                HOME_STATE_CHANGE_NEW_JURISDICTION,
                UNRECOGNIZED_LICENSE_TYPE_JURISDICTION,
            ],
        )
        client_id = client_credentials['client_id']
        client_secret = client_credentials['client_secret']
        test_license_type_not_recognized_in_jurisdiction_rejected(
            client_id=client_id,
            client_secret=client_secret,
        )
        logger.info('Invalid license type jurisdiction validation smoke test passed')
        staff_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
        test_home_state_change_notification(
            staff_headers=staff_headers,
            client_id=client_id,
            client_secret=client_secret,
            practitioner_state=practitioner_state,
        )
        test_provider_privileges_exclude_unrecognized_license_type_jurisdictions(practitioner_state.provider_id)
        logger.info('License upload smoke tests passed')
    except SmokeTestFailureException as e:
        logger.error(f'License record upload smoke test failed: {str(e)}')
    finally:
        if practitioner_state.provider_id and practitioner_state.start_time:
            logger.info(
                'Cleaning up license upload smoke test records',
                provider_id=practitioner_state.provider_id,
            )
            cleanup_practitioner_records(practitioner_state.provider_id, practitioner_state.start_time)
        if client_id:
            delete_test_app_client(client_id)
        if test_user_sub:
            # Clean up the test staff user
            delete_test_staff_user(TEST_STAFF_USER_EMAIL, user_sub=test_user_sub, compact=COMPACT)
