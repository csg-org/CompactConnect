#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for local scripts
"""Script to fetch AWS resources names and IDs required for local deployment. Run from `backend/compact-connect`.

To display in human-readable format:
    python fetch_aws_resources.py

To output in .env format:
    python fetch_aws_resources.py --as-env

The CLI must also be configured with AWS credentials that have appropriate access to Cognito and DynamoDB
"""

import argparse

import boto3.session

# Initialize AWS clients
cognito_client = boto3.client('cognito-idp')
cloudformation_client = boto3.client('cloudformation')

# Fetch the AWS region
aws_region = boto3.session.Session().region_name

# List of stack names
STACK_NAMES = [
    'Sandbox-TransactionMonitoringStack',
    'Sandbox-APIStack',
    'Sandbox-IngestStack',
    'Sandbox-PersistentStack',
    'Sandbox-ProviderUsersStack',
]


def get_stack_outputs(stack_name):
    """Fetch outputs from CloudFormation stack"""
    try:
        response = cloudformation_client.describe_stacks(StackName=stack_name)
        stack = response['Stacks'][0]
        return {output['OutputKey']: output['OutputValue'] for output in stack.get('Outputs', [])}
    except Exception as e:  # noqa: BLE001
        print(f'Error retrieving stack {stack_name}: {e}')
        return {}


def get_cognito_details(user_pool_id):
    """Fetch Cognito User Pool Name and Client ID"""
    try:
        pool_response = cognito_client.describe_user_pool(UserPoolId=user_pool_id)
        user_pool_name = pool_response['UserPool']['Name']

        client_response = cognito_client.list_user_pool_clients(UserPoolId=user_pool_id)
        client_id = (
            client_response['UserPoolClients'][0]['ClientId']
            if client_response['UserPoolClients']
            else 'No Client ID Found'
        )

        return user_pool_name, client_id
    except Exception as e:  # noqa: BLE001
        print(f'Error retrieving Cognito details for {user_pool_id}: {e}')
        return 'Unknown', 'Unknown'


def get_cognito_login_url(user_pool_domain):
    """Construct Cognito Hosted UI Login URL"""
    if user_pool_domain:
        return f'https://{user_pool_domain}.auth.{aws_region}.amazoncognito.com/login'
    return None


def extract_table_name(value):
    """Extracts the actual DynamoDB table name from an ARN"""
    if value.startswith('arn:aws:dynamodb:'):
        return value.split(':')[-1].split('/')[-1]
    return value


def fetch_resources():
    """Fetch all required AWS resources"""
    api_gateway_url = None
    provider_details = {}
    staff_details = {}

    for stack in STACK_NAMES:
        outputs = get_stack_outputs(stack)

        for key, value in outputs.items():
            # API Gateway Endpoint
            if 'ApiGateway' in key or 'Endpoint' in key:
                if value.startswith('https://') and 'execute-api' in value:
                    api_gateway_url = value

            # Provider Users (Cognito + DynamoDB)
            if 'ProviderUsers' in key:
                if 'UserPoolId' in key:
                    provider_details['user_pool_id'] = value
                    provider_details['user_pool_name'], provider_details['client_id'] = get_cognito_details(value)
                elif 'UsersDomain' in key:
                    provider_details['login_url'] = get_cognito_login_url(value)

            # Staff Users (Cognito + DynamoDB)
            if 'StaffUsersGreen' in key:
                if 'UserPoolId' in key:
                    staff_details['user_pool_id'] = value
                    staff_details['user_pool_name'], staff_details['client_id'] = get_cognito_details(value)
                elif 'UsersDomain' in key:
                    staff_details['login_url'] = get_cognito_login_url(value)

            # Find associated DynamoDB tables
            if 'Table' in key:
                if 'ProviderTable' in value:
                    provider_details['dynamodb_table'] = extract_table_name(value)
                if 'StaffUsersGreen' in value:
                    staff_details['dynamodb_table'] = extract_table_name(value)

    return api_gateway_url, provider_details, staff_details


def print_human_readable(api_gateway_url, provider_details, staff_details):
    """Prints data in a human-readable format"""
    print('\n\033[1;34m=== AWS Resource Information ===\033[0m\n')  # Blue header

    # Print API Gateway URL
    if api_gateway_url:
        print(f'\033[1;32mAPI Gateway Endpoint:\033[0m {api_gateway_url}\n')  # Green header

    # Print Provider User Pool Details
    print('\033[1;36m=== Provider Users ===\033[0m')  # Cyan header
    if provider_details:
        print(f'\033[1mLogin URL:\033[0m {provider_details.get("login_url", "N/A")}')
        print(f'\033[1mCognito User Pool Name:\033[0m {provider_details.get("user_pool_name", "N/A")}')
        print(f'\033[1mCognito User Pool ID:\033[0m {provider_details.get("user_pool_id", "N/A")}')
        print(f'\033[1mClient ID:\033[0m {provider_details.get("client_id", "N/A")}')
        print(f'\033[1mDynamoDB Table:\033[0m {provider_details.get("dynamodb_table", "N/A")}\n')
    else:
        print('No Provider user pool found.\n')

    # Print Staff User Pool Details
    print('\033[1;36m=== Staff Users ===\033[0m')  # Cyan header
    if staff_details:
        print(f'\033[1mLogin URL:\033[0m {staff_details.get("login_url", "N/A")}')
        print(f'\033[1mCognito User Pool Name:\033[0m {staff_details.get("user_pool_name", "N/A")}')
        print(f'\033[1mCognito User Pool ID:\033[0m {staff_details.get("user_pool_id", "N/A")}')
        print(f'\033[1mClient ID:\033[0m {staff_details.get("client_id", "N/A")}')
        print(f'\033[1mDynamoDB Table:\033[0m {staff_details.get("dynamodb_table", "N/A")}\n')
    else:
        print('No Staff user pool found.\n')


def print_env_format(api_gateway_url, provider_details, staff_details):
    """Prints data in .env format"""
    provider_login_url = provider_details.get('login_url', 'N/A').removesuffix('/login')
    staff_login_url = staff_details.get('login_url', 'N/A').removesuffix('/login')
    staff_client_id = staff_details.get('client_id', 'N/A')
    provider_client_id = provider_details.get('client_id', 'N/A')
    staff_table = staff_details.get('dynamodb_table', 'N/A')
    provider_table = provider_details.get('dynamodb_table', 'N/A')

    print(f'VUE_APP_API_STATE_ROOT={api_gateway_url}')
    print(f'VUE_APP_API_LICENSE_ROOT={api_gateway_url}')
    print(f'VUE_APP_API_USER_ROOT={api_gateway_url}')
    print(f'VUE_APP_COGNITO_REGION={aws_region}')
    print(f'VUE_APP_COGNITO_AUTH_DOMAIN_STAFF={staff_login_url}')
    print(f'VUE_APP_COGNITO_CLIENT_ID_STAFF={staff_client_id}')
    print(f'VUE_APP_COGNITO_AUTH_DOMAIN_LICENSEE={provider_login_url}')
    print(f'VUE_APP_COGNITO_CLIENT_ID_LICENSEE={provider_client_id}')
    print(f'VUE_APP_DYNAMO_TABLE_PROVIDER={provider_table}')
    print(f'VUE_APP_DYNAMO_TABLE_STAFF={staff_table}')


if __name__ == '__main__':
    # Argument parser for --as-env flag
    parser = argparse.ArgumentParser(description='Fetch AWS resource details.')
    parser.add_argument('--as-env', action='store_true', help='Output in .env format')
    args = parser.parse_args()

    # Fetch resources
    api_gateway_url, provider_details, staff_details = fetch_resources()

    # Output in the requested format
    if args.as_env:
        print_env_format(api_gateway_url, provider_details, staff_details)
    else:
        print_human_readable(api_gateway_url, provider_details, staff_details)
