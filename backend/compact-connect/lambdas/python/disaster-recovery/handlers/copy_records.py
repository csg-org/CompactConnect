import json
import time
from base64 import b64decode, b64encode

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from cc_common.config import logger


def copy_records(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    As part of synchronizing tables during a DR event, we copy all records from the restored
    table (source) to the original table (destination) to complete the data synchronization.

    In the event that the copy process takes longer than the 15-minute time limit window for lambda, we return a
    'copyStatus' field of 'IN_PROGRESS', causing the step function to loop around and continue the copy process using
    the lastEvaluatedKey found in the response.
    If all the records have been copied, we return a 'copyStatus' of 'COMPLETE', causing the step function to
    complete the sync workflow.
    """
    start_time = time.time()
    max_execution_time = 12 * 60  # 12 minutes in seconds

    # Get source and destination table ARNs from event
    source_table_arn = event['sourceTableArn']
    destination_table_arn = event['destinationTableArn']

    # Extract table names from ARNs (format: arn:aws:dynamodb:region:account:table/table-name)
    source_table_name = source_table_arn.split('/')[-1]
    destination_table_name = destination_table_arn.split('/')[-1]

    # Guard rail: ensure explicit table name was passed in by caller
    specified_table_name = event.get('tableNameRecoveryConfirmation')
    if specified_table_name != destination_table_name:
        logger.error('DR execution guard flag missing or invalid')
        return {
            'copyStatus': 'FAILED',
            'error': f'Invalid table name specified. '
            f'tableNameRecoveryConfirmation field must be set to {destination_table_name}',
        }

    # Get any pagination key from previous execution
    last_evaluated_key = event.get('copyLastEvaluatedKey')
    if last_evaluated_key is not None:
        last_evaluated_key = json.loads(b64decode(last_evaluated_key).decode('utf-8'))

    logger.info(f'Starting copy of records from {source_table_name} to {destination_table_name}')
    if last_evaluated_key:
        logger.info(f'Continuing from last evaluated key: {last_evaluated_key}')

    # Initialize DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    source_table = dynamodb.Table(source_table_name)
    destination_table = dynamodb.Table(destination_table_name)

    total_copied = event.get('copiedCount', 0)

    try:
        while True:
            # Check if we're approaching the time limit
            current_time = time.time()
            elapsed_time = current_time - start_time

            if elapsed_time > max_execution_time:
                logger.info(f'Approaching time limit after {elapsed_time:.2f} seconds. Returning IN_PROGRESS status.')
                return {
                    'copyStatus': 'IN_PROGRESS',
                    'copyLastEvaluatedKey': b64encode(json.dumps(last_evaluated_key).encode('utf-8')).decode('utf-8'),
                    'copiedCount': total_copied,
                    'sourceTableArn': source_table_arn,
                    'destinationTableArn': destination_table_arn,
                    'tableNameRecoveryConfirmation': event['tableNameRecoveryConfirmation'],
                }

            # Scan the source table to get records to copy
            scan_kwargs = {'Limit': 2000}

            if last_evaluated_key:
                scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

            response = source_table.scan(**scan_kwargs)
            items = response.get('Items', [])

            # Copy items to destination table using batch_writer
            with destination_table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
                    total_copied += 1

            logger.info(f'Copied batch of {len(items)} records. Total copied so far: {total_copied}')

            # Update last_evaluated_key for next iteration
            last_evaluated_key = response.get('LastEvaluatedKey')

            # If no more pages, we're done
            if not last_evaluated_key:
                logger.info(f'Copy complete. Total records copied: {total_copied}')
                return {
                    'copyStatus': 'COMPLETE',
                    'copiedCount': total_copied,
                    'sourceTableArn': source_table_arn,
                    'destinationTableArn': destination_table_arn,
                    'tableNameRecoveryConfirmation': event['tableNameRecoveryConfirmation'],
                }

    except ClientError as e:
        logger.error(f'Error during copy: {str(e)}')
        # raise exception so step function will retry
        raise e
