#!/usr/bin/env python3
"""Script to bootstrap staff users in a sandbox environment with predefined credentials to simplify testing.
Run this script from `backend/compact-connect`.

The AWS CLI must be configured with AWS credentials that have appropriate access to Cognito and DynamoDB.

Configuration is loaded from `sandbox_bootstrap_config.json` in the same directory.
"""
# ruff: noqa T201

import json
import os
import sys
from argparse import ArgumentParser

# Add parent directory to Python path to find common modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sandbox_bootstrap_config import SandboxBootstrapConfig
from sandbox_bootstrap_api import SandboxBootstrapAPI

# Import common modules for user creation
import boto3
from botocore.exceptions import ClientError


def create_cognito_user(email: str, permanent_password: str | None = None) -> str:
    """Create a Cognito user with the given email address and password."""

    def get_sub_from_attributes(user_attributes: list):
        for attribute in user_attributes:
            if attribute['Name'] == 'sub':
                return attribute['Value']
        raise ValueError('Failed to find user sub!')

    cognito_client = boto3.client('cognito-idp')
    user_pool_id = os.environ['USER_POOL_ID']

    try:
        kwargs = {'TemporaryPassword': permanent_password} if permanent_password is not None else {}
        user_data = cognito_client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            UserAttributes=[{'Name': 'email', 'Value': email}],
            DesiredDeliveryMediums=['EMAIL'],
            **kwargs,
        )

        if permanent_password is not None:
            cognito_client.admin_set_user_password(
                UserPoolId=user_pool_id, Username=email, Password=permanent_password, Permanent=True
            )
        return get_sub_from_attributes(user_data['User']['Attributes'])

    except ClientError as e:
        if e.response['Error']['Code'] == 'UsernameExistsException':
            print('   ⏭️  User already exists, using existing user')
            user_data = cognito_client.admin_get_user(UserPoolId=user_pool_id, Username=email)
            return get_sub_from_attributes(user_data['UserAttributes'])
        else:
            raise Exception(f'Failed to create user: {e.response["Error"]["Message"]}')


def create_user_record(user_id: str, compact: str, user_attributes: dict, permissions: dict):
    """Create a user record in DynamoDB."""
    dynamodb = boto3.resource('dynamodb')
    user_table = dynamodb.Table(os.environ['USER_TABLE_NAME'])  # type: ignore

    # Check if user record already exists
    try:
        existing_record = user_table.get_item(
            Key={
                'pk': f'USER#{user_id}',
                'sk': f'USER#{user_id}',
            }
        )
        if 'Item' in existing_record:
            print(f'   ⏭️  User record already exists, skipping...')
            return
    except Exception as e:
        print(f'   ⚠️  Warning: Could not check for existing user record: {str(e)}')

    # Simple user record structure - no need for full schema validation in bootstrap
    user_record = {
        'pk': f'USER#{user_id}',
        'sk': f'USER#{user_id}',
        'type': 'user',
        'userId': user_id,
        'status': 'ACTIVE',
        'compact': compact,
        'attributes': user_attributes,
        'permissions': permissions,
    }

    user_table.put_item(Item=user_record)


def bootstrap_board_ed_user(compact: str, jurisdiction: str, email_username: str, email_domain: str) -> str:
    """Create a board editor user for a specific jurisdiction.

    :param compact: The compact abbreviation
    :param jurisdiction: The jurisdiction abbreviation
    :param email_username: The email username part
    :param email_domain: The email domain part
    :return: The created user's email address
    """
    email = f'{email_username}+board-ed-{compact}-{jurisdiction}@{email_domain}'
    user_attributes = {
        'email': email,
        'familyName': f'{compact.upper()}-{jurisdiction.upper()}',
        'givenName': 'TEST BOARD ED',
    }

    print(f'   🔐 Creating Cognito user...')
    user_id = create_cognito_user(email=email, permanent_password='Test12345678')  # noqa: S105

    permissions = {'actions': {'read'}, 'jurisdictions': {jurisdiction: {'write', 'admin'}}}

    print(f'   💾 Creating user record...')
    create_user_record(user_id, compact, user_attributes, permissions)
    return email


def bootstrap_compact_ed_user(compact: str, email_username: str, email_domain: str) -> str:
    """Create a compact editor user.

    :param compact: The compact abbreviation
    :param email_username: The email username part
    :param email_domain: The email domain part
    :return: The created user's email address
    """
    email = f'{email_username}+compact-ed-{compact}@{email_domain}'
    user_attributes = {'email': email, 'familyName': compact.upper(), 'givenName': 'TEST COMPACT ED'}

    print(f'   🔐 Creating Cognito user...')
    user_id = create_cognito_user(email=email, permanent_password='Test12345678')  # noqa: S105

    permissions = {'actions': {'read', 'admin'}, 'jurisdictions': {}}

    print(f'   💾 Creating user record...')
    create_user_record(user_id, compact, user_attributes, permissions)
    return email


def get_license_types_for_compact(compact: str) -> list:
    """Get license types for a compact from the CDK context.

    :param compact: The compact abbreviation
    :return: List of license type configurations
    """
    with open('cdk.json') as context_file:
        cdk_context = json.load(context_file)['context']
        license_types = cdk_context.get('license_types', {}).get(compact, [])

    if not license_types:
        raise Exception(f'No license types found for compact {compact}')

    return license_types


def create_privilege_fees(license_types: list, default_amount: float, military_rate: float) -> list:
    """Create privilege fee configurations for all license types.

    :param license_types: List of license type configurations
    :param default_amount: Default fee amount
    :param military_rate: Military rate amount
    :return: List of privilege fee configurations
    """
    privilege_fees = []
    for lt in license_types:
        privilege_fees.append(
            {'licenseTypeAbbreviation': lt['abbreviation'], 'amount': default_amount, 'militaryRate': military_rate}
        )
    return privilege_fees


def main():
    """Main function to bootstrap the sandbox environment."""
    parser = ArgumentParser(
        description='Bootstraps a sandbox environment with a static set of staff users using configuration from JSON file.',
        epilog='Configuration is loaded from sandbox_bootstrap_config.json in the same directory.',
    )
    parser.add_argument(
        '--config-file',
        help='Path to configuration JSON file (default: sandbox_bootstrap_config.json in script directory)',
        default=None,
    )
    args = parser.parse_args()

    try:
        print('🚀 Starting Sandbox Bootstrap Process')
        print('=' * 50)

        # Load configuration
        print('📋 Loading configuration...')
        config = SandboxBootstrapConfig(args.config_file)
        print(f'   ✓ Base email: {config.base_email}')
        print(f'   ✓ Compact: {config.compact_abbreviation}')
        print(f'   ✓ States: {", ".join(config.additional_states)}')

        # Initialize API helper
        print('\n🔧 Initializing API connection...')
        api = SandboxBootstrapAPI(config)

        # Get email parts
        email_username, email_domain = config.email_parts

        # Create staff users
        print('\n👥 Creating Staff Users')
        print('-' * 30)
        emails = {}
        for i, state in enumerate(config.additional_states, 1):
            print(f'   [{i}/{len(config.additional_states)}] Creating board admin for {state.upper()}...')
            email = bootstrap_board_ed_user(
                compact=config.compact_abbreviation,
                jurisdiction=state,
                email_username=email_username,
                email_domain=email_domain,
            )
            emails[state] = email
            print(f'   ✓ Board admin for {state.upper()}: {email}\n')

        print(f'   Creating compact admin...')
        compact_email = bootstrap_compact_ed_user(
            compact=config.compact_abbreviation, email_username=email_username, email_domain=email_domain
        )
        print(f'   ✓ Compact admin: {compact_email}')

        # Configure the compact initially (without licensee registration)
        print('\n⚙️  Configuring Compact')
        print('-' * 30)
        print('   Step 1: Initial configuration (fees and settings)...')
        api.configure_compact(
            compact=config.compact_abbreviation, staff_user_email=compact_email, enable_licensee_registration=False
        )

        # Upload authorize.net credentials
        print('\n   Step 2: Uploading payment processor credentials...')
        api.upload_authorize_net_credentials(compact=config.compact_abbreviation, staff_user_email=compact_email)

        # Enable licensee registration
        print('\n   Step 3: Enabling licensee registration...')
        api.configure_compact(
            compact=config.compact_abbreviation, staff_user_email=compact_email, enable_licensee_registration=True
        )

        # Get license types and create privilege fees
        print('\n💰 Setting up privilege fees...')
        license_types = get_license_types_for_compact(config.compact_abbreviation)
        privilege_fees = create_privilege_fees(
            license_types=license_types,
            default_amount=config.privilege_fees['default_amount'],
            military_rate=config.privilege_fees['military_rate'],
        )
        print(f'   ✓ Created {len(privilege_fees)} privilege fee configurations')

        # Configure jurisdictions
        print('\n🏛️  Configuring Jurisdictions')
        print('-' * 30)
        for i, (state, email) in enumerate(emails.items(), 1):
            print(f'   [{i}/{len(emails)}] Configuring {state.upper()}...')
            api.configure_jurisdiction(
                compact=config.compact_abbreviation,
                jurisdiction=state,
                staff_user_email=email,
                privilege_fees=privilege_fees,
            )

        # Set up test provider
        print('\n👤 Setting Up Test Provider')
        print('-' * 30)

        # Create provider user in Cognito first
        first_state = config.additional_states[0]
        print(f'   Creating provider user in Cognito...')
        api.create_test_provider_user(email=config.base_email)

        # Upload license record
        print(f'   Uploading license record in {first_state.upper()}...')
        api.upload_license_record(
            compact=config.compact_abbreviation, jurisdiction=first_state, staff_user_email=emails[first_state]
        )

        # Link provider to license record using staff API
        print(f'   Linking provider to license record...')
        api.link_provider_to_license_record(
            compact=config.compact_abbreviation, jurisdiction=first_state, staff_user_email=emails[first_state]
        )

        print('\n' + '=' * 50)
        print('🎉 Sandbox Bootstrap Completed Successfully!')
        print('=' * 50)
        print(f'📊 Summary:')
        print(f'   • Compact: {config.compact_abbreviation.upper()}')
        print(f'   • States configured: {", ".join(state.upper() for state in config.additional_states)}')
        print(f'   • Compact admin: {compact_email}')
        print(f'   • Board admins: {len(emails)} users created')
        print(f'   • Privilege fees: {len(privilege_fees)} configurations')
        print(f'   • Test provider: {config.base_email}')
        print(f'   • Test licensee: Registered in {first_state.upper()}')
        print('\n✨ Your sandbox environment is ready for testing!')
        print(f'🔑 Provider login: {config.base_email} / Test12345678')

    except Exception as e:
        print('\n' + '=' * 50)
        print('💥 Bootstrap Failed')
        print('=' * 50)
        print(f'❌ Error: {str(e)}')
        print('\n🔧 Please check your configuration and try again.')
        sys.exit(1)


if __name__ == '__main__':
    main()
