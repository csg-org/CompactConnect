#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for scripts run locally

"""
Script to create and modify AWS Cognito app clients interactively.

This script prompts users for the necessary information to create app clients
in different environments (test, beta, prod) and automatically generates
the standard scopes based on compact and state inputs.

It also supports modifying existing app clients by updating their scopes.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

BASE_CLIENT_CONFIG = {
    'PreventUserExistenceErrors': 'ENABLED',
    'TokenValidityUnits': {'AccessToken': 'minutes'},
    'AccessTokenValidity': 15,
    'AllowedOAuthFlowsUserPoolClient': True,
    'AllowedOAuthFlows': ['client_credentials'],
}


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


# Valid scope patterns for validation
VALID_SCOPE_PATTERNS = [
    r'^[a-z]+/readGeneral$',
    r'^[a-z]+/readSSN$',
    r'^[a-z]+/write$',
    r'^[a-z]+/admin$',
    r'^[a-z]{2}/[a-z]+\.write$',
    r'^[a-z]{2}/[a-z]+\.readPrivate$',
    r'^[a-z]{2}/[a-z]+\.readSSN$',
    r'^[a-z]{2}/[a-z]+\.admin$',
]


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


def validate_scope(scope):
    """Validate a single scope against known patterns."""
    scope = scope.strip()
    for pattern in VALID_SCOPE_PATTERNS:
        if re.match(pattern, scope):
            return True
    return False


def validate_additional_scopes(scopes_input):
    """Validate additional scopes input."""
    if not scopes_input.strip():
        return []

    scopes = [scope.strip() for scope in scopes_input.split(',')]
    invalid_scopes = []

    for scope in scopes:
        if not validate_scope(scope):
            invalid_scopes.append(scope)

    if invalid_scopes:
        print(f'\nInvalid scopes detected: {", ".join(invalid_scopes)}')
        print('Valid scope patterns:')
        print('  Compact-level: {compact}/readGeneral, {compact}/readSSN, {compact}/write, {compact}/admin')
        print(
            'Jurisdiction-level: {state}/{compact}.write, {state}/{compact}.readPrivate, {state}/{compact}.readSSN, '
            '{state}/{compact}.admin'
        )
        raise ValueError('Invalid scopes provided')

    return scopes


def get_user_input():
    """Get user input for app client configuration."""
    print('=== App Client Configuration ===\n')

    # Get environment
    while True:
        try:
            print('Valid environments: test, beta, prod')
            environment = input('Enter the environment: ').strip().lower()
            if environment not in ['test', 'beta', 'prod']:
                raise ValueError('Invalid environment. Must be one of: test, beta, prod')
            break
        except ValueError as e:
            print(f'Error: {e}')

    # Get client name
    client_name = input("Enter the app client name (e.g., 'example-ky-app-client-v1'): ").strip()
    if not client_name:
        raise ValueError('Client name is required')

    # Get compact
    while True:
        try:
            print(f'\nValid compacts: {", ".join(VALID_COMPACTS)}')
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

    # Get additional scopes (optional)
    print('\nThe following scope will be automatically included:')
    print(f'  - {state}/{compact}.write')

    additional_scopes = []
    while True:
        try:
            scopes_input = input('\nEnter any additional scopes (comma-separated, or press Enter for none): ').strip()
            additional_scopes = validate_additional_scopes(scopes_input)
            break
        except ValueError as e:
            print(f'Error: {e}')
            continue

    # Generate final scope list
    scopes = [f'{state}/{compact}.write']
    scopes.extend(additional_scopes)

    # Remove duplicates
    deduped_scopes = list(set(scopes))

    print('\nFinal configuration:')
    print(f'  Client Name: {client_name}')
    print(f'  Compact: {compact}')
    print(f'  State: {state}')
    print(f'  Scopes: {", ".join(deduped_scopes)}')

    confirm = input('\nProceed with this configuration? (y/N): ').strip().lower()
    if confirm != 'y':
        print('Configuration cancelled.')
        sys.exit(0)

    return {
        'environment': environment,
        'clientName': client_name,
        'compact': compact,
        'state': state,
        'scopes': deduped_scopes,
    }


def get_cognito_client():
    """Get a boto3 Cognito IDP client."""
    try:
        return boto3.client('cognito-idp')
    except NoCredentialsError:
        print('Error: AWS credentials not found. Please configure your AWS credentials.')
        print("You can use 'aws configure' or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        sys.exit(1)


def get_app_client(user_pool_id, client_id):
    """Get the current app client configuration from AWS."""
    cognito_client = get_cognito_client()

    try:
        response = cognito_client.describe_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_id,
        )
        return response.get('UserPoolClient', {})
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        if error_code == 'ResourceNotFoundException':
            print(f'Error: App client with ID {client_id} not found in user pool {user_pool_id}')
        else:
            print(f'Error retrieving app client: {error_code} - {error_message}')
        sys.exit(1)


def create_app_client(user_pool_id, config):
    """Create the app client using boto3 Cognito client."""
    client_name = config['clientName']
    scopes = config['scopes']

    print(f'\nCreating app client: {client_name}')
    print(f'With scopes: {", ".join(scopes)}')

    cognito_client = get_cognito_client()

    try:
        # Create the user pool client
        return cognito_client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=client_name,
            AllowedOAuthScopes=scopes,
            GenerateSecret=True,
            **BASE_CLIENT_CONFIG,
        )
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f'Error creating app client: {error_code} - {error_message}')
        sys.exit(1)


def update_app_client_scopes(user_pool_id, client_id, current_client_config, new_scopes):
    """Update the app client scopes using boto3 Cognito client."""
    cognito_client = get_cognito_client()

    print('\nUpdating app client scopes')
    print(f'New scopes: {", ".join(new_scopes)}')

    try:
        # Update the user pool client with new scopes, keeping the same base configuration
        return cognito_client.update_user_pool_client(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            ClientName=current_client_config.get('ClientName'),
            **BASE_CLIENT_CONFIG,
            AllowedOAuthScopes=new_scopes,
        )
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f'Error updating app client: {error_code} - {error_message}')
        sys.exit(1)


def print_credentials(client_id, client_secret):
    """Print only the sensitive credentials in JSON format for secure copy/paste."""
    credentials = {
        'clientId': client_id,
        'clientSecret': client_secret,
    }

    print('\n' + '=' * 60)
    print('APP CLIENT CREDENTIALS (FOR ONE-TIME LINK SERVICE)')
    print('=' * 60)
    print(json.dumps(credentials, indent=2))
    print('=' * 60)
    print('Please copy the JSON above and use it with your one-time secret link generator.')
    print('Do not leave these credentials in terminal history or logs.')
    print('=' * 60)


def get_modification_input(user_pool_id, client_id):
    """Get user input for modifying app client scopes."""
    print('=== Modify App Client Scopes ===\n')

    # Get current client configuration
    print(f'Fetching current configuration for client ID: {client_id}...')
    current_client = get_app_client(user_pool_id, client_id)
    current_scopes = current_client.get('AllowedOAuthScopes', [])

    print(f'\nCurrent scopes: {", ".join(current_scopes) if current_scopes else "(none)"}')

    # Prompt for add or remove
    while True:
        try:
            operation = input('\nDo you want to (a)dd or (r)emove scopes? [a/r]: ').strip().lower()
            if operation not in ['a', 'add', 'r', 'remove']:
                raise ValueError('Invalid operation. Please enter "a" for add or "r" for remove')
            break
        except ValueError as e:
            print(f'Error: {e}')

    is_add = operation in ['a', 'add']

    # Prompt for scopes
    while True:
        try:
            if is_add:
                scopes_input = input('\nEnter scope(s) to add (comma-separated): ').strip()
            else:
                scopes_input = input('\nEnter scope(s) to remove (comma-separated): ').strip()

            if not scopes_input:
                raise ValueError('At least one scope is required')

            scopes = validate_additional_scopes(scopes_input)
            break
        except ValueError as e:
            print(f'Error: {e}')
            continue

    # Calculate new scopes
    if is_add:
        new_scopes = list(set(current_scopes + scopes))
        print(f'\nScopes to add: {", ".join(scopes)}')
    else:
        new_scopes = [s for s in current_scopes if s not in scopes]
        removed_scopes = [s for s in scopes if s in current_scopes]
        not_found_scopes = [s for s in scopes if s not in current_scopes]

        if not_found_scopes:
            print(f'\nWarning: The following scopes were not found in current scopes: {", ".join(not_found_scopes)}')

        if removed_scopes:
            print(f'\nScopes to remove: {", ".join(removed_scopes)}')
        else:
            print('\nNo scopes will be removed (none of the specified scopes were found in current scopes)')
            sys.exit(0)

    print(f'\nNew scopes after modification: {", ".join(new_scopes) if new_scopes else "(none)"}')

    confirm = input('\nProceed with this modification? (y/N): ').strip().lower()
    if confirm != 'y':
        print('Modification cancelled.')
        sys.exit(0)

    return {
        'current_client': current_client,
        'new_scopes': new_scopes,
    }


def print_email_template(environment, compact, state):
    """Print an email template with contextual information for the consuming team."""
    # Get environment-specific URLs
    auth_urls = {
        'beta': 'https://compact-connect-state-auth-beta.auth.us-east-1.amazoncognito.com/oauth2/token',
        'prod': 'https://compact-connect-state-auth.auth.us-east-1.amazoncognito.com/oauth2/token',
        'test': 'https://compact-connect-state-auth-test.auth.us-east-1.amazoncognito.com/oauth2/token',
    }

    api_base_urls = {
        'beta': 'https://state-api.beta.compactconnect.org',
        'prod': 'https://state-api.compactconnect.org',
        'test': 'https://state-api.test.compactconnect.org',
    }

    # Compact name mapping
    compact_names = {
        'aslp': 'Audiology and Speech Language Pathology',
        'octp': 'Occupational Therapy',
        'coun': 'Counseling',
    }

    compact_name = compact_names.get(compact, compact.upper())
    auth_url = auth_urls.get(environment)
    license_upload_url = f'{api_base_urls.get(environment)}/v1/compacts/{compact}/jurisdictions/{state}/licenses'

    email_template = f"""
Thank you for integrating with Compact Connect! You have been designated as the IT professional who is able to handle
credentials for secure machine-to-machine authentication between your state and CompactConnect.

Details for these credentials are:
Compact: {compact_name}
State: {state.upper()}
Auth URL: {auth_url}
License Upload URL: {license_upload_url}

Follow this link to your API credentials as soon as you are ready to securely store them. They will only be viewable
once:
<insert one-time link here>

**Please respond to this email to confirm that you have received and securely stored the credentials. This link will
expire in 7 days.**

For more information on CompactConnect and how to integrate your state IT system with ours, see the documentation
here:
https://github.com/csg-org/CompactConnect/blob/main/backend/compact-connect/docs/it_staff_onboarding_instructions.md
"""

    print('\n' + '=' * 60)
    print('EMAIL TEMPLATE (COPY/PASTE INTO EMAIL CLIENT)')
    print('=' * 60)
    print(email_template.strip())
    print('=' * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Create or modify AWS Cognito app client interactively',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  Create a new app client:\n'
            '    %(prog)s -u <user-pool-id>\n\n'
            '  Modify scopes on an existing app client:\n'
            '    %(prog)s -u <user-pool-id> --client-id <client-id>'
        ),
    )
    parser.add_argument('-u', '--user-pool-id', required=True, help='AWS Cognito User Pool ID')
    parser.add_argument(
        '-c',
        '--client-id',
        help='Client ID of existing app client to modify (if provided, script will modify scopes instead of creating)',
    )

    args = parser.parse_args()

    try:
        print(f'User Pool ID: {args.user_pool_id}\n')

        if args.client_id:
            # Modification mode
            modification_config = get_modification_input(args.user_pool_id, args.client_id)

            # Update the app client
            response = update_app_client_scopes(
                args.user_pool_id,
                args.client_id,
                modification_config['current_client'],
                modification_config['new_scopes'],
            )

            updated_client = response.get('UserPoolClient', {})
            client_name = updated_client.get('ClientName')

            print('\n✅ App client scopes updated successfully!')
            print(f'Client Name: {client_name}')
            print(f'Client ID: {args.client_id}')
            print(f'Updated Scopes: {", ".join(modification_config["new_scopes"])}')

        else:
            # Creation mode
            # Get configuration from user input (including environment)
            config = get_user_input()

            print(f'\nCreating app client for {config["environment"]} environment...')

            # Create the app client
            response = create_app_client(args.user_pool_id, config)

            # Extract credentials from response
            user_pool_client = response.get('UserPoolClient', {})
            client_id = user_pool_client.get('ClientId')
            client_secret = user_pool_client.get('ClientSecret')
            client_name = user_pool_client.get('ClientName')

            if not client_id or not client_secret:
                print('Error: Could not extract client ID or secret from AWS response')
                sys.exit(1)

            print('\n✅ App client created successfully!')
            print(f'Client Name: {client_name}')
            print(f'Client ID: {client_id}')

            # Print credentials for secure copy/paste
            print_credentials(client_id, client_secret)

            # Print email template
            print_email_template(config['environment'], config['compact'], config['state'])

            print('\n📝 Remember to add this app client to your external registry!')

    except Exception as e:  # noqa: BLE001
        print(f'Error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
