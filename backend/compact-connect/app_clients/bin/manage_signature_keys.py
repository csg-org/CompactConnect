#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for scripts run locally

"""
Script to manage SIGNATURE public keys in the compact configuration database.

This script allows users to create and delete SIGNATURE public keys for different
compact/jurisdiction combinations. It follows the same interactive style as
the create_app_client.py script.
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def load_cdk_config():
    """Load configuration from cdk.json file."""
    # Find cdk.json file - look in parent directories
    current_dir = Path(__file__).parent
    cdk_json_path = None

    # Look up the directory tree for cdk.json
    for parent in [current_dir] + list(current_dir.parents):
        potential_path = parent / 'cdk.json'
        if potential_path.exists():
            cdk_json_path = potential_path
            break

    if not cdk_json_path:
        raise FileNotFoundError('Could not find cdk.json file in current directory or parent directories')

    with open(cdk_json_path) as f:
        cdk_config = json.load(f)

    context = cdk_config.get('context', {})

    return {
        'compacts': context.get('compacts', []),
        'active_compact_member_jurisdictions': context.get('active_compact_member_jurisdictions', {}),
    }


# Load configuration from cdk.json
CDK_CONFIG = load_cdk_config()
VALID_COMPACTS = CDK_CONFIG['compacts']
ACTIVE_COMPACT_JURISDICTIONS = CDK_CONFIG['active_compact_member_jurisdictions']


def validate_compact(compact):
    """Validate compact input."""
    compact = compact.lower().strip()
    if compact not in VALID_COMPACTS:
        raise ValueError(f'Invalid compact: {compact}. Valid compacts are: {", ".join(VALID_COMPACTS)}')
    return compact


def validate_state(state, compact):
    """Validate state postal abbreviation for the given compact."""
    state = state.lower().strip()

    # Get valid states for this compact
    valid_states = ACTIVE_COMPACT_JURISDICTIONS.get(compact, [])

    if state not in valid_states:
        raise ValueError(
            f'Invalid state: {state}. Valid states for {compact.upper()} compact are: {", ".join(sorted(valid_states))}'
        )
    return state


def validate_key_id(key_id):
    """Validate key ID input."""
    key_id = key_id.strip()
    if not key_id:
        raise ValueError('Key ID cannot be empty')
    if len(key_id) > 100:  # Reasonable limit for key ID
        raise ValueError('Key ID is too long (max 100 characters)')
    if not key_id.replace('-', '').replace('_', '').isalnum():
        raise ValueError('Key ID can only contain alphanumeric characters, hyphens, and underscores')
    return key_id


def get_user_input_for_create():
    """Get user input for creating a SIGNATURE public key."""
    print('=== SIGNATURE Public Key Creation ===\n')

    # Get compact
    while True:
        try:
            print(f'Valid compacts: {", ".join(VALID_COMPACTS)}')
            compact = input('Enter the compact: ').strip()
            compact = validate_compact(compact)
            break
        except ValueError as e:
            print(f'Error: {e}')

    # Get state
    while True:
        try:
            valid_states = ACTIVE_COMPACT_JURISDICTIONS.get(compact, [])
            print(f'\nValid states for {compact.upper()} compact: {", ".join(sorted(valid_states))}')
            state = input("Enter the state postal abbreviation (e.g., 'ky', 'la'): ").strip()
            state = validate_state(state, compact)
            break
        except ValueError as e:
            print(f'Error: {e}')

    # Get key ID
    while True:
        try:
            key_id = input('\nEnter the key ID (e.g., "client-key-001"): ').strip()
            key_id = validate_key_id(key_id)
            break
        except ValueError as e:
            print(f'Error: {e}')

    print('\nConfiguration:')
    print(f'  Compact: {compact}')
    print(f'  State: {state}')
    print(f'  Key ID: {key_id}')
    print(f'  Public key file: {key_id}.pub')

    confirm = input('\nProceed with this configuration? (y/N): ').strip().lower()
    if confirm != 'y':
        print('Configuration cancelled.')
        sys.exit(0)

    return {'compact': compact, 'state': state, 'key_id': key_id}


def read_public_key_file(key_id):
    """Read the public key from the specified file."""
    file_path = Path(f'{key_id}.pub')

    if not file_path.exists():
        raise FileNotFoundError(
            f'Public key file "{file_path}" not found. Please ensure the file exists in the current directory.'
        )

    try:
        with open(file_path) as f:
            public_key_content = f.read().strip()

        if not public_key_content:
            raise ValueError('Public key file is empty')

        # Basic validation that this looks like a PEM public key
        if not public_key_content.startswith('-----BEGIN PUBLIC KEY-----'):
            raise ValueError(
                'Public key file does not appear to be in PEM format (should start with "-----BEGIN PUBLIC KEY-----")'
            )

        if not public_key_content.endswith('-----END PUBLIC KEY-----'):
            raise ValueError(
                'Public key file does not appear to be in PEM format (should end with "-----END PUBLIC KEY-----")'
            )

        return public_key_content

    except (FileNotFoundError, ValueError) as e:
        raise ValueError(f'Error reading public key file: {e}') from e


def create_signature_key(table_name, config):
    """Create the SIGNATURE public key in DynamoDB."""
    compact = config['compact']
    state = config['state']
    key_id = config['key_id']

    print(f'\nCreating SIGNATURE public key: {key_id}')
    print(f'For compact: {compact}, state: {state}')

    try:
        # Create boto3 DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)

        # Check if key already exists
        pk = f'{compact}#SIGNATURE_KEYS'
        sk = f'{compact}#JURISDICTION#{state}#{key_id}'

        response = table.get_item(Key={'pk': pk, 'sk': sk})

        if 'Item' in response:
            print(f'\n⚠️  Warning: A key with ID "{key_id}" already exists for {compact}/{state}')
            overwrite = input('Do you want to overwrite it? (y/N): ').strip().lower()
            if overwrite != 'y':
                print('Operation cancelled.')
                sys.exit(0)

        # Read the public key file
        print(f'\nReading public key from {key_id}.pub...')
        public_key_pem = read_public_key_file(key_id)

        # Create the item
        item = {
            'pk': pk,
            'sk': sk,
            'publicKey': public_key_pem,
            'compact': compact,
            'jurisdiction': state,
            'keyId': key_id,
            'createdAt': datetime.now(tz=UTC).isoformat(),
        }

        # Write to DynamoDB
        table.put_item(Item=item)

        print('\n✅ SIGNATURE public key created successfully!')
        print(f'Key ID: {key_id}')
        print(f'Compact: {compact}')
        print(f'State: {state}')

    except NoCredentialsError:
        print('Error: AWS credentials not found. Please configure your AWS credentials.')
        print("You can use 'aws configure' or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        raise
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f'Error creating SIGNATURE key: {error_code} - {error_message}')
        raise


def get_user_input_for_delete():
    """Get user input for deleting a SIGNATURE public key."""
    print('=== SIGNATURE Public Key Deletion ===\n')

    # Get compact
    while True:
        try:
            print(f'Valid compacts: {", ".join(VALID_COMPACTS)}')
            compact = input('Enter the compact: ').strip()
            compact = validate_compact(compact)
            break
        except ValueError as e:
            print(f'Error: {e}')

    # Get state
    while True:
        try:
            valid_states = ACTIVE_COMPACT_JURISDICTIONS.get(compact, [])
            print(f'\nValid states for {compact.upper()} compact: {", ".join(sorted(valid_states))}')
            state = input("Enter the state postal abbreviation (e.g., 'ky', 'la'): ").strip()
            state = validate_state(state, compact)
            break
        except ValueError as e:
            print(f'Error: {e}')

    return {'compact': compact, 'state': state}


def list_existing_keys(table_name, config):
    """List existing SIGNATURE keys for the given compact/state combination."""
    compact = config['compact']
    state = config['state']

    try:
        # Create boto3 DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)

        # Query for existing keys
        pk = f'{compact}#SIGNATURE_KEYS'
        sk_prefix = f'{compact}#JURISDICTION#{state}#'

        response = table.query(
            KeyConditionExpression='pk = :pk AND begins_with(sk, :sk_prefix)',
            ExpressionAttributeValues={':pk': pk, ':sk_prefix': sk_prefix},
        )

        items = response.get('Items', [])

        if not items:
            print(f'\nNo SIGNATURE keys found for {compact}/{state}')
            return []

        print(f'\nExisting SIGNATURE keys for {compact}/{state}:')
        for i, item in enumerate(items, 1):
            key_id = item['sk'].split('#')[-1]
            created_at = item.get('createdAt', 'Unknown')
            print(f'  {i}. Key ID: {key_id} (Created: {created_at})')

        return items

    except NoCredentialsError:
        print('Error: AWS credentials not found. Please configure your AWS credentials.')
        print("You can use 'aws configure' or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        raise
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f'Error listing SIGNATURE keys: {error_code} - {error_message}')
        raise


def delete_signature_key(table_name, config, key_id):
    """Delete the specified SIGNATURE public key from DynamoDB."""
    compact = config['compact']
    state = config['state']

    print(f'\nDeleting SIGNATURE public key: {key_id}')
    print(f'For compact: {compact}, state: {state}')

    try:
        # Create boto3 DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)

        # Delete the item
        pk = f'{compact}#SIGNATURE_KEYS'
        sk = f'{compact}#JURISDICTION#{state}#{key_id}'

        table.delete_item(Key={'pk': pk, 'sk': sk})

        print('\n✅ SIGNATURE public key deleted successfully!')
        print(f'Key ID: {key_id}')
        print(f'Compact: {compact}')
        print(f'State: {state}')

    except NoCredentialsError:
        print('Error: AWS credentials not found. Please configure your AWS credentials.')
        print("You can use 'aws configure' or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        raise
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f'Error deleting SIGNATURE key: {error_code} - {error_message}')
        raise


def main():
    parser = argparse.ArgumentParser(description='Manage SIGNATURE public keys in the compact configuration database')
    parser.add_argument('action', choices=['create', 'delete'], help='Action to perform (create or delete)')
    parser.add_argument('-t', '--table-name', required=True, help='DynamoDB table name for compact configuration')

    args = parser.parse_args()

    print(f'Managing SIGNATURE keys for {args.table_name} table...\n')

    if args.action == 'create':
        # Create flow
        config = get_user_input_for_create()

        create_signature_key(args.table_name, config)

    elif args.action == 'delete':
        # Delete flow
        config = get_user_input_for_delete()

        # List existing keys
        existing_keys = list_existing_keys(args.table_name, config)

        if not existing_keys:
            print('\nNo keys to delete.')
            sys.exit(0)

        # Get key ID to delete
        while True:
            key_id = input('\nEnter the exact key ID to delete: ').strip()
            key_id = validate_key_id(key_id)

            # Check if key exists
            key_exists = any(item['sk'].split('#')[-1] == key_id for item in existing_keys)
            if not key_exists:
                print(f'Error: Key ID "{key_id}" not found in the list above')
                continue

            break

        # Final confirmation
        print(f'\n⚠️  You are about to delete SIGNATURE key "{key_id}" for {config["compact"]}/{config["state"]}')
        print('This action cannot be undone.')

        confirm = input('\nAre you sure you want to delete this key? Type "DELETE" to confirm: ').strip()
        if confirm != 'DELETE':
            print('Deletion cancelled.')
            sys.exit(0)

        delete_signature_key(args.table_name, config, key_id)


if __name__ == '__main__':
    main()
