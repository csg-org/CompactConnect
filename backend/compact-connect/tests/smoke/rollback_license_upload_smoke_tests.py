# ruff: noqa: T201  we use print statements for smoke testing
#!/usr/bin/env python3
import json
import time
from datetime import UTC, datetime, timedelta

import boto3
import requests
from config import config, logger
from smoke_common import (
    SmokeTestFailureException,
    create_test_staff_user,
    delete_test_staff_user,
    get_api_base_url,
    get_provider_user_records,
    get_staff_user_auth_headers,
    load_smoke_test_env,
)

COMPACT = 'aslp'
JURISDICTION = 'ne'
TEST_STAFF_USER_EMAIL = 'testStaffUserLicenseRollback@smokeTestFakeEmail.com'

# Test configuration
NUM_LICENSES_TO_UPLOAD = 1000
BATCH_SIZE = 100  # Upload in batches of 100 to avoid timeouts


def upload_test_license_batch(
    staff_headers: dict, batch_start_index: int, batch_size: int
):
    """
    Upload a batch of test license records.

    :param staff_headers: Authentication headers for staff user
    :param batch_start_index: Starting index for this batch
    :param batch_size: Number of licenses to upload in this batch
    :return: List of license records that were uploaded
    """
    licenses_batch = []

    for i in range(batch_start_index, batch_start_index + batch_size):
        # Generate unique data for each license
        license_data = {
            'licenseNumber': f'ROLLBACK-TEST-{i:04d}',
            'homeAddressPostalCode': '68001',
            'givenName': f'TestProvider{i}',
            'familyName': f'RollbackTest{i:04d}',
            'homeAddressStreet1': '123 Test Street',
            'dateOfBirth': '1985-01-01',
            'dateOfIssuance': '2020-01-01',
            'ssn': f'500-50-{i:04d}',  # Incrementing SSN with padded zeros
            'licenseType': 'audiologist',
            'dateOfExpiration': '2050-12-10',
            'homeAddressState': 'NE',
            'homeAddressCity': 'Omaha',
            'compactEligibility': 'eligible',
            'licenseStatus': 'active',
        }
        licenses_batch.append(license_data)

    # Upload the batch
    logger.info(
        f'Uploading batch of {len(licenses_batch)} licenses (indices {batch_start_index}-{batch_start_index + batch_size - 1})'
    )

    post_response = requests.post(
        url=f'{get_api_base_url()}/v1/compacts/{COMPACT}/jurisdictions/{JURISDICTION}/licenses',
        headers=staff_headers,
        json=licenses_batch,
        timeout=60,  # Longer timeout for batch uploads
    )

    if post_response.status_code != 200:
        raise SmokeTestFailureException(
            f'Failed to upload license batch {batch_start_index}. Response: {post_response.json()}'
        )

    logger.info(f'Successfully uploaded batch {batch_start_index}-{batch_start_index + batch_size - 1}')
    return licenses_batch


def upload_test_licenses(staff_headers: dict, num_licenses: int, batch_size: int):
    """
    Upload test license records in batches.

    :param staff_headers: Authentication headers for staff user
    :param num_licenses: Total number of licenses to upload
    :param batch_size: Number of licenses per batch
    :return: Tuple of (all uploaded license data, upload start time, upload end time)
    """
    upload_start_time = datetime.now(tz=UTC)
    all_licenses = []

    logger.info(f'Starting upload of {num_licenses} test licenses in batches of {batch_size}')

    for batch_start in range(0, num_licenses, batch_size):
        current_batch_size = min(batch_size, num_licenses - batch_start)
        batch_licenses = upload_test_license_batch(staff_headers, batch_start, current_batch_size)
        all_licenses.extend(batch_licenses)

        # Small delay between batches to avoid rate limiting
        if batch_start + current_batch_size < num_licenses:
            time.sleep(2)

    # wait for several minutes for all licenses to propagate in the system

    upload_end_time = datetime.now(tz=UTC)
    logger.info(f'Completed upload of {len(all_licenses)} licenses')

    return all_licenses, upload_start_time, upload_end_time


def wait_for_all_providers_created(staff_headers: dict, expected_count: int, max_wait_time: int = 900):
    """
    Wait for all provider records to be created from uploaded licenses.

    :param staff_headers: Authentication headers for staff user
    :param expected_count: Expected number of providers to be created
    :param max_wait_time: Maximum time to wait in seconds (default: 900 = 15 minutes)
    :return: List of provider IDs that were created
    """
    logger.info(f'Waiting for {expected_count} provider records to be created...')

    start_time = time.time()
    check_interval = 30

    # Query using the common family name prefix 'RollbackTest'
    # The API will return all providers with family names starting with this prefix
    base_query_body = {
        'query': {'familyName': 'RollbackTest'},
        'pagination': {
            'pageSize': 1000  # Maximum page size to minimize number of requests
        },
    }

    while time.time() - start_time < max_wait_time:
        all_provider_ids = []
        last_key = None
        page_num = 1

        # Collect all providers across all pages
        while True:
            query_body = base_query_body.copy()
            if last_key:
                query_body['pagination']['lastKey'] = last_key

            query_response = requests.post(
                url=f'{get_api_base_url()}/v1/compacts/{COMPACT}/providers/query',
                headers=staff_headers,
                json=query_body,
                timeout=30,
            )

            if query_response.status_code != 200:
                logger.warning(f'Query failed with status {query_response.status_code}. Retrying...')
                break

            response_data = query_response.json()
            providers = response_data.get('providers', [])
            pagination = response_data.get('pagination', {})

            # Collect provider IDs from this page
            page_provider_ids = [p['providerId'] for p in providers]
            all_provider_ids.extend(page_provider_ids)

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
            f'Found {num_found}/{expected_count} providers with family name prefix "RollbackTest" '
            f'(across {page_num} pages)'
        )

        if num_found >= expected_count:
            logger.info(f'All {expected_count} providers found!')
            return all_provider_ids[:expected_count]  # Return only the expected count

        elapsed = time.time() - start_time
        if elapsed < max_wait_time:
            logger.info(f'Waiting {check_interval}s for remaining providers... (elapsed: {elapsed:.1f}s)')
            time.sleep(check_interval)

    # Timeout reached - make one final query to get the latest results
    logger.warning(f'Timeout reached after {max_wait_time}s. Making final query to collect all available providers.')

    all_provider_ids = []
    last_key = None
    page_num = 1

    while True:
        query_body = base_query_body.copy()
        if last_key:
            query_body['pagination']['lastKey'] = last_key

        query_response = requests.post(
            url=f'{get_api_base_url()}/v1/compacts/{COMPACT}/providers/query',
            headers=staff_headers,
            json=query_body,
            timeout=30,
        )

        if query_response.status_code != 200:
            logger.warning(f'Final query failed with status {query_response.status_code}')
            break

        response_data = query_response.json()
        providers = response_data.get('providers', [])
        pagination = response_data.get('pagination', {})

        page_provider_ids = [p['providerId'] for p in providers]
        all_provider_ids.extend(page_provider_ids)

        logger.info(f'Final query page {page_num}: Found {len(page_provider_ids)} providers')

        last_key = pagination.get('lastKey')
        if not last_key:
            break

        page_num += 1

    logger.warning(f'Final count: {len(all_provider_ids)}/{expected_count} providers found')
    return all_provider_ids


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
        'startDateTime': start_datetime.isoformat().replace('+00:00', 'Z'),
        'endDateTime': end_datetime.isoformat().replace('+00:00', 'Z'),
        'executionName': execution_name,
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

    logger.info(f'Waiting for step function to complete...')
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
        elif status in ['FAILED', 'TIMED_OUT', 'ABORTED']:
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
    :param bucket_name: S3 bucket name
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


def verify_rollback_results(results: dict, expected_provider_count: int):
    """
    Verify the rollback results match expected format and counts.

    :param results: Rollback results from S3
    :param expected_provider_count: Expected number of providers rolled back
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

    # Verify all providers were reverted (none skipped or failed)
    if num_skipped > 0:
        logger.error(f'Found {num_skipped} skipped providers:')
        for detail in skipped[:5]:  # Show first 5
            logger.error(f'Details for skipped provider: {detail["providerId"]}', skipped=detail)
        raise SmokeTestFailureException(f'Expected 0 skipped providers but found {num_skipped}')

    if num_failed > 0:
        logger.error(f'Found {num_failed} failed providers:')
        for detail in failed[:5]:  # Show first 5
            logger.error(f'Details for failed provider: {detail["providerId"]}', failed=detail)
        raise SmokeTestFailureException(f'Expected 0 failed providers but found {num_failed}')

    # Verify we got the expected number of reverted providers
    if num_reverted != expected_provider_count:
        logger.warning(f'Expected {expected_provider_count} reverted providers but found {num_reverted}')

    # Verify the  reverted provider has the expected structure
    for i, summary in enumerate(reverted):
        if 'providerId' not in summary:
            raise SmokeTestFailureException(f'Reverted provider summary {i} missing providerId')
        if 'licensesReverted' not in summary:
            raise SmokeTestFailureException(f'Reverted provider summary {i} missing licensesReverted')

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
    1. Upload 1,000 test license records
    2. Wait for all providers to be created
    3. Start rollback step function
    4. Wait for step function completion
    5. Retrieve and verify results from S3
    6. Verify providers were deleted from database
    """
    # Get environment configuration
    step_function_arn = config.license_upload_rollback_step_function_arn

    if not step_function_arn:
        raise SmokeTestFailureException('CC_TEST_ROLLBACK_STEP_FUNCTION_ARN environment variable not set')

    staff_headers = get_staff_user_auth_headers(TEST_STAFF_USER_EMAIL)

    # Step 1: Upload test licenses
    logger.info('=' * 80)
    logger.info('STEP 1: Uploading test licenses')
    logger.info('=' * 80)

    uploaded_licenses, upload_start_time, upload_end_time = upload_test_licenses(
        staff_headers,
        NUM_LICENSES_TO_UPLOAD,
        BATCH_SIZE,
    )

    logger.info(f'Upload time window: {upload_start_time.isoformat()} to {upload_end_time.isoformat()}')

    # Step 2: Wait for providers to be created
    logger.info('=' * 80)
    logger.info('STEP 2: Waiting for provider records to be created')
    logger.info('=' * 80)

    provider_ids = wait_for_all_providers_created(staff_headers, len(uploaded_licenses))

    logger.info(f'Found {len(provider_ids)} provider records')

    # Step 3: Start rollback step function
    logger.info('=' * 80)
    logger.info('STEP 3: Starting rollback step function')
    logger.info('=' * 80)

    # Add buffer to time window to ensure we catch all uploads
    rollback_start = upload_start_time - timedelta(minutes=5)
    rollback_end = upload_end_time + timedelta(minutes=5)

    execution_arn = start_rollback_step_function(
        step_function_arn=step_function_arn,
        compact=COMPACT,
        jurisdiction=JURISDICTION,
        start_datetime=rollback_start,
        end_datetime=rollback_end,
    )

    # Step 4: Wait for step function completion
    logger.info('=' * 80)
    logger.info('STEP 4: Waiting for step function to complete')
    logger.info('=' * 80)

    status, output = wait_for_step_function_completion(execution_arn)

    logger.info(f'Step function output: {json.dumps(output, indent=2)}')

    # Step 5: Retrieve and verify results from S3
    logger.info('=' * 80)
    logger.info('STEP 5: Retrieving and verifying results from S3')
    logger.info('=' * 80)

    results_s3_key = output.get('resultsS3Key')
    if not results_s3_key:
        raise SmokeTestFailureException('No resultsS3Key in step function output')

    results = get_rollback_results_from_s3(results_s3_key)

    verify_rollback_results(results, len(provider_ids))

    # Step 6: Verify providers deleted from database
    logger.info('=' * 80)
    logger.info('STEP 6: Verifying providers were deleted from database')
    logger.info('=' * 80)

    verify_providers_deleted_from_database(results, COMPACT)

    logger.info('=' * 80)
    logger.info('✅ ALL TESTS PASSED')
    logger.info('=' * 80)


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
