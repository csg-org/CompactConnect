import time

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import logger


def cleanup_records(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    As part of synchronizing tables during a DR event, we clear the current records from the target
    table to put it in a clean state. After which the next step in the recovery process will copy over all the
    existing records from the recovery point table into the target table.

    In the event that the deletion process takes longer than the 15-minute time limit window for lambda, we return a
    'deleteStatus' field of 'IN_PROGRESS', causing the step function to loop around and continue the cleanup process.
    If all the records have been cleaned up, we return a 'deleteStatus' of 'COMPLETE', causing the step function to
    proceed to the copy step.
    """
    start_time = time.time()
    max_execution_time = 12 * 60  # 12 minutes in seconds

    # Get destination table ARN from event
    destination_table_arn = event['destinationTableArn']

    # Extract table name from ARN (format: arn:aws:dynamodb:region:account:table/table-name)
    table_name = destination_table_arn.split('/')[-1]

    logger.info(f'Starting cleanup of records from table: {table_name}')

    # Initialize DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    total_deleted = 0

    last_evaluated_key = None

    try:
        while True:
            # Check if we're approaching the time limit
            current_time = time.time()
            elapsed_time = current_time - start_time

            if elapsed_time > max_execution_time:
                logger.info(f'Approaching time limit after {elapsed_time:.2f} seconds. Returning IN_PROGRESS status.')
                # Note we don't return the last evaluated key here, since we are deleting all records, the lambda
                # can just resume the scan on the next iteration without the need for a key.
                return {
                    'deleteStatus': 'IN_PROGRESS',
                    'deletedCount': total_deleted,
                    'destinationTableArn': destination_table_arn,
                }

            # Scan the table to get records to delete
            scan_kwargs = {
                'Limit': 100  # Process in smaller batches for better performance
            }

            if last_evaluated_key:
                scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])

            if not items:
                # No more items to delete
                logger.info(f'Cleanup complete. Total records deleted: {total_deleted}')
                return {
                    'deleteStatus': 'COMPLETE',
                    'deletedCount': total_deleted,
                    'destinationTableArn': destination_table_arn,
                }

            # Delete items using batch_writer
            with table.batch_writer() as batch:
                for item in items:
                    # Extract the key attributes (pk and sk)
                    key = {'pk': item['pk'], 'sk': item['sk']}
                    batch.delete_item(Key=key)
                    total_deleted += 1

            logger.info(f'Deleted batch of {len(items)} records. Total deleted so far: {total_deleted}')

            # Update last_evaluated_key for next iteration
            last_evaluated_key = response.get('LastEvaluatedKey')

            # If no more pages, we're done
            if not last_evaluated_key:
                logger.info(f'Cleanup complete. Total records deleted: {total_deleted}')
                return {
                    'deleteStatus': 'COMPLETE',
                    'deletedCount': total_deleted,
                    'destinationTableArn': destination_table_arn,
                }

    except Exception as e:
        logger.error(f'Error during cleanup: {str(e)}')
        return {
            'deleteStatus': 'FAILED',
            'error': str(e),
            'deletedCount': total_deleted,
            'destinationTableArn': destination_table_arn,
            'lastEvaluatedKey': last_evaluated_key,
        }
