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


def throttle_lambda_functions(environment_name: str, dry_run: bool = False) -> dict:
    """
    Throttle all Lambda functions for the specified environment except DR functions.

    param: environment_name: Environment to throttle functions for
    param: dry_run: If True, only simulate the actions without making changes

    return: Dict containing results of the operation
    """
    lambda_client = boto3.client('lambda')

    # Environment prefix for filtering functions (e.g., "Test-", "Beta-", "Prod-")
    environment_prefix = f'{environment_name}-'

    print(f'{"[DRY RUN] " if dry_run else ""}Starting recovery mode for environment: {environment_name}')
    print(f'Function prefix filter: {environment_prefix}')

    throttled_functions = []
    skipped_functions = []
    errors = []
    failed_functions = []

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
                    failed_functions.append(function_name)

                except Exception as e:  # noqa: BLE001
                    error_msg = f'Unexpected error throttling {function_name}: {str(e)}'
                    print(error_msg)
                    errors.append(error_msg)
                    failed_functions.append(function_name)

        if errors:
            print(f'Encountered {len(errors)} errors during throttling process')

        return {
            'throttled_functions': throttled_functions,
            'skipped_functions': skipped_functions,
            'failed_functions': failed_functions,
            'errors': errors,
            'total_functions_checked': total_functions_checked,
        }

    except ClientError as e:
        error_msg = f'Failed to list Lambda functions: {str(e)}'
        print(error_msg)
        return {
            'error': error_msg,
            'throttled_functions': throttled_functions,
            'skipped_functions': skipped_functions,
            'errors': errors + [error_msg],
        }

    except Exception as e:  # noqa: BLE001
        error_msg = f'Unexpected error during recovery mode activation: {str(e)}'
        print(error_msg)
        return {
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

    parser.add_argument('-e', '--environment', required=True, help='Environment name (Test, Beta, Prod, Sandbox)')

    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')

    args = parser.parse_args()

    try:
        environment_name = validate_environment(args.environment)
    except ValueError as e:
        print(f'Environment validation failed: {e}')
        return

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
    result = throttle_lambda_functions(environment_name, dry_run=args.dry_run)

    action = 'would be throttled' if args.dry_run else 'throttled'
    print(f'   Functions {action}: {len(result["throttled_functions"])}')
    print(f'   Functions skipped: {len(result["skipped_functions"])}')

    # Show failed functions if any
    if result.get('failed_functions') or result.get('errors'):
        print(f'\n❌ Recovery mode {"dry run" if args.dry_run else "activation"} failed')
        print(f'   Functions that failed: {result.get("failed_functions", "unknown")}')
        print(f'   Errors: {result.get("errors", "unknown")}')
    else:
        print(f'\n✅ Recovery mode {"dry run" if args.dry_run else "activation"} completed')
        if not args.dry_run:
            print(f"\n🔒 Environment '{args.environment}' is now in recovery mode.")
            print("Remember to run 'end_recovery_mode.py' when disaster recovery is complete!")


if __name__ == '__main__':
    main()
