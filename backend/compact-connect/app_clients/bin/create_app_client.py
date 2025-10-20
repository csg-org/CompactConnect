#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for scripts run locally

"""
Script to create AWS Cognito app clients interactively.

This script prompts users for the necessary information to create app clients
in different environments (test, beta, prod) and automatically generates
the standard scopes based on compact and state inputs.
"""

import argparse
import json
import re
import sys
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

    return {'environment': environment, 'clientName': client_name, 'compact': compact, 'state': state, 'scopes': deduped_scopes}


def create_app_client(user_pool_id, config):
    """Create the app client using boto3 Cognito client."""
    client_name = config['clientName']
    scopes = config['scopes']

    print(f'\nCreating app client: {client_name}')
    print(f'With scopes: {", ".join(scopes)}')

    try:
        # Create boto3 Cognito IDP client
        cognito_client = boto3.client('cognito-idp', region_name='us-east-1')

        # Create the user pool client
        return cognito_client.create_user_pool_client(
            UserPoolId=user_pool_id,
            ClientName=client_name,
            PreventUserExistenceErrors='ENABLED',
            GenerateSecret=True,
            TokenValidityUnits={'AccessToken': 'minutes'},
            AccessTokenValidity=15,
            AllowedOAuthFlowsUserPoolClient=True,
            AllowedOAuthFlows=['client_credentials'],
            AllowedOAuthScopes=scopes,
        )

    except NoCredentialsError:
        print('Error: AWS credentials not found. Please configure your AWS credentials.')
        print("You can use 'aws configure' or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        sys.exit(1)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f'Error creating app client: {error_code} - {error_message}')
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

For more information on CompactConnect and how to integrate your state IT system with ours, see the documentation
here:
https://github.com/csg-org/CompactConnect/blob/development/backend/compact-connect/docs/it_staff_onboarding_instructions.md
"""

    print('\n' + '=' * 60)
    print('EMAIL TEMPLATE (COPY/PASTE INTO EMAIL CLIENT)')
    print('=' * 60)
    print(email_template.strip())
    print('=' * 60)


def main():
    parser = argparse.ArgumentParser(description='Create AWS Cognito app client interactively')
    parser.add_argument('-u', '--user-pool-id', required=True, help='AWS Cognito User Pool ID')

    args = parser.parse_args()

    try:
        print(f'User Pool ID: {args.user_pool_id}\n')

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
