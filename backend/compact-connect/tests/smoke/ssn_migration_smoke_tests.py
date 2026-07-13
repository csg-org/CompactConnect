# ruff: noqa: T201 we use print statements for smoke testing
#!/usr/bin/env python3
"""
Smoke tests for the SSN-correction migration feature (the optional 'previousSSN' license upload field).

When a state uploads a license with a 'previousSSN', the system migrates the license record (and any
associated records) from the provider id the incorrect SSN resolved to over to the provider id of the
corrected SSN. If the corrected license was the old provider's only license, the entire old provider is
migrated (a "full migration"): person-level records and S3 documents move as well, the old partition is
deleted, and the old Cognito account is removed so the practitioner can re-register.

These tests require:
- The 'license-ssn-correction-migration-flag' feature flag to be ENABLED in the target environment.
- A registered test provider user (CC_TEST_PROVIDER_USER_USERNAME) whose license records are stored under
  the SSN configured in the CC_TEST_PROVIDER_MOCK_SSN env var.
- The CC_TEST_PROVIDER_USER_BUCKET_NAME env var set to the environment's provider users S3 bucket.

License uploads are performed against the State API (CC_TEST_STATE_API_BASE_URL) using a Cognito
client-credentials app client, the same way state IT systems authenticate in production - see
'signature_auth_smoke_tests.py' for the pattern this follows. Provider lookups (query by name) go through
the general API (CC_TEST_API_BASE_URL) using a staff user, since 'providers/query' is a staff-facing
endpoint, not a state-facing one.

Note that by design, developers do not have the ability to delete records from the SSN DynamoDB table,
so the SSN records created by these tests are left in place. The tests use fixed mock SSNs so repeated
runs reuse the same SSN -> provider id mappings rather than accumulating new ones.

The full migration test intentionally deletes the test provider's Cognito account mid-test (that is part
of the feature) and restores it at the end, so the shared test provider account remains usable.
"""

import json
import os
import time
from collections.abc import Callable

import boto3
import requests
from botocore.exceptions import ClientError
from config import config, logger
from military_affiliation_smoke_tests import test_military_affiliation_upload
from smoke_common import (
    SmokeTestFailureException,
    call_provider_users_me_endpoint,
    cleanup_test_provider_records,
    create_test_app_client,
    create_test_staff_user,
    delete_test_app_client,
    delete_test_staff_user,
    get_api_base_url,
    get_client_auth_headers,
    get_provider_user_dynamodb_table,
    get_staff_user_auth_headers,
    load_smoke_test_env,
    wait_for_provider_creation,
)


# If you test provider is in a different compact, change this value
TEST_COMPACT = 'coun'
# The corrected SSN the test provider is temporarily migrated to during the full migration roundtrip
FULL_MIGRATION_CORRECTED_SSN = '999-99-8877'

# Partial migration test constants: a standalone mock practitioner with OT + OTA licenses in octp/ne
PARTIAL_MIGRATION_COMPACT = 'octp'
PARTIAL_MIGRATION_JURISDICTION = 'ne'
PARTIAL_MIGRATION_GIVEN_NAME = 'SsnMigration'
PARTIAL_MIGRATION_FAMILY_NAME = 'PartialSmokeTest'
PARTIAL_MIGRATION_ORIGINAL_SSN = '999-99-8888'
PARTIAL_MIGRATION_CORRECTED_SSN = '999-99-8899'
OT_LICENSE_TYPE = 'occupational therapist'
OTA_LICENSE_TYPE = 'occupational therapy assistant'

TEST_STAFF_USER_EMAIL = 'testStaffUserSsnMigration@smokeTestFakeEmail.com'
TEST_APP_CLIENT_NAME = 'test-ssn-migration-client'

# License fields that can be round-tripped from a provider's existing license record into an upload payload
_UPLOADABLE_LICENSE_FIELDS = (
    'npi',
    'licenseNumber',
    'licenseStatusName',
    'givenName',
    'middleName',
    'familyName',
    'suffix',
    'dateOfBirth',
    'dateOfIssuance',
    'dateOfRenewal',
    'dateOfExpiration',
    'homeAddressStreet1',
    'homeAddressStreet2',
    'homeAddressCity',
    'homeAddressState',
    'homeAddressPostalCode',
    'emailAddress',
    'phoneNumber',
    'licenseType',
)

# Record fields that legitimately change when a record is re-keyed to a new provider id, and so are
# excluded when comparing a provider's records before and after a migration. The provider id itself is
# normalized (not dropped) so that provider-id-derived fields still participate in the comparison.
_VOLATILE_RECORD_FIELDS = ('pk', 'sk', 'dateOfUpdate', 'providerDateOfUpdate', 'ssnLastFour')

_MIGRATION_WAIT_SECONDS = 900
_POLL_INTERVAL_SECONDS = 30


# -------------------------------------------------------------------------------------------------
# Shared helpers
# -------------------------------------------------------------------------------------------------
def _upload_license_records(client_headers: dict, compact: str, jurisdiction: str, license_records: list[dict]):
    """POST the given license records to the State API's synchronous license upload endpoint.

    This endpoint only exists on the State API (not the general API) and is authenticated with a state
    IT-system client-credentials token, per 'client_headers' - see '_create_test_app_client_headers'.
    """
    post_response = requests.post(
        url=f'{config.state_api_base_url}/v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses',
        headers=client_headers,
        json=license_records,
        timeout=30,
    )
    if post_response.status_code != 200:
        raise SmokeTestFailureException(f'Failed to POST license records. Response: {post_response.json()}')
    print(f'Successfully uploaded {len(license_records)} license record(s) to {compact}/{jurisdiction}')


def _create_test_app_client_headers(client_name: str, compact: str, jurisdiction: str) -> tuple[dict, str]:
    """Create a state IT-system test app client and return (auth headers, client_id) for later cleanup."""
    client_credentials = create_test_app_client(client_name, compact, jurisdiction)
    client_headers = get_client_auth_headers(
        client_credentials['client_id'], client_credentials['client_secret'], compact, jurisdiction
    )
    return client_headers, client_credentials['client_id']


def _get_provider_dynamo_records(compact: str, provider_id: str) -> list[dict]:
    """Query DynamoDB directly for every record under the provider's partition."""
    dynamo_table = get_provider_user_dynamodb_table()
    records = []
    last_evaluated_key = None
    while True:
        pagination = {'ExclusiveStartKey': last_evaluated_key} if last_evaluated_key else {}
        query_response = dynamo_table.query(
            KeyConditionExpression='pk = :pk',
            ExpressionAttributeValues={':pk': f'{compact}#PROVIDER#{provider_id}'},
            ConsistentRead=True,
            **pagination,
        )
        records.extend(query_response.get('Items', []))
        last_evaluated_key = query_response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    return records


def _list_provider_s3_keys(compact: str, provider_id: str) -> list[str]:
    """List the S3 object keys under the provider's keyspace, without downloading the objects."""
    s3_client = boto3.client('s3')
    provider_prefix = f'compact/{compact}/provider/{provider_id}/'
    keys = []
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=config.provider_user_bucket_name, Prefix=provider_prefix):
        keys.extend(s3_object['Key'] for s3_object in page.get('Contents', []))
    return keys


def _get_provider_s3_objects(compact: str, provider_id: str) -> dict[str, bytes]:
    """List every S3 object under the provider's keyspace, keyed relative to the provider prefix.

    Returns a dict of {key suffix after the provider prefix: object body bytes} so that objects can be
    compared across provider ids.
    """
    s3_client = boto3.client('s3')
    provider_prefix = f'compact/{compact}/provider/{provider_id}/'
    objects = {}
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=config.provider_user_bucket_name, Prefix=provider_prefix):
        for s3_object in page.get('Contents', []):
            object_body = s3_client.get_object(Bucket=config.provider_user_bucket_name, Key=s3_object['Key'])[
                'Body'
            ].read()
            objects[s3_object['Key'][len(provider_prefix) :]] = object_body
    return objects


def _normalized_migratable_records(records: list[dict], provider_id: str) -> dict[str, str]:
    """Canonicalize a provider's records for comparison across provider ids.

    Each record is serialized with its provider id replaced by a placeholder (which also normalizes
    provider-id-derived values such as document keys and embedded 'previous' snapshots) and with fields
    that legitimately change during a migration removed.

    The top-level provider record is excluded: it is rebuilt (not moved) during a migration, and the
    ssnCorrection provider update records created by each migration are also excluded since they are
    additions rather than migrated records.
    """
    normalized = {}
    for record in records:
        if record['type'] == 'provider' or (
            record['type'] == 'providerUpdate' and record.get('updateType') == 'ssnCorrection'
        ):
            continue
        scrubbed = {key: value for key, value in record.items() if key not in _VOLATILE_RECORD_FIELDS}
        canonical = json.dumps(scrubbed, sort_keys=True, default=str).replace(provider_id, '<PROVIDER_ID>')
        # key by something readable for failure messages
        normalized[f'{record["type"]}: {record["sk"].replace(provider_id, "<PROVIDER_ID>")}'] = canonical
    return normalized


def _verify_all_records_migrated(
    *, source_records: list[dict], source_provider_id: str, target_records: list[dict], target_provider_id: str
):
    """Verify every migratable record captured from the source provider now exists under the target provider."""
    source_normalized = _normalized_migratable_records(source_records, source_provider_id)
    target_normalized = set(_normalized_migratable_records(target_records, target_provider_id).values())

    missing_records = [label for label, canonical in source_normalized.items() if canonical not in target_normalized]
    if missing_records:
        raise SmokeTestFailureException(
            f'The following records were not migrated to provider {target_provider_id}: {missing_records}'
        )
    print(f'Verified all {len(source_normalized)} migratable records now exist under provider {target_provider_id}')


def _verify_all_s3_objects_migrated(*, source_objects: dict[str, bytes], compact: str, target_provider_id: str):
    """Verify every S3 object captured from the source keyspace exists, byte-for-byte, under the target keyspace."""
    target_objects = _get_provider_s3_objects(compact, target_provider_id)
    for relative_key, source_body in source_objects.items():
        if relative_key not in target_objects:
            raise SmokeTestFailureException(
                f'S3 object {relative_key} was not migrated to provider {target_provider_id}'
            )
        if target_objects[relative_key] != source_body:
            raise SmokeTestFailureException(
                f'S3 object {relative_key} under provider {target_provider_id} does not match the original content'
            )
    print(f'Verified all {len(source_objects)} S3 objects migrated to provider {target_provider_id} keyspace')


def _wait_until(description: str, predicate: Callable, max_wait_seconds: int = _MIGRATION_WAIT_SECONDS):
    """Poll the given predicate until it returns a truthy value, or raise after the wait limit."""
    start_time = time.time()
    while time.time() - start_time < max_wait_seconds:
        result = predicate()
        if result:
            print(f'✅ {description} (after {time.time() - start_time:.0f} seconds)')
            return result
        print(f'Waiting for {description}...')
        time.sleep(_POLL_INTERVAL_SECONDS)
    raise SmokeTestFailureException(f'Timed out after {max_wait_seconds} seconds waiting for {description}')


def _query_provider_ids_by_name(staff_headers: dict, compact: str, given_name: str, family_name: str) -> list[str]:
    """Query the providers endpoint by name and return all matching provider ids."""
    query_response = requests.post(
        url=f'{get_api_base_url()}/v1/compacts/{compact}/providers/query',
        headers=staff_headers,
        json={'query': {'familyName': family_name, 'givenName': given_name}},
        timeout=10,
    )
    if query_response.status_code != 200:
        logger.warning(f'Provider query failed with status {query_response.status_code}')
        return []
    return [provider['providerId'] for provider in query_response.json().get('providers', [])]


# -------------------------------------------------------------------------------------------------
# Full migration test (with roundtrip back to the original SSN)
# -------------------------------------------------------------------------------------------------
def _build_correction_upload_from_existing_license(
    provider_data: dict, license_record: dict, *, corrected_ssn: str, previous_ssn: str
) -> dict:
    """Build a license upload payload that mirrors an existing license record, with a corrected SSN.

    Mirroring the existing license data keeps the post-migration license write a no-op content-wise, so the
    migration is the only change under test.
    """
    upload = {
        field: license_record[field] for field in _UPLOADABLE_LICENSE_FIELDS if license_record.get(field) is not None
    }
    # dateOfBirth is not always returned on the license object itself; fall back to the provider record
    upload.setdefault('dateOfBirth', provider_data['dateOfBirth'])
    # these fields are stored under jurisdiction-uploaded names internally
    upload['licenseStatus'] = license_record['jurisdictionUploadedLicenseStatus']
    upload['compactEligibility'] = license_record['jurisdictionUploadedCompactEligibility']
    upload['ssn'] = corrected_ssn
    upload['previousSSN'] = previous_ssn
    return upload


def _migrate_test_provider_to_ssn(
    *,
    staff_headers: dict,
    client_headers: dict,
    provider_data: dict,
    license_record: dict,
    current_provider_id: str,
    corrected_ssn: str,
    previous_ssn: str,
) -> str:
    """Upload the test provider's license with a corrected SSN and wait for the migration to complete.

    :param staff_headers: Staff auth headers, used to query for the provider by name (general API)
    :param client_headers: State IT-system client-credentials headers, used to upload the license (State API)
    :return: The provider id the records were migrated to
    """
    compact = provider_data['compact']
    upload = _build_correction_upload_from_existing_license(
        provider_data, license_record, corrected_ssn=corrected_ssn, previous_ssn=previous_ssn
    )
    _upload_license_records(client_headers, compact, license_record['jurisdiction'], [upload])

    # The migration is complete once the provider's records resolve to a different provider id
    def _find_new_provider_id():
        provider_ids = _query_provider_ids_by_name(
            staff_headers, compact, provider_data['givenName'], provider_data['familyName']
        )
        return next((provider_id for provider_id in provider_ids if provider_id != current_provider_id), None)

    new_provider_id = _wait_until(
        f'the test provider to migrate off of provider id {current_provider_id}', _find_new_provider_id
    )

    # The old partition is emptied by the migration, and the S3 objects move just after the DynamoDB records
    _wait_until(
        f'all DynamoDB records to be removed from old provider {current_provider_id}',
        lambda: not _get_provider_dynamo_records(compact, current_provider_id),
        max_wait_seconds=900,
    )
    _wait_until(
        f'all S3 objects to be removed from old provider {current_provider_id} keyspace',
        lambda: not _list_provider_s3_keys(compact, current_provider_id),
        max_wait_seconds=900,
    )
    return new_provider_id


def _restore_test_provider_account(compact: str, provider_id: str, baseline_provider_record: dict):
    """Restore the shared test provider account after a full migration deleted its Cognito user.

    Recreates the provider Cognito user pointed at the given provider id and restores the registration
    fields on the top-level provider record, which are intentionally dropped by the migration (in real
    usage the practitioner re-registers).

    If the Cognito user already exists, this is a no-op: 'custom:compact' and 'custom:providerId' are
    immutable Cognito custom attributes, so an existing user cannot be re-pointed at a different provider
    id. A pre-existing user only happens when the full migration never actually deleted it (e.g. the test
    failed before reaching that step, or this is being called defensively after a failure), in which case
    the account is already valid and does not need restoring.
    """
    username = config.test_provider_user_username
    try:
        config.cognito_client.admin_create_user(
            UserPoolId=config.cognito_provider_user_pool_id,
            Username=username,
            UserAttributes=[
                {'Name': 'custom:compact', 'Value': compact},
                {'Name': 'custom:providerId', 'Value': provider_id},
                {'Name': 'email', 'Value': username},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
            MessageAction='SUPPRESS',
        )
        print(f'Recreated test provider Cognito user, pointed at provider id {provider_id}')
    except ClientError as e:
        if e.response['Error']['Code'] != 'UsernameExistsException':
            raise
        print(
            f'Test provider Cognito user already exists; leaving it as-is (custom:providerId is immutable, '
            f'so it cannot be re-pointed at provider id {provider_id})'
        )
        return

    config.cognito_client.admin_set_user_password(
        UserPoolId=config.cognito_provider_user_pool_id,
        Username=username,
        Password=config.test_provider_user_password,
        Permanent=True,
    )
    # clear the cached provider token so the next /me call performs a fresh login against the restored user
    os.environ.pop('TEST_PROVIDER_USER_ID_TOKEN', None)

    # restore the registration fields on the provider record, which populate_provider_record does not carry over
    registration_fields = {
        field: baseline_provider_record[field]
        for field in ('compactConnectRegisteredEmailAddress', 'currentHomeJurisdiction')
        if field in baseline_provider_record
    }
    if registration_fields:
        get_provider_user_dynamodb_table().update_item(
            Key={'pk': f'{compact}#PROVIDER#{provider_id}', 'sk': f'{compact}#PROVIDER'},
            UpdateExpression='SET ' + ', '.join(f'#{i} = :{i}' for i in range(len(registration_fields))),
            ExpressionAttributeNames={f'#{i}': field for i, field in enumerate(registration_fields)},
            ExpressionAttributeValues={f':{i}': value for i, value in enumerate(registration_fields.values())},
        )
        print(f'Restored registration fields on provider record {provider_id}: {sorted(registration_fields)}')


def _cognito_user_exists(username: str) -> bool:
    """Check whether a Cognito user currently exists in the provider user pool."""
    try:
        config.cognito_client.admin_get_user(UserPoolId=config.cognito_provider_user_pool_id, Username=username)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'UserNotFoundException':
            return False
        raise


def _recover_stranded_test_provider():
    """
    Detect and recover from a previous full migration test run that was interrupted after the shared test
    provider's records were migrated off of their original provider id, but before they were migrated back
    (e.g. the process was killed while waiting on a slow migration). In that state, the test provider's
    Cognito account no longer exists (deleted by the full migration) and their records are stranded under
    whatever provider id the intermediate corrected SSN currently resolves to.

    If the original provider id has no records AND the Cognito account does not exist, this prompts the
    developer for the stranded (new) provider id, migrates the records back to the original provider id,
    and recreates the Cognito account - so the test below can then proceed exactly as it would from a
    clean starting state. Otherwise this is a no-op: either the records are already home, or the account
    is already usable.

    Developers cannot look up provider ids via the SSN table, so the stranded provider id must be supplied
    manually (e.g. from CloudWatch logs or a DynamoDB console query from the interrupted run).
    """

    if _get_provider_dynamo_records(TEST_COMPACT, config.test_provider_original_provider_id) or _cognito_user_exists(
        config.test_provider_user_username
    ):
        return

    print(
        'Detected a stranded test provider from an interrupted previous run (no records under the original '
        'provider id and no Cognito account). Recovering before running the test...'
    )
    print(
        'Enter the provider id where the stranded records currently live '
        '(the id they were migrated to during the interrupted run).'
    )
    stuck_provider_id = input('Stuck provider id: ').strip()
    if not stuck_provider_id:
        raise SmokeTestFailureException(
            'Test provider records are not under the original provider id and no Cognito account exists, '
            'but no stuck provider id was provided. Re-run and supply the stranded provider id to recover.'
        )

    stuck_records = _get_provider_dynamo_records(TEST_COMPACT, stuck_provider_id)
    stuck_license = next((record for record in stuck_records if record['type'] == 'license'), None)
    stuck_provider_record = next((record for record in stuck_records if record['type'] == 'provider'), None)
    if not stuck_license or not stuck_provider_record:
        raise SmokeTestFailureException(
            f'Could not find a stranded license and provider record under provider id {stuck_provider_id} '
            f'to recover from. Confirm the provider id is correct for compact {TEST_COMPACT}.'
        )

    client_headers, client_id = _create_test_app_client_headers(
        TEST_APP_CLIENT_NAME, TEST_COMPACT, stuck_license['jurisdiction']
    )
    try:
        upload = _build_correction_upload_from_existing_license(
            stuck_provider_record,
            stuck_license,
            corrected_ssn=config.test_provider_mock_ssn,
            previous_ssn=FULL_MIGRATION_CORRECTED_SSN,
        )
        _upload_license_records(client_headers, TEST_COMPACT, stuck_license['jurisdiction'], [upload])
    finally:
        delete_test_app_client(client_id)

    _wait_until(
        'the stranded test provider records to migrate back to the original provider id',
        lambda: bool(_get_provider_dynamo_records(TEST_COMPACT, config.test_provider_original_provider_id)),
    )

    recovered_provider_record = next(
        record
        for record in _get_provider_dynamo_records(TEST_COMPACT, config.test_provider_original_provider_id)
        if record['type'] == 'provider'
    )
    _restore_test_provider_account(
        TEST_COMPACT, config.test_provider_original_provider_id, recovered_provider_record
    )
    print('Recovery complete: records and Cognito account are back under the original provider id.')


def test_full_ssn_migration_roundtrip():
    """
    Full migration: the test provider (single license, with military documentation) is migrated from their
    current mock SSN to a corrected SSN, verified, then migrated back to the original SSN.

    Step 0: Recover from any prior interrupted run that left the test provider stranded (see
            _recover_stranded_test_provider).
    Step 1: Capture the test provider's baseline state (all DynamoDB records + all S3 objects).
    Step 2: Upload a fresh military affiliation document so there is a recent document to migrate.
    Step 3: Upload the provider's license with a corrected SSN and previousSSN set to their current mock SSN.
    Step 4: Wait for the migration, then verify every record and S3 object moved to the new provider id.
    Step 5: Migrate back to the original SSN (roundtrip) and verify everything returned to the original
            provider id and the intermediate provider id was cleaned up.
    Step 6: Restore the test provider's Cognito account (deleted by the full migration) and registration
            fields so the shared test account remains usable.
    """
    _recover_stranded_test_provider()

    provider_data = call_provider_users_me_endpoint()
    compact = provider_data['compact']
    original_provider_id = provider_data['providerId']
    licenses = provider_data.get('licenses', [])
    if len(licenses) != 1:
        raise SmokeTestFailureException(
            f'The full migration test expects the test provider to have exactly one license record; '
            f'found {len(licenses)}. A multi-license provider would only be partially migrated.'
        )
    license_record = licenses[0]
    print(f'Testing full SSN migration for provider {original_provider_id} in compact {compact}')

    # Step 1: capture the initial baseline directly from DynamoDB and S3
    baseline_records = _get_provider_dynamo_records(compact, original_provider_id)
    baseline_s3_objects = _get_provider_s3_objects(compact, original_provider_id)
    baseline_provider_record = next(record for record in baseline_records if record['type'] == 'provider')
    print(
        f'Captured baseline: {len(baseline_records)} DynamoDB records, {len(baseline_s3_objects)} S3 objects '
        f'under provider {original_provider_id}'
    )

    # Step 2: upload a fresh military affiliation document, then re-capture the pre-migration state so the
    # new document (record + S3 object) is included in what we expect to migrate
    test_military_affiliation_upload()
    pre_migration_records = _get_provider_dynamo_records(compact, original_provider_id)
    pre_migration_s3_objects = _get_provider_s3_objects(compact, original_provider_id)
    print(
        f'Pre-migration state after military upload: {len(pre_migration_records)} DynamoDB records, '
        f'{len(pre_migration_s3_objects)} S3 objects'
    )

    jurisdiction = license_record['jurisdiction']
    test_staff_user_sub = create_test_staff_user(
        email=TEST_STAFF_USER_EMAIL,
        compact=compact,
        jurisdiction=jurisdiction,
        permissions={'actions': {'admin'}, 'jurisdictions': {jurisdiction: {'write', 'admin'}}},
    )
    staff_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
    client_headers, test_app_client_id = _create_test_app_client_headers(TEST_APP_CLIENT_NAME, compact, jurisdiction)
    try:
        # Step 3 + 4: migrate to the corrected SSN and verify everything moved
        migrated_provider_id = _migrate_test_provider_to_ssn(
            staff_headers=staff_headers,
            client_headers=client_headers,
            provider_data=provider_data,
            license_record=license_record,
            current_provider_id=original_provider_id,
            corrected_ssn=FULL_MIGRATION_CORRECTED_SSN,
            previous_ssn=config.test_provider_mock_ssn,
        )
        migrated_records = _get_provider_dynamo_records(compact, migrated_provider_id)
        _verify_all_records_migrated(
            source_records=pre_migration_records,
            source_provider_id=original_provider_id,
            target_records=migrated_records,
            target_provider_id=migrated_provider_id,
        )
        if not any(
            record['type'] == 'providerUpdate' and record.get('updateType') == 'ssnCorrection'
            for record in migrated_records
        ):
            raise SmokeTestFailureException('No ssnCorrection provider update record found after migration')
        _verify_all_s3_objects_migrated(
            source_objects=pre_migration_s3_objects, compact=compact, target_provider_id=migrated_provider_id
        )

        # Step 5: roundtrip back to the original SSN and verify everything returned home
        returned_provider_id = _migrate_test_provider_to_ssn(
            staff_headers=staff_headers,
            client_headers=client_headers,
            provider_data=provider_data,
            license_record=license_record,
            current_provider_id=migrated_provider_id,
            corrected_ssn=config.test_provider_mock_ssn,
            previous_ssn=FULL_MIGRATION_CORRECTED_SSN,
        )
        if returned_provider_id != original_provider_id:
            raise SmokeTestFailureException(
                f'Roundtrip migration did not return to the original provider id. '
                f'Expected {original_provider_id}, got {returned_provider_id}'
            )
        _verify_all_records_migrated(
            source_records=pre_migration_records,
            source_provider_id=original_provider_id,
            target_records=_get_provider_dynamo_records(compact, original_provider_id),
            target_provider_id=original_provider_id,
        )
        _verify_all_s3_objects_migrated(
            source_objects=pre_migration_s3_objects, compact=compact, target_provider_id=original_provider_id
        )
        print('Roundtrip migration completed; all records and documents are back under the original provider id')
    finally:
        # Restore the shared test provider account no matter what state the test failed in: point the
        # Cognito user at whichever provider id currently holds the provider's records
        current_ids = _query_provider_ids_by_name(
            staff_headers, compact, provider_data['givenName'], provider_data['familyName']
        )
        restore_provider_id = current_ids[0] if current_ids else original_provider_id
        _restore_test_provider_account(compact, restore_provider_id, baseline_provider_record)
        delete_test_staff_user(TEST_STAFF_USER_EMAIL, user_sub=test_staff_user_sub, compact=compact)
        delete_test_app_client(test_app_client_id)

    # Final verification: the restored account can log in and sees the original provider id
    restored_provider_data = call_provider_users_me_endpoint()
    if restored_provider_data['providerId'] != original_provider_id:
        raise SmokeTestFailureException(
            f'Restored test provider account resolves to provider id {restored_provider_data["providerId"]}; '
            f'expected {original_provider_id}'
        )
    print('Test provider account restored and verified. Full migration roundtrip smoke test passed.')


# -------------------------------------------------------------------------------------------------
# Partial migration test
# -------------------------------------------------------------------------------------------------
def _build_partial_test_license(license_type: str, ssn: str, previous_ssn: str | None = None) -> dict:
    license_record = {
        'ssn': ssn,
        'npi': '2222222222',
        'licenseNumber': f'SSN-MIG-{("OT" if license_type == OT_LICENSE_TYPE else "OTA")}',
        'givenName': PARTIAL_MIGRATION_GIVEN_NAME,
        'familyName': PARTIAL_MIGRATION_FAMILY_NAME,
        'dateOfBirth': '1990-01-01',
        'dateOfIssuance': '2020-01-01',
        'dateOfExpiration': '2050-01-01',
        'licenseType': license_type,
        'licenseStatus': 'active',
        'compactEligibility': 'eligible',
        'homeAddressStreet1': '123 Test Street',
        'homeAddressCity': 'Omaha',
        'homeAddressState': 'ne',
        'homeAddressPostalCode': '68001',
    }
    if previous_ssn is not None:
        license_record['previousSSN'] = previous_ssn
    return license_record


def _get_license_types_in_partition(compact: str, provider_id: str) -> set[str]:
    return {
        record['licenseType']
        for record in _get_provider_dynamo_records(compact, provider_id)
        if record['type'] == 'license'
    }


def test_partial_ssn_migration():
    """
    Partial migration: a mock practitioner with OT and OTA licenses under one (incorrect) SSN has only the
    OT license's SSN corrected. The OT license must move to a new provider id while the OTA license and the
    old provider record remain in place.

    Step 1: Upload OT + OTA licenses under the same mock SSN and wait for the provider to be created.
    Step 2: Re-upload the OT license with a corrected SSN and previousSSN set to the original mock SSN.
    Step 3: Verify the OT license now lives under a new provider id with its own top-level provider record,
            while the OTA license and provider record remain under the old provider id.
    Step 4: Clean up all DynamoDB records for both provider ids.
    """
    test_staff_user_sub = create_test_staff_user(
        email=TEST_STAFF_USER_EMAIL,
        compact=PARTIAL_MIGRATION_COMPACT,
        jurisdiction=PARTIAL_MIGRATION_JURISDICTION,
        permissions={'actions': {'admin'}, 'jurisdictions': {PARTIAL_MIGRATION_JURISDICTION: {'write', 'admin'}}},
    )
    staff_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)
    client_headers, test_app_client_id = _create_test_app_client_headers(
        TEST_APP_CLIENT_NAME, PARTIAL_MIGRATION_COMPACT, PARTIAL_MIGRATION_JURISDICTION
    )
    old_provider_id = None
    new_provider_id = None
    try:
        # Step 1: create the mock practitioner with two license types under the same (incorrect) SSN
        _upload_license_records(
            client_headers,
            PARTIAL_MIGRATION_COMPACT,
            PARTIAL_MIGRATION_JURISDICTION,
            [
                _build_partial_test_license(OT_LICENSE_TYPE, PARTIAL_MIGRATION_ORIGINAL_SSN),
                _build_partial_test_license(OTA_LICENSE_TYPE, PARTIAL_MIGRATION_ORIGINAL_SSN),
            ],
        )
        old_provider_id = wait_for_provider_creation(
            staff_headers, PARTIAL_MIGRATION_COMPACT, PARTIAL_MIGRATION_GIVEN_NAME, PARTIAL_MIGRATION_FAMILY_NAME
        )
        _wait_until(
            f'both license records to exist under provider {old_provider_id}',
            lambda: (
                _get_license_types_in_partition(PARTIAL_MIGRATION_COMPACT, old_provider_id)
                == {OT_LICENSE_TYPE, OTA_LICENSE_TYPE}
            ),
        )

        # Step 2: correct the SSN on the OT license only
        _upload_license_records(
            client_headers,
            PARTIAL_MIGRATION_COMPACT,
            PARTIAL_MIGRATION_JURISDICTION,
            [
                _build_partial_test_license(
                    OT_LICENSE_TYPE, PARTIAL_MIGRATION_CORRECTED_SSN, previous_ssn=PARTIAL_MIGRATION_ORIGINAL_SSN
                )
            ],
        )

        # Step 3: wait for the OT license to arrive under a new provider id
        def _find_new_provider_id():
            provider_ids = _query_provider_ids_by_name(
                staff_headers, PARTIAL_MIGRATION_COMPACT, PARTIAL_MIGRATION_GIVEN_NAME, PARTIAL_MIGRATION_FAMILY_NAME
            )
            return next((provider_id for provider_id in provider_ids if provider_id != old_provider_id), None)

        new_provider_id = _wait_until('the OT license to migrate to a new provider id', _find_new_provider_id)

        old_provider_records = _get_provider_dynamo_records(PARTIAL_MIGRATION_COMPACT, old_provider_id)
        old_record_types = {record['type'] for record in old_provider_records}
        old_license_types = {record['licenseType'] for record in old_provider_records if record['type'] == 'license'}
        if 'provider' not in old_record_types:
            raise SmokeTestFailureException(
                'The old provider record was deleted during a partial migration; it should have been preserved'
            )
        if old_license_types != {OTA_LICENSE_TYPE}:
            raise SmokeTestFailureException(
                f'Expected only the OTA license to remain under the old provider id; found: {old_license_types}'
            )
        print(f'Verified the OTA license and provider record remain under old provider {old_provider_id}')

        new_provider_records = _get_provider_dynamo_records(PARTIAL_MIGRATION_COMPACT, new_provider_id)
        new_record_types = {record['type'] for record in new_provider_records}
        new_license_types = {record['licenseType'] for record in new_provider_records if record['type'] == 'license'}
        if 'provider' not in new_record_types:
            raise SmokeTestFailureException('No top-level provider record was created for the new provider id')
        if new_license_types != {OT_LICENSE_TYPE}:
            raise SmokeTestFailureException(
                f'Expected only the OT license under the new provider id; found: {new_license_types}'
            )
        print(f'Verified the OT license and a new provider record exist under new provider {new_provider_id}')
        print('Partial migration smoke test passed.')
    finally:
        # Step 4: clean up all DynamoDB records for the mock practitioner (the SSN table records cannot be
        # deleted by developers, and the fixed mock SSNs make reruns reuse the same mappings)
        for provider_id in (old_provider_id, new_provider_id):
            if provider_id:
                cleanup_test_provider_records(provider_id, PARTIAL_MIGRATION_COMPACT)
        delete_test_staff_user(TEST_STAFF_USER_EMAIL, user_sub=test_staff_user_sub, compact=PARTIAL_MIGRATION_COMPACT)
        delete_test_app_client(test_app_client_id)


if __name__ == '__main__':
    load_smoke_test_env()
    test_full_ssn_migration_roundtrip()
    test_partial_ssn_migration()
