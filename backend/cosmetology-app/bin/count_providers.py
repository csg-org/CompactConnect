#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for local scripts
"""
Script to count the number of providers in the system by querying the provider table
for all records where the type field equals 'provider'.

Run from 'backend/compact-connect' like:
bin/count_providers.py --table-name test-provider-table
"""

import argparse
import sys

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.config import Config


def count_providers(provider_table) -> int:
    """Count all provider records in the table where type='provider'."""
    count = 0
    scanned_count = 0
    
    scan_kwargs = {
        'FilterExpression': Attr('type').eq('provider'),
        'Select': 'COUNT',  # Only return count, not full items
    }
    
    print('Scanning provider table for records with type="provider"...')
    
    done = False
    start_key = None
    
    while not done:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key
        
        response = provider_table.scan(**scan_kwargs)
        
        count += response.get('Count', 0)
        scanned_count += response.get('ScannedCount', 0)
        
        print(f'Found {count} providers so far (scanned {scanned_count} items)...')
        
        start_key = response.get('LastEvaluatedKey')
        done = start_key is None
    
    print(f'Total providers: {count} (scanned {scanned_count} total items)')
    return count


def main():
    parser = argparse.ArgumentParser(description='Count providers in the provider table')
    parser.add_argument('--table-name', required=True, help='The full provider table name')
    
    args = parser.parse_args()
    
    # Initialize DynamoDB resources
    dynamodb_config = Config(retries=dict(max_attempts=10))
    dynamodb = boto3.resource('dynamodb', config=dynamodb_config)
    
    provider_table = dynamodb.Table(args.table_name)
    
    print(f'Counting providers in table: {args.table_name}\n')
    
    try:
        count = count_providers(provider_table)
        print(f'\n✓ Total number of providers: {count}')
        sys.exit(0)
    except Exception as e:
        print(f'\n✗ Error counting providers: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
