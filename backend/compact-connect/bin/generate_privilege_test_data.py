#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for local scripts
"""
Script to generate test privilege purchase data for test environments.
It creates privilege records directly in the database to simulate recent privilege purchases.

Run from 'backend/compact-connect' like:
bin/generate_privilege_test_data.py --compact aslp --home-state oh --privilege-state ne --count 10
"""

import argparse
import json
import os
import random
import sys
from datetime import UTC, datetime

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.config import Config

# Add the common lambda runtime to our pythonpath
common_lib_path = os.path.join('lambdas', 'python', 'common')
sys.path.append(common_lib_path)

with open('cdk.json') as context_file:
    _context = json.load(context_file)['context']
COMPACTS = _context['compacts']
JURISDICTIONS = _context['jurisdictions']
LICENSE_TYPES = _context['license_types']

# Set environment variables for cc_common modules
os.environ['COMPACTS'] = json.dumps(COMPACTS)
os.environ['JURISDICTIONS'] = json.dumps(JURISDICTIONS)
os.environ['LICENSE_TYPES'] = json.dumps(LICENSE_TYPES)
os.environ['ENVIRONMENT_NAME'] = 'test'  # Required for cc_common

# Import after setting environment variables
from cc_common.config import config  # noqa: E402
from cc_common.data_model.data_client import DataClient  # noqa: E402
from cc_common.data_model.provider_record_util import ProviderUserRecords  # noqa: E402
from cc_common.data_model.schema.common import ActiveInactiveStatus  # noqa: E402
from cc_common.data_model.schema.privilege import PrivilegeData  # noqa: E402
from cc_common.data_model.schema.provider import ProviderData  # noqa: E402


def get_table_by_pattern(tables: list[str], pattern: str) -> str:
    """Find table name that contains the given pattern."""
    matching_tables = [t for t in tables if pattern in t]
    if not matching_tables:
        raise ValueError(f'No table found containing pattern: {pattern}')
    return matching_tables[0]


def query_eligible_providers(
    provider_table, compact: str, home_state: str, privilege_state: str, count: int
) -> list[dict]:
    """Query providers eligible for privilege purchase in the specified state."""
    eligible_providers = []
    scan_kwargs = {
        'FilterExpression': Attr('sk').eq(f'{compact}#PROVIDER')
        & Attr('licenseJurisdiction').eq(home_state)
        & Attr('jurisdictionUploadedCompactEligibility').eq('eligible')
    }

    done = False
    start_key = None
    scanned_count = 0

    print(f'Scanning for eligible providers in {home_state}...')

    while not done and len(eligible_providers) < count:
        if start_key:
            scan_kwargs['ExclusiveStartKey'] = start_key

        response = provider_table.scan(**scan_kwargs)
        scanned_count += response.get('ScannedCount', 0)
        items_processed = 0

        for item in response.get('Items', []):
            items_processed += 1

            # Check if we already have enough providers
            if len(eligible_providers) >= count:
                break

            provider_id = item.get('providerId')
            if not provider_id:
                continue

            # Check if provider already has a privilege in the target state
            privilege_jurisdictions = item.get('privilegeJurisdictions', set())
            if privilege_state in privilege_jurisdictions:
                continue

            # Provider is eligible - add to our list
            eligible_providers.append(item)
            print(f'Found eligible provider {len(eligible_providers)}/{count}: {provider_id}')

        print(f'Processed {items_processed} items in this batch, scanned {scanned_count} total items')

        start_key = response.get('LastEvaluatedKey')
        done = start_key is None

        # If we've scanned the entire table and still don't have enough, break
        if done:
            break

    print(f'Found {len(eligible_providers)} eligible providers out of {scanned_count} scanned items')
    return eligible_providers


def generate_transaction_id() -> str:
    """Generate a random 12-digit transaction ID."""
    return str(random.randint(100000000000, 999999999999))


def create_privilege_record(
    provider_user_records: ProviderUserRecords,
    compact: str,
    privilege_state: str,
    transaction_id: str,
    privilege_number: int,
) -> dict:
    """Create a privilege record for the provider."""
    provider_data = provider_user_records.get_provider_record()
    provider_id = provider_data.providerId

    # Get license information from provider's license records
    license_records = provider_user_records.get_license_records()

    if not license_records:
        raise ValueError(f'No license records found for provider {provider_id}')

    # Use the first license record (should be the home state license)
    license_record = license_records[0]
    license_type = license_record.licenseType
    license_expiration = license_record.dateOfExpiration

    # Get license type abbreviation
    license_type_abbr: str = config.license_type_abbreviations[compact][license_type]

    # Format privilege ID
    privilege_id = f'{license_type_abbr.upper()}-{privilege_state.upper()}-{int(privilege_number)}'

    current_time = datetime.now(tz=UTC)

    privilege_data = {
        'providerId': provider_id,
        'compact': compact,
        'jurisdiction': privilege_state,
        'licenseJurisdiction': provider_data.licenseJurisdiction,
        'licenseType': license_type,
        'dateOfIssuance': current_time,
        'dateOfRenewal': current_time,
        'dateOfExpiration': license_expiration,
        'compactTransactionId': transaction_id,
        'attestations': [],
        'privilegeId': privilege_id,
        'administratorSetStatus': ActiveInactiveStatus.ACTIVE,
        'dateOfUpdate': current_time,
    }

    # Create PrivilegeData object and serialize to database format
    privilege = PrivilegeData.create_new(privilege_data)
    return privilege.serialize_to_database_record()


def create_provider_update(
    provider_data: ProviderData, privilege_state: str, home_state: str, provider_id: str
) -> dict:
    """Create a combined update expression for all provider fields that need to be set."""
    # Generate a test email address if one doesn't exist
    email = provider_data.compactConnectRegisteredEmailAddress or f'test-provider-{provider_id[:8]}@example.com'

    # Get current privilege jurisdictions and add the new one
    current_privilege_jurisdictions = set(provider_data.privilegeJurisdictions or [])
    current_privilege_jurisdictions.add(privilege_state)

    # Get current timestamp for update fields
    current_time = datetime.now(tz=UTC)

    return {
        'UpdateExpression': (
            'SET currentHomeJurisdiction = :home_jurisdiction, '
            'compactConnectRegisteredEmailAddress = :email, '
            'dateOfUpdate = :date_of_update, '
            'providerDateOfUpdate = :provider_date_of_update '
            'ADD privilegeJurisdictions :privilege_jurisdictions'
        ),
        'ExpressionAttributeValues': {
            ':home_jurisdiction': home_state,
            ':email': email,
            ':date_of_update': current_time.isoformat(),
            ':provider_date_of_update': current_time.isoformat(),
            ':privilege_jurisdictions': {privilege_state},
        },
    }


def main():
    parser = argparse.ArgumentParser(description='Generate test privilege purchase data')
    parser.add_argument('--compact', required=True, choices=COMPACTS, help='The compact to generate privileges for')
    parser.add_argument('--home-state', required=True, help='Jurisdiction where providers have licenses')
    parser.add_argument('--privilege-state', required=True, help='Jurisdiction for privilege purchase')
    parser.add_argument('--count', type=int, default=10, help='Number of privileges to generate')

    args = parser.parse_args()

    if args.home_state == args.privilege_state:
        print('Error: home-state and privilege-state must be different')
        sys.exit(1)

    # Initialize DynamoDB resources
    dynamodb_config = Config(retries=dict(max_attempts=10))
    dynamodb = boto3.resource('dynamodb', config=dynamodb_config)
    dynamodb_client = boto3.client('dynamodb', config=dynamodb_config)

    # Get table names
    tables = dynamodb_client.list_tables()['TableNames']

    provider_table = dynamodb.Table(get_table_by_pattern(tables, 'ProviderTable'))

    # Set the environment variable that cc_common modules expect
    os.environ['PROVIDER_TABLE_NAME'] = provider_table.name

    # Initialize data client for privilege number claiming
    data_client = DataClient(config)

    print(f'Querying eligible providers in {args.home_state}...')

    # Query eligible providers (query more than needed to account for filtering)
    eligible_providers = query_eligible_providers(
        provider_table, args.compact, args.home_state, args.privilege_state, args.count
    )

    if not eligible_providers:
        print(f'No eligible providers found in {args.home_state} without existing privileges')
        sys.exit(1)

    print(f'Found {len(eligible_providers)} eligible providers, generating {args.count} privileges...')

    # Generate privilege records
    processed_count = 0

    for provider_data in eligible_providers:
        if processed_count >= args.count:
            break
        provider_id = provider_data['providerId']
        transaction_id = generate_transaction_id()

        # Claim privilege number for this provider
        privilege_number = data_client.claim_privilege_number(args.compact)

        # Load full provider records to get license information
        provider_user_records = data_client.get_provider_user_records(compact=args.compact, provider_id=provider_id)

        # Check if provider has license records
        license_records = provider_user_records.get_license_records()
        if not license_records:
            print(f'Skipping provider {provider_id} - no license records found')
            continue

        # Create privilege record
        privilege_record = create_privilege_record(
            provider_user_records, args.compact, args.privilege_state, transaction_id, privilege_number
        )

        # Create combined provider update expression
        provider_update_expression = create_provider_update(
            provider_user_records.get_provider_record(), args.privilege_state, args.home_state, provider_id
        )

        # Write privilege record directly to database
        try:
            provider_table.put_item(Item=privilege_record)

            # Update provider record
            provider_table.update_item(
                Key={'pk': f'{args.compact}#PROVIDER#{provider_id}', 'sk': f'{args.compact}#PROVIDER'},
                **provider_update_expression,
            )

            processed_count += 1
            print(f'Created privilege for provider {provider_id} (privilege number {privilege_number})')

        except Exception as e:
            print(f'Error creating privilege for provider {provider_id}: {e}')
            raise

    print(f'Successfully created {processed_count} privilege records for {args.privilege_state}')


if __name__ == '__main__':
    main()
