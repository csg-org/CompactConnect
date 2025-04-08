#!/usr/bin/env python3
"""
This script is used to purge the provider table of all items.
It is intended to be run from the command line and will delete all items from the table. Obviously, we never want to run
this in production.

To run this script, set the PROVIDER_TABLE_NAME environment variable to the name of the table you want to purge.

Example:
PROVIDER_TABLE_NAME=compact-connect-provider-table-dev ./bin/purge_provider_table.py
"""

import logging
import os

import boto3

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_table_name() -> str:
    """Get the table name from environment variable."""
    table_name = os.environ.get('PROVIDER_TABLE_NAME')
    if not table_name:
        raise ValueError('Please set PROVIDER_TABLE_NAME environment variable')

    if table_name.startswith('Prod'):
        raise ValueError('This script should not be run against production tables. Aborting.')
    return table_name


def purge_table(table_name: str) -> None:
    """Delete all items from the specified DynamoDB table."""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # Initialize counters
    deleted_count = 0
    error_count = 0

    # Scan the table
    scan_pagination = {}
    while True:
        try:
            response = table.scan(**scan_pagination)
            items = response.get('Items', [])

            if not items:
                logger.info('No more items to delete')
                break

            logger.info('Found %d items to delete in current batch', len(items))

            # Delete each item
            for item in items:
                try:
                    key = {'pk': item['pk'], 'sk': item['sk']}
                    table.delete_item(Key=key)
                    deleted_count += 1
                    if deleted_count % 100 == 0:
                        logger.info('Deleted %d items so far', deleted_count)
                except Exception as e:  # noqa: BLE001
                    logger.error('Error deleting item %s: %s', key, str(e))
                    error_count += 1

            # Check if we need to continue pagination
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break

            scan_pagination = {'ExclusiveStartKey': last_evaluated_key}

        except Exception as e:  # noqa: BLE001
            logger.error('Error during scan: %s', str(e))
            error_count += 1
            break

    # Log final statistics
    logger.info('Purge completed. Successfully deleted %d items', deleted_count)
    if error_count > 0:
        logger.warning('Encountered %d errors during purge', error_count)


if __name__ == '__main__':
    try:
        table_name = get_table_name()
        logger.info('Starting purge of table: %s', table_name)
        purge_table(table_name)
    except Exception as e:  # noqa: BLE001
        logger.error('Script failed: %s', e)
        exit(1)
