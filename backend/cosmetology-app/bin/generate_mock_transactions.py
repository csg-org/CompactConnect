# ruff: noqa: T201 we use print statements for local scripts
#!/usr/bin/env python3
# Script to generate mock transaction data for test environments
# it spreads the transactions across a range of dates and providers to simulate real-world data.
#
# Run from 'backend/compact-connect' like:
# bin/generate_mock_transactions.py --compact cosm --start_date 01/01/2024 --end_date 03/01/2024 --count 100

import argparse
import asyncio
import json
import os
import random
import sys
from datetime import UTC, datetime

import boto3
from botocore.config import Config

# Add the provider data lambda runtime to our pythonpath
provider_data_path = os.path.join('lambdas', 'python', 'common')
sys.path.append(provider_data_path)

with open('cdk.json') as context_file:
    _context = json.load(context_file)['context']
COMPACTS = _context['compacts']


def parse_date(date_str: str) -> datetime:
    """Parse date string in mm/dd/yyyy format to datetime object."""
    return datetime.strptime(date_str, '%m/%d/%Y').replace(tzinfo=UTC)


def get_random_timestamp(start_date: datetime, end_date: datetime) -> datetime:
    """Generate a random timestamp between start and end dates."""
    time_diff = end_date.timestamp() - start_date.timestamp()
    random_time = start_date.timestamp() + random.random() * time_diff
    return datetime.fromtimestamp(random_time, tz=UTC)


def get_table_by_pattern(tables: list[dict], pattern: str) -> str:
    """Find table name that contains the given pattern."""
    matching_tables = [t['TableName'] for t in tables if pattern in t['TableName']]
    if not matching_tables:
        raise ValueError(f'No table found containing pattern: {pattern}')
    return matching_tables[0]


async def get_provider_ids(provider_table, compact: str) -> set:
    """Get all provider IDs for the given compact."""
    provider_ids = set()
    scan_kwargs = {'FilterExpression': boto3.dynamodb.conditions.Key('sk').eq(f'{compact}#PROVIDER')}

    done = False
    start_key = None
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        response = provider_table.scan(**scan_kwargs)
        for item in response.get('Items', []):
            if 'providerId' in item:
                provider_ids.add(item['providerId'])
        start_key = response.get('LastEvaluatedKey', None)
        done = start_key is None

    print(f'Found {len(provider_ids)} providers for compact {compact}')
    return provider_ids


def generate_transaction(compact: str, start_date: datetime, end_date: datetime, provider_id: str) -> dict:
    """Generate a single mock transaction."""
    settlement_time = get_random_timestamp(start_date, end_date)
    submit_time = get_random_timestamp(start_date, settlement_time)
    transaction_id = str(random.randint(100000000000, 999999999999))
    batch_id = '15867123'
    epoch_timestamp = int(settlement_time.timestamp())
    month_key = settlement_time.strftime('%Y-%m')

    return {
        'pk': f'COMPACT#{compact}#TRANSACTIONS#MONTH#{month_key}',
        'sk': f'COMPACT#{compact}#TIME#{epoch_timestamp}#BATCH#{batch_id}#TX#{transaction_id}',
        'batch': {
            'batchId': batch_id,
            'settlementState': 'settledSuccessfully',
            'settlementTimeLocal': settlement_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'settlementTimeUTC': settlement_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        },
        'compact': compact,
        'licenseeId': provider_id,
        'lineItems': [
            {
                'description': 'Compact Privilege for Ohio',
                'itemId': f'{compact}-oh',
                'name': 'Ohio Compact Privilege',
                'quantity': '1.0',
                'taxable': 'False',
                'unitPrice': '75.0',
            },
            {
                'description': 'Compact fee applied for each privilege purchased',
                'itemId': f'{compact}-compact-fee',
                'name': f'{compact.upper()} Compact Fee',
                'quantity': '1.0',
                'taxable': 'False',
                'unitPrice': '10.0',
            },
        ],
        'responseCode': '1',
        'settleAmount': '85.0',
        'submitTimeUTC': submit_time.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        'transactionId': transaction_id,
        'transactionProcessor': 'authorize.net',
        'transactionStatus': 'settledSuccessfully',
        'transactionType': 'authCaptureTransaction',
    }


async def write_transactions_batch(transaction_table, batch: list[dict]):
    """Write a batch of transactions to DynamoDB."""
    try:
        with transaction_table.batch_writer() as batch_writer:
            for transaction in batch:
                batch_writer.put_item(Item=transaction)
                # Give other tasks a chance to run
                await asyncio.sleep(0)
    except Exception as e:
        print(f'Error writing batch: {str(e)}')
        raise


async def main():
    parser = argparse.ArgumentParser(description='Generate mock transaction data')
    parser.add_argument('--compact', required=True, choices=COMPACTS, help='The compact to generate transactions for')
    parser.add_argument('--start_date', required=True, help='Start date in mm/dd/yyyy format')
    parser.add_argument('--end_date', required=True, help='End date in mm/dd/yyyy format')
    parser.add_argument('--count', type=int, required=True, help='Number of transactions to generate')

    args = parser.parse_args()

    # Parse dates
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)

    # Initialize DynamoDB resource
    config = Config(retries=dict(max_attempts=10))
    dynamodb = boto3.resource('dynamodb', config=config)

    # Get list of tables
    client = boto3.client('dynamodb')
    tables = client.list_tables()['TableNames']
    tables = [{'TableName': t} for t in tables]

    # Get table resources
    provider_table = dynamodb.Table(get_table_by_pattern(tables, 'ProviderTable'))
    transaction_table = dynamodb.Table(get_table_by_pattern(tables, 'TransactionHistoryTable'))

    # Get provider IDs
    provider_ids = await get_provider_ids(provider_table, args.compact)
    if not provider_ids:
        raise ValueError(f'No providers found for compact {args.compact}')

    # Convert provider_ids to list for random selection
    provider_ids = list(provider_ids)

    # Generate transactions
    transactions = []
    for _ in range(args.count):
        provider_id = provider_ids[_ % len(provider_ids)]
        transaction = generate_transaction(args.compact, start_date, end_date, provider_id)
        transactions.append(transaction)

    # Split transactions into batches for parallel processing
    batch_size = 25  # DynamoDB batch_writer handles up to 25 items
    transaction_batches = [transactions[i : i + batch_size] for i in range(0, len(transactions), batch_size)]

    # Create tasks for parallel batch writing
    tasks = [write_transactions_batch(transaction_table, batch) for batch in transaction_batches]

    # Execute all batch writes concurrently
    await asyncio.gather(*tasks)

    print(f'Successfully wrote {len(transactions)} transactions to the database')


if __name__ == '__main__':
    asyncio.run(main())
