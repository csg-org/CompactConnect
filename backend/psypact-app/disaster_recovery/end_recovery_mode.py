#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for local scripts
"""
Disaster Recovery - End Recovery Mode Script

This script removes reserved concurrency throttling from all Lambda functions in the account
to restore normal operations after disaster recovery mode.

Usage:
    python end_recovery_mode.py --environment <environment_name>

Example:
    python end_recovery_mode.py --environment Test
    python end_recovery_mode.py --environment Beta
    python end_recovery_mode.py --environment Prod

Requirements:
    - AWS CLI configured with appropriate credentials
    - boto3 installed
    - Lambda permissions: ListFunctions, GetReservedConcurrencyConfiguration, DeleteReservedConcurrencyConfiguration
"""

import argparse
import sys

import boto3
from botocore.exceptions import ClientError


def validate_environment(environment_name: str) -> str:
    """
    Validate and normalize the environment name.
    param: environment_name: Environment name to validate

    return: Normalized environment name in title case
    raise ValueError: If environment name is invalid
    """
    if not environment_name:
        raise ValueError('Environment name cannot be empty')

    # Normalize to title case for validation and consistency
    normalized = environment_name.strip().title()
    valid_environments = ['Test', 'Beta', 'Prod', 'Sandbox']

    if normalized not in valid_environments:
        raise ValueError(f"Invalid environment '{environment_name}'. Valid options: {valid_environments}")

    return normalized


def unthrottle_lambda_functions(environment_name: str) -> dict:
    """
    Remove reserved concurrency throttling from Lambda functions for the specified environment.

    param: environment_name: Environment to unthrottle functions for

    return: Dict containing results of the operation
    """
    lambda_client = boto3.client('lambda')

    # Environment prefix for filtering functions (e.g., "Test-", "Beta-", "Prod-")
    environment_prefix = f'{environment_name}-'

    print(f'Ending recovery mode for environment: {environment_name}')
    print(f'Function prefix filter: {environment_prefix}')

    unthrottled_functions = []
    skipped_functions = []
    errors = []
    failed_function_names = []

    try:
        # Use paginator to handle accounts with many Lambda functions
        paginator = lambda_client.get_paginator('list_functions')
        total_functions_checked = 0

        for page in paginator.paginate():
            for function in page['Functions']:
                function_name = function['FunctionName']
                total_functions_checked += 1

                # Skip functions that don't match the environment prefix
                if not function_name.startswith(environment_prefix):
                    print(f'Skipping {function_name} - does not match environment prefix {environment_prefix}')
                    skipped_functions.append(function_name)
                    continue

                # Skip Disaster Recovery functions as they weren't throttled
                if 'DisasterRecovery' in function_name:
                    print(f'Skipping DR function: {function_name}')
                    skipped_functions.append(function_name)
                    continue

                try:
                    # Remove the reserved concurrency configuration
                    lambda_client.delete_function_concurrency(FunctionName=function_name)

                    print(f'Successfully unthrottled function: {function_name}')
                    unthrottled_functions.append(function_name)

                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    error_message = e.response['Error']['Message']
                    error_msg = f'Error unthrottling {function_name}: {error_code} - {error_message}'
                    print(error_msg)
                    errors.append(error_msg)
                    failed_function_names.append(function_name)

                except Exception as e:  # noqa: BLE001
                    error_msg = f'Unexpected error unthrottling {function_name}: {str(e)}'
                    print(error_msg)
                    errors.append(error_msg)
                    failed_function_names.append(function_name)

        return {
            'unthrottled_functions': unthrottled_functions,
            'skipped_functions': skipped_functions,
            'failed_functions': failed_function_names,
            'errors': errors,
            'total_functions_checked': total_functions_checked,
        }

    except ClientError as e:
        error_msg = f'Failed to list Lambda functions: {str(e)}'
        print(error_msg)
        return {
            'unthrottled_functions': unthrottled_functions,
            'skipped_functions': skipped_functions,
            'errors': errors + [error_msg],
        }

    except Exception as e:  # noqa: BLE001
        error_msg = f'Unexpected error during recovery mode deactivation: {str(e)}'
        print(error_msg)
        return {
            'unthrottled_functions': unthrottled_functions,
            'skipped_functions': skipped_functions,
            'errors': errors + [error_msg],
        }


def main():
    """Main script execution."""
    parser = argparse.ArgumentParser(
        description='End recovery mode by unthrottling Lambda functions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
          python end_recovery_mode.py --environment Test
          python end_recovery_mode.py -e Beta
        """,
    )

    parser.add_argument('-e', '--environment', required=True, help='Environment name (Test, Beta, Prod, Sandbox)')

    args = parser.parse_args()

    try:
        environment_name = validate_environment(args.environment)
    except ValueError as e:
        print(f'Environment validation failed: {e}')
        return

    # Confirmation prompt
    print(f'\n🔓 This will restore normal Lambda function operations for the {args.environment} environment.')
    print('All reserved concurrency throttling will be removed.')
    print('Application functionality will be restored.')

    response = input(f'\nAre you sure you want to end recovery mode for {args.environment}? (yes/no): ')

    if response.lower() not in ['yes', 'y']:
        print('Operation cancelled.')
        sys.exit(0)

    # Execute the unthrottling operation
    result = unthrottle_lambda_functions(environment_name)

    print(f'   Functions unthrottled: {len(result["unthrottled_functions"])}')
    print(f'   Functions skipped: {len(result["skipped_functions"])}')

    if result.get('failed_functions') or result.get('errors'):
        print(f'   Functions that failed: {result.get("failed_functions", "unknown")}')
        print(f'   Errors: {result.get("errors", "unknown")}')
    else:
        print('\n✅ Recovery mode deactivation completed')
        print(f"\n🔓 Environment '{args.environment}' recovery mode has been ended.")
        print('Normal application operations have been restored!')


if __name__ == '__main__':
    main()
