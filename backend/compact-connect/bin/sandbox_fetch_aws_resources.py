#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for local scripts
"""Script to fetch AWS resources names and IDs required for local deployment. Run from `backend/compact-connect`.

To display in human-readable format:
    python fetch_aws_resources.py

To output in .env format:
    python fetch_aws_resources.py --as-env

To output in smoke test config format:
    python fetch_aws_resources.py --as-smoke-test-config

The CLI must also be configured with AWS credentials that have appropriate access to Cognito and DynamoDB
"""

import argparse
import json

import boto3.session

# Initialize AWS clients
cognito_client = boto3.client('cognito-idp')
cloudformation_client = boto3.client('cloudformation')
lambda_client = boto3.client('lambda')

# Fetch the AWS region
aws_region = boto3.session.Session().region_name

# List of stack names
STACK_NAMES = [
    'Sandbox-TransactionMonitoringStack',
    'Sandbox-APIStack',
    'Sandbox-IngestStack',
    'Sandbox-PersistentStack',
    'Sandbox-StateAuthStack',
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


def get_lambda_function_name(function_arn):
    """Extract Lambda function name from ARN"""
    if function_arn.startswith('arn:aws:lambda:'):
        return function_arn.split(':')[-1]
    return function_arn


def fetch_resources():
    """Fetch all required AWS resources"""
    api_gateway_url = None
    state_api_gateway_url = None
    provider_details = {}
    staff_details = {}
    dynamodb_tables = {}
    lambda_functions = {}
    state_auth_details = {}

    for stack in STACK_NAMES:
        outputs = get_stack_outputs(stack)

        for key, value in outputs.items():
            # API Gateway Endpoint
            if 'ApiGateway' in key or 'Endpoint' in key:
                if value.startswith('https://') and 'execute-api' in value:
                    if 'State' in key:
                        state_api_gateway_url = value
                    else:
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

            # State Auth (Cognito)
            if 'StateAuth' in key:
                if 'UserPoolId' in key:
                    state_auth_details['user_pool_id'] = value
                    state_auth_details['user_pool_name'], state_auth_details['client_id'] = get_cognito_details(value)
                elif 'AuthUrl' in key:
                    state_auth_details['auth_url'] = value

            # DynamoDB Tables
            if 'Table' in key:
                table_name = extract_table_name(value)
                if 'ProviderTable' in value:
                    dynamodb_tables['provider'] = table_name
                    provider_details['dynamodb_table'] = table_name
                elif 'StaffUsersGreen' in value:
                    dynamodb_tables['staff_users'] = table_name
                    staff_details['dynamodb_table'] = table_name
                elif 'CompactConfig' in value:
                    dynamodb_tables['compact_configuration'] = table_name
                elif 'RateLimiting' in value:
                    dynamodb_tables['rate_limiting'] = table_name
                elif 'SSN' in value:
                    dynamodb_tables['ssn'] = table_name
                elif 'DataEvent' in value:
                    dynamodb_tables['data_events'] = table_name

            # Lambda Functions
            if 'Lambda' in key and 'Function' in key:
                function_name = get_lambda_function_name(value)
                if 'GetProviderSSN' in key:
                    lambda_functions['get_provider_ssn'] = function_name

    return api_gateway_url, state_api_gateway_url, provider_details, staff_details, dynamodb_tables, lambda_functions, state_auth_details


def print_human_readable(api_gateway_url, state_api_gateway_url, provider_details, staff_details, dynamodb_tables, lambda_functions, state_auth_details):
    """Prints data in a human-readable format"""
    print('\n\033[1;34m=== AWS Resource Information ===\033[0m\n')  # Blue header

    # Print API Gateway URLs
    if api_gateway_url:
        print(f'\033[1;32mAPI Gateway Endpoint:\033[0m {api_gateway_url}\n')  # Green header
    if state_api_gateway_url:
        print(f'\033[1;32mState API Gateway Endpoint:\033[0m {state_api_gateway_url}\n')  # Green header

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

    # Print State Auth Details
    print('\033[1;36m=== State Auth ===\033[0m')  # Cyan header
    if state_auth_details:
        print(f'\033[1mAuth URL:\033[0m {state_auth_details.get("auth_url", "N/A")}')
        print(f'\033[1mCognito User Pool Name:\033[0m {state_auth_details.get("user_pool_name", "N/A")}')
        print(f'\033[1mCognito User Pool ID:\033[0m {state_auth_details.get("user_pool_id", "N/A")}')
        print(f'\033[1mClient ID:\033[0m {state_auth_details.get("client_id", "N/A")}\n')
    else:
        print('No State Auth user pool found.\n')

    # Print DynamoDB Tables
    print('\033[1;36m=== DynamoDB Tables ===\033[0m')  # Cyan header
    for table_type, table_name in dynamodb_tables.items():
        print(f'\033[1m{table_type.replace("_", " ").title()}:\033[0m {table_name}')
    print()

    # Print Lambda Functions
    print('\033[1;36m=== Lambda Functions ===\033[0m')  # Cyan header
    for func_type, func_name in lambda_functions.items():
        print(f'\033[1m{func_type.replace("_", " ").title()}:\033[0m {func_name}')
    print()


def print_env_format(api_gateway_url, state_api_gateway_url, provider_details, staff_details, dynamodb_tables, lambda_functions, state_auth_details):
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


def print_smoke_test_config(api_gateway_url, state_api_gateway_url, provider_details, staff_details, dynamodb_tables, lambda_functions, state_auth_details):
    """Prints data in smoke test config format"""
    config = {
        "CC_TEST_API_BASE_URL": api_gateway_url or "https://api.test.compactconnect.org",
        "CC_TEST_STATE_API_BASE_URL": state_api_gateway_url or "https://state-api.test.compactconnect.org",
        "CC_TEST_STATE_AUTH_URL": state_auth_details.get('auth_url', "N/A"),
        "CC_TEST_COGNITO_STATE_AUTH_USER_POOL_ID": state_auth_details.get('user_pool_id', "N/A"),
        "CC_TEST_PROVIDER_DYNAMO_TABLE_NAME": dynamodb_tables.get('provider', "N/A"),
        "CC_TEST_COMPACT_CONFIGURATION_DYNAMO_TABLE_NAME": dynamodb_tables.get('compact_configuration', "N/A"),
        "CC_TEST_RATE_LIMITING_DYNAMO_TABLE_NAME": dynamodb_tables.get('rate_limiting', "N/A"),
        "CC_TEST_GET_PROVIDER_SSN_LAMBDA_NAME": lambda_functions.get('get_provider_ssn', "N/A"),
        "CC_TEST_SSN_DYNAMO_TABLE_NAME": dynamodb_tables.get('ssn', "N/A"),
        "CC_TEST_DATA_EVENT_DYNAMO_TABLE_NAME": dynamodb_tables.get('data_events', "N/A"),
        "CC_TEST_STAFF_USER_DYNAMO_TABLE_NAME": dynamodb_tables.get('staff_users', "N/A"),
        "CC_TEST_COGNITO_STAFF_USER_POOL_ID": staff_details.get('user_pool_id', "N/A"),
        "CC_TEST_COGNITO_STAFF_USER_POOL_CLIENT_ID": staff_details.get('client_id', "N/A"),
        "CC_TEST_COGNITO_PROVIDER_USER_POOL_ID": provider_details.get('user_pool_id', "N/A"),
        "CC_TEST_COGNITO_PROVIDER_USER_POOL_CLIENT_ID": provider_details.get('client_id', "N/A"),
        "CC_TEST_PROVIDER_USER_USERNAME": "example@example.com",
        "CC_TEST_PROVIDER_USER_PASSWORD": "examplePassword",
        "ENVIRONMENT_NAME": "your_environment_name",
        "SANDBOX_AUTHORIZE_NET_API_LOGIN_ID": "your_sandbox_api_login_id",
        "SANDBOX_AUTHORIZE_NET_TRANSACTION_KEY": "your_sandbox_transaction_key",
    }

    print(json.dumps(config, indent=2))


if __name__ == '__main__':
    # Argument parser for output format flags
    parser = argparse.ArgumentParser(description='Fetch AWS resource details.')
    parser.add_argument('--as-env', action='store_true', help='Output in .env format')
    parser.add_argument('--as-smoke-test-config', action='store_true', help='Output in smoke test config format')
    args = parser.parse_args()

    # Fetch resources
    api_gateway_url, state_api_gateway_url, provider_details, staff_details, dynamodb_tables, lambda_functions, state_auth_details = fetch_resources()

    # Output in the requested format
    if args.as_env:
        print_env_format(api_gateway_url, state_api_gateway_url, provider_details, staff_details, dynamodb_tables, lambda_functions, state_auth_details)
    elif args.as_smoke_test_config:
        print_smoke_test_config(api_gateway_url, state_api_gateway_url, provider_details, staff_details, dynamodb_tables, lambda_functions, state_auth_details)
    else:
        print_human_readable(api_gateway_url, state_api_gateway_url, provider_details, staff_details, dynamodb_tables, lambda_functions, state_auth_details)
