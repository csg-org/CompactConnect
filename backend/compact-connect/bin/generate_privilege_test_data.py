#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for local scripts
"""
Script to generate test privilege purchase data for test environments.
It creates privilege records directly in the database to simulate recent privilege purchases.

Run from 'backend/compact-connect' like:
bin/generate_privilege_test_data.py --compact aslp --home-state oh --privilege-state ne --count 10

To only create privileges for licenses uploaded after a specific date:
bin/generate_privilege_test_data.py --compact aslp --home-state oh --privilege-state ne --count 10 \
    --license-uploaded-after "2028-01-15T10:30:00Z"
"""

import argparse
import json
import os
import random
import sys
from datetime import UTC, datetime
from uuid import UUID

import boto3
from boto3.dynamodb.conditions import Attr, Key
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


def query_eligible_providers(
    provider_table,
    compact: str,
    home_state: str,
    count: int,
    license_type: str | None = None,
    license_uploaded_after: datetime | None = None,
) -> set[str]:
    """Query licenseGSI or licenseUploadDateGSI and return set of provider IDs from eligible license records."""

    from dateutil.relativedelta import relativedelta

    provider_ids = set()

    # Determine which GSI to use based on whether we're filtering by upload date
    if license_uploaded_after:
        # Use licenseUploadDateGSI for more efficient date filtering
        # Note: The GSI only projects providerId, so we need to load full records to filter by type/eligibility
        # The GSI is partitioned by month, so we may need to query multiple months

        current_date = datetime.now(tz=UTC)
        query_start_date = license_uploaded_after

        print(
            f'Querying licenseUploadDateGSI for providers with licenses uploaded after {license_uploaded_after.isoformat()}...'
        )
        # Iterate through each month from the start date to now
        month_date = query_start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Collect license items to process
        license_items_to_check = []

        while month_date <= current_date:
            year_month = month_date.strftime('%Y-%m')
            gsi_pk = f'C#{compact.lower()}#J#{home_state.lower()}#D#{year_month}'

            # For the first month, use the specific timestamp
            # For subsequent months, start from the beginning of the month
            if month_date.year == query_start_date.year and month_date.month == query_start_date.month:
                upload_epoch_time = int(query_start_date.timestamp())
            else:
                upload_epoch_time = int(month_date.timestamp())

            query_kwargs = {
                'IndexName': 'licenseUploadDateGSI',
                'KeyConditionExpression': Key('licenseUploadDateGSIPK').eq(gsi_pk)
                & Key('licenseUploadDateGSISK').gte(f'TIME#{upload_epoch_time}'),
            }

            print(f'  Querying month: {year_month}...')

            # Query this month's partition - GSI only returns pk, sk, and providerId
            queried_count = 0
            done = False
            start_key = None

            while not done:
                if start_key:
                    query_kwargs['ExclusiveStartKey'] = start_key

                response = provider_table.query(**query_kwargs)
                items = response.get('Items', [])
                queried_count += len(items)
                license_items_to_check.extend(items)

                start_key = response.get('LastEvaluatedKey')
                done = start_key is None

            print(f'  Found {queried_count} license records in {year_month}')

            # Move to next month
            month_date = month_date + relativedelta(months=1)

        print(f'Total license records from GSI: {len(license_items_to_check)}')
        print('Loading full license records to filter by type and eligibility...')

        # Now load the full license records and filter
        checked_count = 0
        for item in license_items_to_check:
            if len(provider_ids) >= count:
                break

            checked_count += 1
            if checked_count % 100 == 0:
                print(
                    f'  Checked {checked_count}/{len(license_items_to_check)} records, found {len(provider_ids)} eligible providers...'
                )

            # Load the full license record using pk and sk
            pk = item.get('pk')
            sk = item.get('sk')

            if not pk or not sk:
                continue

            # Get the full license record
            try:
                full_record_response = provider_table.get_item(Key={'pk': pk, 'sk': sk})
                full_license = full_record_response.get('Item')

                if not full_license:
                    continue

                # Filter by license type if specified
                if license_type and full_license.get('licenseType') != license_type:
                    continue

                # Filter by eligibility
                if full_license.get('jurisdictionUploadedCompactEligibility') != 'eligible':
                    continue

                # This license meets our criteria
                provider_id = full_license.get('providerId')
                if provider_id:
                    provider_ids.add(provider_id)
                    if len(provider_ids) % 10 == 0:
                        print(f'    Found {len(provider_ids)}/{count} unique eligible provider IDs...')
            except Exception as e:
                print(f'  Warning: Error loading record {pk}/{sk}: {e}')
                continue

        print(f'Found {len(provider_ids)} eligible provider IDs after filtering {checked_count} license records')
        return provider_ids
    else:
        # Use the standard licenseGSI
        # Build GSI PK: C#<compact>#J#<home_state>
        gsi_pk = f'C#{compact.lower()}#J#{home_state.lower()}'

        # Build query kwargs
        query_kwargs = {
            'IndexName': 'licenseGSI',
            'KeyConditionExpression': Key('licenseGSIPK').eq(gsi_pk),
        }

        print(f'Querying licenseGSI for eligible providers in {home_state}...')

    # Add license type filter if specified
    if license_type:
        query_kwargs['FilterExpression'] = Attr('licenseType').eq(license_type)
        print(f'Filtering by license type: {license_type}')

    # Also filter for eligible licenses
    if 'FilterExpression' in query_kwargs:
        query_kwargs['FilterExpression'] = query_kwargs['FilterExpression'] & Attr(
            'jurisdictionUploadedCompactEligibility'
        ).eq('eligible')
    else:
        query_kwargs['FilterExpression'] = Attr('jurisdictionUploadedCompactEligibility').eq('eligible')

    queried_count = 0
    done = False
    start_key = None

    while not done and len(provider_ids) < count:
        if start_key:
            query_kwargs['ExclusiveStartKey'] = start_key

        response = provider_table.query(**query_kwargs)
        queried_count += len(response.get('Items', []))

        for license_item in response.get('Items', []):
            # Check if we already have enough providers
            if len(provider_ids) >= count:
                break

            provider_id = license_item.get('providerId')
            if provider_id:
                provider_ids.add(provider_id)
                if len(provider_ids) % 10 == 0:
                    print(f'Found {len(provider_ids)}/{count} unique provider IDs...')

        start_key = response.get('LastEvaluatedKey')
        done = start_key is None

        # If we've queried all records and still don't have enough, break
        if done:
            break

    print(f'Found {len(provider_ids)} unique provider IDs out of {queried_count} license records queried')
    return provider_ids


def generate_transaction_id() -> str:
    """Generate a random 12-digit transaction ID."""
    return str(random.randint(100000000000, 999999999999))


def create_privilege_record(
    provider_user_records: ProviderUserRecords,
    compact: str,
    privilege_state: str,
    transaction_id: str,
    privilege_number: int,
    license_type: str | None = None,
) -> dict:
    """Create a privilege record for the provider."""
    provider_data = provider_user_records.get_provider_record()
    provider_id = provider_data.providerId

    # Get license information from provider's license records
    license_records = provider_user_records.get_license_records()

    if not license_records:
        raise ValueError(f'No license records found for provider {provider_id}')

    # Find the appropriate license record
    license_record = None
    if license_type:
        # Find license record matching the specified license type
        for record in license_records:
            if record.licenseType == license_type:
                license_record = record
                break
        if not license_record:
            raise ValueError(f'No license record found for provider {provider_id} with license type {license_type}')
    else:
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
    parser.add_argument('--provider-id', type=str, help='Optional: Specific provider ID to add privileges to')
    parser.add_argument('--license-type', type=str, help='Optional: License type to associate with the privilege(s)')
    parser.add_argument(
        '--license-uploaded-after',
        type=str,
        help='Optional: UTC timestamp (ISO 8601 format) to only consider licenses uploaded after this time',
    )

    args = parser.parse_args()

    if args.home_state == args.privilege_state:
        print('Error: home-state and privilege-state must be different')
        sys.exit(1)

    # Validate license type if provided
    if args.license_type:
        valid_license_types = config.license_types_for_compact(args.compact)
        if args.license_type not in valid_license_types:
            print(f'Error: Invalid license type "{args.license_type}" for compact "{args.compact}"')
            print(f'Valid license types: {", ".join(valid_license_types)}')
            sys.exit(1)

    # Parse and validate license-uploaded-after timestamp if provided
    license_uploaded_after = None
    if args.license_uploaded_after:
        try:
            # Parse ISO 8601 timestamp string to datetime object
            license_uploaded_after = datetime.fromisoformat(args.license_uploaded_after.replace('Z', '+00:00'))
            # Ensure it's timezone-aware and in UTC
            if license_uploaded_after.tzinfo is None:
                license_uploaded_after = license_uploaded_after.replace(tzinfo=UTC)
            else:
                license_uploaded_after = license_uploaded_after.astimezone(UTC)
            print(f'Filtering licenses uploaded after: {license_uploaded_after.isoformat()}')
        except ValueError as e:
            print(f'Error: Invalid timestamp format for --license-uploaded-after: {e}')
            print('Expected ISO 8601 format (e.g., "2024-01-15T10:30:00Z" or "2024-01-15T10:30:00+00:00")')
            sys.exit(1)

    # Prompt for environment name for safety validation
    print('\n⚠️  WARNING: This script will write directly to the database.')
    environment_name = input('Enter the environment name (e.g., beta, sandbox, test): ').strip()
    if not environment_name:
        print('Error: Environment name is required')
        sys.exit(1)

    # Refuse to run if environment looks like production
    if environment_name.lower() == 'prod' or environment_name.lower() == 'production':
        print('Error: This script cannot be run against production environments')
        sys.exit(1)

    # Prompt for full provider table name
    provider_table_name = input('Enter the full provider table name: ').strip()
    if not provider_table_name:
        print('Error: Provider table name is required')
        sys.exit(1)

    # Validate that table name starts with environment name prefix (case insensitive)
    expected_prefix = f'{environment_name}-'
    if not provider_table_name.lower().startswith(expected_prefix.lower()):
        print(
            f'Error: Table name "{provider_table_name}" does not match environment "{environment_name}". '
            f'Expected table name to start with "{expected_prefix}" (case insensitive)'
        )
        sys.exit(1)

    print(f'✓ Validated table: {provider_table_name}')

    # Initialize DynamoDB resources
    dynamodb_config = Config(retries=dict(max_attempts=10))
    dynamodb = boto3.resource('dynamodb', config=dynamodb_config)

    provider_table = dynamodb.Table(provider_table_name)

    # Set the environment variables that cc_common modules expect
    os.environ['PROVIDER_TABLE_NAME'] = provider_table.name

    # Initialize data client for privilege number claiming
    data_client = DataClient(config)

    # Handle provider-id case: skip query and use specific provider
    if not args.provider_id:
        print(f'Querying eligible providers in {args.home_state}...')

        # Query eligible provider IDs using licenseGSI or licenseUploadDateGSI
        provider_ids = query_eligible_providers(
            provider_table,
            args.compact,
            args.home_state,
            args.count,
            args.license_type,
            license_uploaded_after,
        )

        if not provider_ids:
            print(f'No eligible providers found in {args.home_state}')
            sys.exit(1)
    else:
        # Use the provided provider ID
        provider_ids = [args.provider_id]

    print(f'Found {len(provider_ids)} provider(s), generating privileges...')

    # Generate privilege records
    processed_count = 0

    for provider_id in provider_ids:
        if processed_count >= args.count:
            break
        transaction_id = generate_transaction_id()

        # Claim privilege number for this provider
        privilege_number = data_client.claim_privilege_number(args.compact)

        # Load full provider records to get license information
        # Convert provider_id to UUID if it's a string
        provider_id_uuid = UUID(provider_id) if isinstance(provider_id, str) else provider_id
        provider_user_records = data_client.get_provider_user_records(
            compact=args.compact, provider_id=provider_id_uuid
        )

        # Check if provider has license records
        license_records = provider_user_records.get_license_records()
        if not license_records:
            print(f'Skipping provider {provider_id} - no license records found')
            continue

        # Determine which license type we'll use for the privilege
        target_license_type = args.license_type or license_records[0].licenseType

        # Check if provider already has a privilege for this specific license type in the target state
        existing_privileges = provider_user_records.get_privilege_records(
            filter_condition=lambda p, license_type=target_license_type: p.jurisdiction == args.privilege_state
            and p.licenseType == license_type
        )
        if existing_privileges:
            if args.provider_id:
                print(
                    f'Error: Provider {provider_id} already has a {target_license_type} '
                    f'privilege in {args.privilege_state}'
                )
                sys.exit(1)
            else:
                print(
                    f'Skipping provider {provider_id} - already has a {target_license_type} '
                    f'privilege in {args.privilege_state}'
                )
                continue

        # Create privilege record
        privilege_record = create_privilege_record(
            provider_user_records,
            args.compact,
            args.privilege_state,
            transaction_id,
            privilege_number,
            args.license_type,
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
