#!/usr/bin/env python3
# ruff: noqa: T201 we use print statements for local scripts
"""
Disaster Recovery - Start Recovery Mode Script

This script throttles all Lambda functions in the account except Disaster Recovery functions
by setting their reserved concurrency to 0. This effectively puts the system into
recovery mode during disaster recovery operations.

Usage:
    python start_recovery_mode.py --environment <environment_name>

Example:
    python start_recovery_mode.py --environment Test
    python start_recovery_mode.py --environment Beta
    python start_recovery_mode.py --environment Prod

Requirements:
    - AWS CLI configured with appropriate credentials
    - boto3 installed
    - Lambda permissions: ListFunctions, PutReservedConcurrencyConfiguration
"""

import argparse
import sys

import boto3
from botocore.exceptions import ClientError


def validate_environment(environment_name: str) -> None:
    """
    Validate the environment name.
    param: environment_name: Environment name to validate

    raise ValueError: If environment name is invalid
    """
    if not environment_name:
        raise ValueError('Environment name cannot be empty')

    valid_environments = ['Test', 'Beta', 'Prod', 'Sandbox']

    if environment_name not in valid_environments:
        raise ValueError(f"Invalid environment '{environment_name}'. Valid options: {valid_environments}")


def throttle_lambda_functions(environment_name: str, dry_run: bool = False) -> dict:
    """
    Throttle all Lambda functions for the specified environment except DR functions.

    param: environment_name: Environment to throttle functions for
    param: dry_run: If True, only simulate the actions without making changes

    return: Dict containing results of the operation
    """
    try:
        validate_environment(environment_name)
    except ValueError as e:
        print(f'Environment validation failed: {e}')
        return {'success': False, 'error': str(e), 'throttled_functions': [], 'skipped_functions': [], 'errors': []}

    lambda_client = boto3.client('lambda')

    # Environment prefix for filtering functions (e.g., "Test-", "Beta-", "Prod-")
    environment_prefix = f'{environment_name}-'

    print(f'{"[DRY RUN] " if dry_run else ""}Starting recovery mode for environment: {environment_name}')
    print(f'Function prefix filter: {environment_prefix}')

    throttled_functions = []
    skipped_functions = []
    errors = []

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
                    skipped_functions.append(
                        {'function_name': function_name, 'reason': 'Does Not Match environment prefix'}
                    )
                    continue

                # Skip Disaster Recovery functions to keep them operational
                if 'DisasterRecovery' in function_name:
                    print(f'Skipping DR function: {function_name}')
                    skipped_functions.append({'function_name': function_name, 'reason': 'Disaster Recovery function'})
                    continue

                if dry_run:
                    print(f'[DRY RUN] Would throttle function: {function_name}')
                    throttled_functions.append(function_name)
                    continue

                try:
                    # Set reserved concurrency to 0 to effectively throttle the function
                    lambda_client.put_function_concurrency(FunctionName=function_name, ReservedConcurrentExecutions=0)

                    print(f'Successfully throttled function: {function_name}')
                    throttled_functions.append(function_name)

                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    error_message = e.response['Error']['Message']

                    error_msg = f'Error throttling {function_name}: {error_code} - {error_message}'
                    print(error_msg)
                    errors.append(error_msg)

                except Exception as e:  # noqa: BLE001
                    error_msg = f'Unexpected error throttling {function_name}: {str(e)}'
                    print(error_msg)
                    errors.append(error_msg)

        if errors:
            print(f'Encountered {len(errors)} errors during throttling process')

        return {
            'success': True,
            'throttled_functions': throttled_functions,
            'throttled_count': len(throttled_functions),
            'skipped_functions': skipped_functions,
            'skipped_count': len(skipped_functions),
            'errors': errors,
            'environment_name': environment_name,
            'environment_prefix': environment_prefix,
            'total_functions_checked': total_functions_checked,
            'dry_run': dry_run,
        }

    except ClientError as e:
        error_msg = f'Failed to list Lambda functions: {str(e)}'
        print(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'throttled_functions': throttled_functions,
            'skipped_functions': skipped_functions,
            'errors': errors + [error_msg],
        }

    except Exception as e:  # noqa: BLE001
        error_msg = f'Unexpected error during recovery mode activation: {str(e)}'
        print(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'throttled_functions': throttled_functions,
            'skipped_functions': skipped_functions,
            'errors': errors + [error_msg],
        }


def main():
    """Main script execution."""
    parser = argparse.ArgumentParser(
        description='Start recovery mode by throttling Lambda functions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
          python start_recovery_mode.py --environment Test
          python start_recovery_mode.py --environment Prod --dry-run
          python start_recovery_mode.py -e Beta
        """,
    )

    parser.add_argument('-e', '--environment', required=True, help='Environment name (test, beta, prod, sandbox)')

    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')

    args = parser.parse_args()

    # Confirmation prompt unless --dry-run is used
    if not args.dry_run:
        print(f'\n⚠️  WARNING: This will throttle ALL Lambda functions in the {args.environment} environment!')
        print('This action will effectively stop all application functionality.')
        print('Only Disaster Recovery functions will remain operational.')
        print('\nThis action should only be performed during disaster recovery operations.')

        response = input(f'\nAre you sure you want to start recovery mode for {args.environment}? (yes/no): ')

        if response.lower() not in ['yes', 'y']:
            print('Operation cancelled.')
            sys.exit(0)

    # Execute the throttling operation
    result = throttle_lambda_functions(args.environment, dry_run=args.dry_run)

    if result['success']:
        action = 'would be throttled' if args.dry_run else 'throttled'
        print(f'\n✅ Recovery mode {"dry run" if args.dry_run else "activation"} completed successfully!')
        print(f'   throttled functions: {result["throttled_functions"]}')
        print(f'   Functions {action}: {result["throttled_count"]}')
        print(f'   Functions skipped: {result["skipped_count"]}')

        if result['errors']:
            print(f'   Errors encountered: {len(result["errors"])}')

        if not args.dry_run:
            print(f"\n🔒 Environment '{args.environment}' is now in recovery mode.")
            print("Remember to run 'end_recovery_mode.py' when disaster recovery is complete!")
    else:
        print(f'\n❌ Recovery mode activation failed: {result.get("error", "Unknown error")}')
        if result.get('errors'):
            print('\nDetailed errors:')
            for error in result['errors']:
                print(f'  - {error}')
        sys.exit(1)


if __name__ == '__main__':
    main()
