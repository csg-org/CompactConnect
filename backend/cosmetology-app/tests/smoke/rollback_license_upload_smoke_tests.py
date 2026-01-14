# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
import json
import time
from datetime import UTC, datetime, timedelta

import boto3
import requests
from config import config, logger
from smoke_common import (
    LicenseData,
    LicenseUpdateData,
    SmokeTestFailureException,
    create_test_app_client,
    create_test_staff_user,
    delete_test_app_client,
    delete_test_staff_user,
    get_api_base_url,
    get_client_auth_headers,
    get_provider_user_records,
    get_staff_user_auth_headers,
    load_smoke_test_env,
)

COMPACT = 'coun'
JURISDICTION = 'ne'
TEST_STAFF_USER_EMAIL = 'testStaffUserLicenseRollback@smokeTestFakeEmail.com'
TEST_APP_CLIENT_NAME = 'test-license-rollback-client'

LICENSE_TYPE = 'licensed professional counselor'

# Test configuration
NUM_LICENSES_TO_UPLOAD = 300
BATCH_SIZE = 100  # Upload in batches of 100

# Global list to track all provider IDs for cleanup
ALL_PROVIDER_IDS = []


def upload_test_license_batch(
    auth_headers: dict, batch_start_index: int, batch_size: int, street_address: str = '123 Test Street'
):
    """
    Upload a batch of test license records.

    :param auth_headers: Authentication headers for app client
    :param batch_start_index: Starting index for this batch
    :param batch_size: Number of licenses to upload in this batch
    :param street_address: Street address to use
    :return: List of license records that were uploaded
    """
    licenses_batch = []

    for i in range(batch_start_index, batch_start_index + batch_size):
        # Generate unique data for each license
        license_data = {
            'licenseNumber': f'ROLLBACK-TEST-{i:04d}',
            'homeAddressPostalCode': '68001',
            'givenName': f'TestProvider{i:04d}',
            # keep the family name consistent so we can query for all the providers which requires an exact
            # match on the family name
            'familyName': 'RollbackTest',
            'homeAddressStreet1': street_address,
            'dateOfBirth': '1985-01-01',
            'dateOfIssuance': '2020-01-01',
            'ssn': f'999-50-{i:04d}',  # Incrementing SSN with padded zeros
            'licenseType': LICENSE_TYPE,
            'dateOfExpiration': '2050-12-10',
            'homeAddressState': 'NE',
            'homeAddressCity': 'Omaha',
            'compactEligibility': 'eligible',
            'licenseStatus': 'active',
        }
        licenses_batch.append(license_data)

    # Upload the batch
    logger.info(
        f'Uploading batch of {len(licenses_batch)} licenses'
        f' (indices {batch_start_index}-{batch_start_index + batch_size - 1})'
    )

    post_response = requests.post(
        url=f'{config.state_api_base_url}/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/licenses',
        headers=auth_headers,
        json=licenses_batch,
        timeout=60,  # Longer timeout for batch uploads
    )

    if post_response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to upload license batch {batch_start_index}. Response: {post_response.json()}'
        )

    logger.info(f'Successfully uploaded batch {batch_start_index}-{batch_start_index + batch_size - 1}')
    return licenses_batch


def upload_test_licenses(
    auth_headers: dict, num_licenses: int, batch_size: int, street_address: str = '123 Test Street'
):
    """
    Upload test license records in batches.

    :param auth_headers: Authentication headers for app client
    :param num_licenses: Total number of licenses to upload
    :param batch_size: Number of licenses per batch
    :param street_address: Street address to use
    :return: Tuple of (all uploaded license data, upload start time, upload end time)
    """
    all_licenses = []

    logger.info(f'Starting upload of {num_licenses} test licenses in batches of {batch_size}')

    for batch_start in range(0, num_licenses, batch_size):
        current_batch_size = min(batch_size, num_licenses - batch_start)
        batch_licenses = upload_test_license_batch(auth_headers, batch_start, current_batch_size, street_address)
        all_licenses.extend(batch_licenses)

        # Small delay between batches to avoid rate limiting
        if batch_start + current_batch_size < num_licenses:
            time.sleep(2)

    # wait for several minutes for all licenses to propagate in the system
    logger.info(f'Completed upload of {len(all_licenses)} licenses')

    return all_licenses


def verify_license_update_records_created(provider_ids, retry_count: int = 0):
    """
    Checks all provider ids for license update records, if none are found, adds to list to retry
    and retries after a delay
    :param provider_ids: List of provider IDs to check
    :param retry_count: Current retry count
    :return: None
    """
    provider_ids_to_retry = []
    for provider_id in provider_ids:
        provider_user_records = get_provider_user_records(COMPACT, provider_id)
        if len(provider_user_records.get_all_license_update_records()) == 0:
            logger.info(f'no license update records found for provider {provider_id}. Will retry.')
            provider_ids_to_retry.append(provider_id)

    if provider_ids_to_retry:
        if retry_count >= 3:
            raise SmokeTestFailureException(
                f'failed to find license update records for {len(provider_ids_to_retry)} providers after 3 retries'
            )
        time.sleep(10)
        logger.info(f'retrying {len(provider_ids_to_retry)} providers after 10 seconds...')
        verify_license_update_records_created(provider_ids_to_retry, retry_count + 1)
    else:
        logger.info('all license update records found')


def wait_for_all_providers_created(staff_headers: dict, expected_count: int, max_wait_time: int = 120):
    """
    Wait for all provider records to be created from uploaded licenses.

    :param staff_headers: Authentication headers for staff user
    :param expected_count: Expected number of providers to be created
    :param max_wait_time: Maximum time to wait in seconds (default: 900 = 15 minutes)
    :return: List of provider IDs that were created
    """
    logger.info(f'Waiting for {expected_count} provider records to be created...')

    start_time = time.time()
    check_interval = 5

    # Query using the common family name prefix 'RollbackTest'
    # The API will return all providers with family names starting with this prefix

    last_key = None
    page_num = 1
    all_provider_ids: set[str] = set()
    while time.time() - start_time < max_wait_time:
        # Collect all providers across all pages
        while True:
            query_body = {
                'query': {'familyName': 'RollbackTest'},
                'pagination': {'pageSize': 100},
            }
            if last_key:
                query_body['pagination']['lastKey'] = last_key

            query_response = requests.post(
                url=f'{get_api_base_url()}/v1/compacts/{COMPACT}/providers/query',
                headers=staff_headers,
                json=query_body,
                timeout=30,
            )

            if query_response.status_code != 200:
                logger.warning(
                    f'Query failed with status {query_response.status_code}: {query_response.json()} Retrying...'
                )
                break

            response_data = query_response.json()
            providers = response_data.get('providers', [])
            pagination = response_data.get('pagination', {})

            # Collect provider IDs from this page and add to set
            page_provider_ids = [p['providerId'] for p in providers]
            all_provider_ids.update(page_provider_ids)

            logger.info(
                f'Page {page_num}: Found {len(page_provider_ids)} providers '
                f'(total: {len(all_provider_ids)}/{expected_count})'
            )

            # Check if there are more pages
            last_key = pagination.get('lastKey')
            if not last_key:
                # No more pages
                break

            page_num += 1

        num_found = len(all_provider_ids)
        logger.info(
            f'Found {num_found}/{expected_count} providers with family name "RollbackTest" (across {page_num} pages)'
        )

        if num_found >= expected_count:
            logger.info(f'All {expected_count} providers found!')
            return list(all_provider_ids)  # Return only the expected count

        elapsed = time.time() - start_time
        if elapsed < max_wait_time:
            logger.info(f'Waiting {check_interval}s for remaining providers... (elapsed: {elapsed:.1f}s)')
            time.sleep(check_interval)

    # Timeout reached - make one final query to get the latest results
    raise SmokeTestFailureException(f'Timeout reached waiting for providers after {max_wait_time}s.')


def start_rollback_step_function(
    step_function_arn: str,
    compact: str,
    jurisdiction: str,
    start_datetime: datetime,
    end_datetime: datetime,
):
    """
    Start the license upload rollback step function.

    :param step_function_arn: ARN of the step function
    :param compact: Compact abbreviation
    :param jurisdiction: Jurisdiction abbreviation
    :param start_datetime: Start of rollback time window
    :param end_datetime: End of rollback time window
    :return: Execution ARN
    """
    sfn_client = boto3.client('stepfunctions')

    # Generate unique execution name
    execution_name = f'smoke-test-rollback-{int(datetime.now(tz=UTC).timestamp())}'

    input_data = {
        'compact': compact,
        'jurisdiction': jurisdiction,
        'startDateTime': start_datetime.isoformat(),
        'endDateTime': end_datetime.isoformat(),
        'rollbackReason': 'Smoke test validation of rollback functionality',
    }

    logger.info(f'Starting step function execution: {execution_name}')
    logger.info(f'Input: {json.dumps(input_data, indent=2)}')

    response = sfn_client.start_execution(
        stateMachineArn=step_function_arn,
        name=execution_name,
        input=json.dumps(input_data),
    )

    execution_arn = response['executionArn']
    logger.info(f'Step function started. Execution ARN: {execution_arn}')

    return execution_arn


def wait_for_step_function_completion(execution_arn: str, max_wait_time: int = 3600):
    """
    Poll the step function until it completes.

    :param execution_arn: ARN of the step function execution
    :param max_wait_time: Maximum time to wait in seconds (default: 3600 = 1 hour)
    :return: Final execution status and output
    """
    sfn_client = boto3.client('stepfunctions')

    logger.info('Waiting for step function to complete...')
    start_time = time.time()
    check_interval = 30

    while time.time() - start_time < max_wait_time:
        response = sfn_client.describe_execution(executionArn=execution_arn)

        status = response['status']
        logger.info(f'Step function status: {status}')

        if status == 'SUCCEEDED':
            output = json.loads(response['output'])
            elapsed = time.time() - start_time
            logger.info(f'Step function completed successfully after {elapsed:.1f}s')
            return status, output
        if status in ['FAILED', 'TIMED_OUT', 'ABORTED']:
            raise SmokeTestFailureException(
                f'Step function execution failed with status: {status}. '
                f'Error: {response.get("error", "N/A")}, Cause: {response.get("cause", "N/A")}'
            )

        # Still running
        time.sleep(check_interval)

    raise SmokeTestFailureException(f'Step function did not complete within {max_wait_time}s timeout')


def get_rollback_results_from_s3(results_s3_key: str):
    """
    Retrieve rollback results from S3.

    :param results_s3_key: S3 URI or key to the results file
    :return: Parsed results data
    """
    s3_client = boto3.client('s3')

    # Format: s3://bucket-name/key
    parts = results_s3_key.replace('s3://', '').split('/', 1)
    bucket_name = parts[0]
    key = parts[1]

    logger.info(f'Retrieving results from S3: {bucket_name}/{key}')

    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    results_json = response['Body'].read().decode('utf-8')
    results = json.loads(results_json)

    logger.info('Retrieved results from S3')
    return results


def create_privilege_for_provider(provider_id: str, compact: str):
    """
    Manually create a privilege record for a provider to test skip conditions.

    :param provider_id: The provider ID to create privilege for
    :param compact: The compact abbreviation
    """
    from datetime import date

    # Create a privilege record for a different jurisdiction (e.g., 'co' for Colorado)
    privilege_jurisdiction = 'co'
    license_type_abbr = 'lpc'

    privilege_record = {
        'pk': f'{compact}#PROVIDER#{provider_id}',
        'sk': f'{compact}#PROVIDER#privilege/{privilege_jurisdiction}/{license_type_abbr}#',
        'type': 'privilege',
        'providerId': provider_id,
        'compact': compact,
        'jurisdiction': privilege_jurisdiction,
        'licenseJurisdiction': JURISDICTION,
        'licenseType': LICENSE_TYPE,
        'dateOfIssuance': datetime.now(tz=UTC).isoformat(),
        'dateOfRenewal': datetime.now(tz=UTC).isoformat(),
        'dateOfExpiration': date(2050, 12, 10).isoformat(),
        'dateOfUpdate': datetime.now(tz=UTC).isoformat(),
        'privilegeId': f'{license_type_abbr.upper()}-{privilege_jurisdiction.upper()}-12345',
        'administratorSetStatus': 'active',
        'compactTransactionId': 'test-transaction-12345',
        'compactTransactionIdGSIPK': f'COMPACT#{compact}#TX#test-transaction-12345#',
    }

    config.provider_user_dynamodb_table.put_item(Item=privilege_record)
    logger.info(f'Created privilege record for provider {provider_id}')


def create_encumbrance_update_for_provider(provider_id: str, compact: str, license_jurisdiction: str):
    """
    Manually create a license encumbrance update record to test skip conditions.

    :param provider_id: The provider ID
    :param compact: The compact abbreviation
    :param license_jurisdiction: The jurisdiction of the license
    """

    license_type_abbr = 'lpc'
    # Use current time or specified time
    now = datetime.now(tz=UTC)

    # First, query the actual license record to get the previous state
    license_sk = f'{compact}#PROVIDER#license/{license_jurisdiction}/{license_type_abbr}#'

    try:
        response = config.provider_user_dynamodb_table.get_item(
            Key={'pk': f'{compact}#PROVIDER#{provider_id}', 'sk': license_sk}
        )
        license_record_item = response.get('Item')

        if not license_record_item:
            raise SmokeTestFailureException(f'License record not found for provider {provider_id}')

        # Load the license record using the schema to get properly typed data
        license_record = LicenseData.from_database_record(license_record_item)

    except Exception as e:
        logger.error(f'Failed to retrieve license record for provider {provider_id}: {str(e)}')
        raise

    # Create a license encumbrance update record using LicenseUpdateData
    # This ensures proper schema validation and field generation (including SK hash)
    update_data = LicenseUpdateData.create_new(
        {
            'type': 'licenseUpdate',
            'updateType': 'encumbrance',
            'providerId': provider_id,
            'compact': compact,
            'jurisdiction': license_jurisdiction,
            'licenseType': LICENSE_TYPE,
            'createDate': now,
            'effectiveDate': now,
            'previous': license_record.to_dict(),
            'updatedValues': {
                'encumberedStatus': 'encumbered',
            },
        }
    )

    # Serialize to database record format
    update_record = update_data.serialize_to_database_record()

    config.provider_user_dynamodb_table.put_item(Item=update_record)
    logger.info(f'Created encumbrance update record for provider {provider_id} with createDate {now.isoformat()}')


def delete_all_provider_records(provider_ids: list[str], compact: str):
    """
    Delete all records for the given provider IDs.

    :param provider_ids: List of provider IDs to delete
    :param compact: The compact abbreviation
    """
    logger.info(f'Starting cleanup of {len(provider_ids)} provider records...')

    for i, provider_id in enumerate(provider_ids):
        if i % 100 == 0:
            logger.info(f'Cleaned up {i}/{len(provider_ids)} provider records')

        try:
            # Query all records for this provider
            response = config.provider_user_dynamodb_table.query(
                KeyConditionExpression='pk = :pk',
                ExpressionAttributeValues={':pk': f'{compact}#PROVIDER#{provider_id}'},
            )

            # Delete all records in batches
            with config.provider_user_dynamodb_table.batch_writer() as batch:
                for item in response.get('Items', []):
                    batch.delete_item(Key={'pk': item['pk'], 'sk': item['sk']})
        except Exception as e:  # noqa: BLE001
            logger.warning(f'Failed to delete records for provider {provider_id}: {str(e)}')

    logger.info(f'✅ Completed cleanup of {len(provider_ids)} provider records')


def verify_rollback_results(results: dict, expected_provider_count: int, expected_skipped_count: int = 0):
    """
    Verify the rollback results match expected format and counts.

    :param results: Rollback results from S3
    :param expected_provider_count: Expected number of providers rolled back (reverted)
    :param expected_skipped_count: Expected number of providers that should be skipped
    """
    logger.info('Verifying rollback results...')

    # Verify structure
    required_keys = ['revertedProviderSummaries', 'skippedProviderDetails', 'failedProviderDetails']
    for key in required_keys:
        if key not in results:
            raise SmokeTestFailureException(f'Missing required key in results: {key}')

    # Check counts
    reverted = results['revertedProviderSummaries']
    skipped = results['skippedProviderDetails']
    failed = results['failedProviderDetails']

    num_reverted = len(reverted)
    num_skipped = len(skipped)
    num_failed = len(failed)

    logger.info('Rollback summary:')
    logger.info(f'  - Reverted: {num_reverted}')
    logger.info(f'  - Skipped: {num_skipped}')
    logger.info(f'  - Failed: {num_failed}')

    # Verify skipped count matches expectation
    if num_skipped != expected_skipped_count:
        logger.error(f'Found {num_skipped} skipped providers, expected {expected_skipped_count}:')
        for detail in skipped[:5]:  # Show first 5
            logger.error(f'Details for skipped provider: {detail["providerId"]}', skipped=detail)
        raise SmokeTestFailureException(f'Expected {expected_skipped_count} skipped providers but found {num_skipped}')

    if num_failed > 0:
        logger.error(f'Found {num_failed} failed providers:')
        for detail in failed[:5]:  # Show first 5
            logger.error(f'Details for failed provider: {detail["providerId"]}', failed=detail)
        raise SmokeTestFailureException(f'Expected 0 failed providers but found {num_failed}')

    # Verify we got the expected number of reverted providers
    if num_reverted != expected_provider_count:
        logger.warning(f'Expected {expected_provider_count} reverted providers but found {num_reverted}')

    # Verify the reverted provider has the expected structure
    for i, summary in enumerate(reverted):
        if 'providerId' not in summary:
            raise SmokeTestFailureException(f'Reverted provider summary {i} missing providerId')
        if 'licensesReverted' not in summary:
            raise SmokeTestFailureException(f'Reverted provider summary {i} missing licensesReverted')
        if 'updatesDeleted' not in summary:
            raise SmokeTestFailureException(f'Reverted provider summary {i} missing updatesDeleted')

        # Verify each license was deleted (not reverted to previous state)
        licenses_reverted = summary['licensesReverted']
        if len(licenses_reverted) != 1:
            raise SmokeTestFailureException(
                f'Expected 1 license reverted for provider {summary["providerId"]}, found {len(licenses_reverted)}'
            )

        license_action = licenses_reverted[0]['action']
        if license_action != 'DELETE':
            raise SmokeTestFailureException(
                f'Expected license action "DELETE" but found "{license_action}" for provider {summary["providerId"]}'
            )

        # Verify that update records were deleted (should have at least 1 from the re-upload)
        updates_deleted = summary['updatesDeleted']
        if len(updates_deleted) < 1:
            raise SmokeTestFailureException(
                f'Expected at least 1 update record deleted for provider {summary["providerId"]}, '
                f'found {len(updates_deleted)}'
            )

    logger.info('✅ Rollback results verification passed')


def verify_providers_deleted_from_database(results: dict, compact: str):
    """
    Verify that all provider records were actually deleted from DynamoDB.

    :param results: Rollback results containing provider IDs
    :param compact: Compact abbreviation
    """
    logger.info('Verifying providers were deleted from database...')

    reverted_summaries = results['revertedProviderSummaries']

    for i, summary in enumerate(reverted_summaries):
        if i % 100 == 0:
            logger.info(f'Verified deletion for {i}/{len(reverted_summaries)} providers')

        provider_id = summary['providerId']

        # Try to get provider records - should return empty or raise exception
        provider_user_records = get_provider_user_records(compact, provider_id)

        # Check if any records exist
        all_records = provider_user_records.provider_records
        if all_records:
            raise SmokeTestFailureException(
                f'Provider {provider_id} still has {len(all_records)} records in database after rollback'
            )

    logger.info(f'✅ Verified {len(reverted_summaries)} providers were deleted from database')


def rollback_license_upload_smoke_test():
    """
    Main smoke test for license upload rollback functionality.

    Steps:
    1. Upload test license records (first time)
    2. Upload test license records again with different address (creates update records)
    3. Wait for all providers to be created AND verify license update records exist in DynamoDB
    4. Store all provider IDs for cleanup
    5. Create privilege for first provider (should be skipped)
    6. Create encumbrance update for second provider (should be skipped)
    7. Start rollback step function
    8. Wait for step function completion
    9. Retrieve and verify results from S3
    10. Verify providers were deleted from database (except 2 skipped)
    11. Clean up remaining test records
    """
    global ALL_PROVIDER_IDS

    # Get environment configuration
    step_function_arn = config.license_upload_rollback_step_function_arn

    if not step_function_arn:
        raise SmokeTestFailureException('CC_TEST_ROLLBACK_STEP_FUNCTION_ARN environment variable not set')

    # staff user to query providers
    staff_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)

    # Create test app client for authentication
    client_credentials = create_test_app_client(TEST_APP_CLIENT_NAME, COMPACT, JURISDICTION)
    client_id = client_credentials['client_id']
    client_secret = client_credentials['client_secret']

    skipped_provider_ids = []

    try:
        # Get authentication headers using app client
        auth_headers = get_client_auth_headers(client_id, client_secret, COMPACT, JURISDICTION)

        # Step 1: Upload test licenses (first time)
        logger.info('=' * 80)
        logger.info('STEP 1: Uploading test licenses (first time)')
        logger.info('=' * 80)

        first_upload_start_time = datetime.now(tz=UTC)
        uploaded_licenses = upload_test_licenses(
            auth_headers,
            NUM_LICENSES_TO_UPLOAD,
            BATCH_SIZE,
            street_address='123 Test Street',
        )
        first_upload_end_time = datetime.now(tz=UTC)
        logger.info(
            f'First upload time window: {first_upload_start_time.isoformat()} to {first_upload_end_time.isoformat()}'
        )

        # Wait for first upload's license records to be created before second upload
        logger.info('=' * 80)
        logger.info('Waiting for first upload providers and license records to be created...')
        logger.info('=' * 80)
        time.sleep(10)
        wait_for_all_providers_created(staff_headers, len(uploaded_licenses))
        logger.info('✅ All first upload license records have been created')

        # Step 2: Upload test licenses again with different address to create update records
        logger.info('=' * 80)
        logger.info('STEP 2: Uploading test licenses again with different address (creates update records)')
        logger.info('=' * 80)

        upload_test_licenses(
            auth_headers,
            NUM_LICENSES_TO_UPLOAD,
            BATCH_SIZE,
            street_address='456 Updated Street',
        )

        logger.info('Second upload completed - update records should be created')

        # Step 3: Wait for providers to be created and update records to propagate
        logger.info('=' * 80)
        logger.info('STEP 3: Waiting for provider records and update records to be created')
        logger.info('=' * 80)

        provider_ids = wait_for_all_providers_created(staff_headers, len(uploaded_licenses))

        # Store all provider IDs globally for cleanup
        ALL_PROVIDER_IDS = provider_ids.copy()

        logger.info('Checking for license update records.')
        verify_license_update_records_created(provider_ids)
        # Capture end time after verifying update records exist
        second_upload_end_time = datetime.now(tz=UTC)

        logger.info(f'Found {len(provider_ids)} provider records')

        # Step 4: Create privilege for first provider (should be skipped in rollback)
        logger.info('=' * 80)
        logger.info('STEP 4: Creating privilege for first provider to test skip condition')
        logger.info('=' * 80)

        first_provider_id = provider_ids[0]
        create_privilege_for_provider(first_provider_id, COMPACT)
        skipped_provider_ids.append(first_provider_id)
        logger.info(f'Created privilege for provider {first_provider_id} - should be skipped in rollback')

        # Step 5: Create encumbrance update for second provider (should be skipped in rollback)
        logger.info('=' * 80)
        logger.info('STEP 5: Creating encumbrance update for second provider to test skip condition')
        logger.info('=' * 80)

        second_provider_id = provider_ids[1]
        create_encumbrance_update_for_provider(second_provider_id, COMPACT, JURISDICTION)
        skipped_provider_ids.append(second_provider_id)
        logger.info(f'Created encumbrance update for provider {second_provider_id} - should be skipped in rollback')

        # Brief wait to ensure the manually created records are written
        logger.info('Waiting briefly for test records to propagate...')
        time.sleep(5)

        # Step 6: Start rollback step function
        logger.info('=' * 80)
        logger.info('STEP 6: Starting rollback step function')
        logger.info('=' * 80)

        rollback_start = first_upload_start_time
        # Add buffer to end time window to ensure we catch all uploads
        rollback_end = second_upload_end_time + timedelta(minutes=5)

        execution_arn = start_rollback_step_function(
            step_function_arn=step_function_arn,
            compact=COMPACT,
            jurisdiction=JURISDICTION,
            start_datetime=rollback_start,
            end_datetime=rollback_end,
        )

        # Step 7: Wait for step function completion
        logger.info('=' * 80)
        logger.info('STEP 7: Waiting for step function to complete')
        logger.info('=' * 80)

        status, output = wait_for_step_function_completion(execution_arn)

        logger.info(f'Step function output: {json.dumps(output, indent=2)}')

        # Step 8: Retrieve and verify results from S3
        logger.info('=' * 80)
        logger.info('STEP 8: Retrieving and verifying results from S3')
        logger.info('=' * 80)

        results_s3_key = output.get('resultsS3Key')
        if not results_s3_key:
            raise SmokeTestFailureException('No resultsS3Key in step function output')

        results = get_rollback_results_from_s3(results_s3_key)

        # Expect all providers reverted except for the 2 skipped
        expected_reverted = NUM_LICENSES_TO_UPLOAD - 2
        expected_skipped = 2
        verify_rollback_results(results, expected_reverted, expected_skipped)

        # Step 9: Verify providers deleted from database (except the 2 skipped ones)
        logger.info('=' * 80)
        logger.info('STEP 9: Verifying providers were deleted from database')
        logger.info('=' * 80)

        verify_providers_deleted_from_database(results, COMPACT)

        # Step 10: Clean up the 2 skipped provider records
        logger.info('=' * 80)
        logger.info('STEP 10: Cleaning up skipped provider records')
        logger.info('=' * 80)

        delete_all_provider_records(skipped_provider_ids, COMPACT)

        logger.info('=' * 80)
        logger.info('✅ ALL TESTS PASSED')
        logger.info('=' * 80)
    except Exception as e:
        logger.error(f'Test failed: {str(e)}')
        # If test failed, we need to clean up all provider records
        if ALL_PROVIDER_IDS:
            logger.info('=' * 80)
            logger.info('CLEANUP: Test failed, cleaning up all provider records')
            logger.info('=' * 80)
            delete_all_provider_records(ALL_PROVIDER_IDS, COMPACT)
        raise
    finally:
        # Clean up the test app client
        delete_test_app_client(client_id)


if __name__ == '__main__':
    load_smoke_test_env()

    # Create staff user with permission to upload licenses and run rollback
    test_user_sub = create_test_staff_user(
        email=TEST_STAFF_USER_EMAIL,
        compact=COMPACT,
        jurisdiction=JURISDICTION,
        permissions={'actions': {'admin'}, 'jurisdictions': {JURISDICTION: {'write', 'admin'}}},
    )

    try:
        rollback_license_upload_smoke_test()
        logger.info('🎉 License upload rollback smoke test completed successfully!')
    except SmokeTestFailureException as e:
        logger.error(f'❌ License upload rollback smoke test failed: {str(e)}')
        raise
    except Exception as e:
        logger.error(f'❌ Unexpected error during smoke test: {str(e)}', exc_info=True)
        raise
    finally:
        # Clean up the test staff user
        delete_test_staff_user(TEST_STAFF_USER_EMAIL, user_sub=test_user_sub, compact=COMPACT)
