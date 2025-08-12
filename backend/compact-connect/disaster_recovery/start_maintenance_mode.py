#!/usr/bin/env python3
"""
Disaster Recovery - Start Maintenance Mode Script

This script throttles all Lambda functions in the account except Disaster Recovery functions
by setting their reserved concurrency to 0. This effectively puts the system into
maintenance mode during disaster recovery operations.

Usage:
    python start_maintenance_mode.py --environment <environment_name>

Example:
    python start_maintenance_mode.py --environment Test
    python start_maintenance_mode.py --environment Beta
    python start_maintenance_mode.py --environment Prod

Requirements:
    - AWS CLI configured with appropriate credentials
    - boto3 installed
    - Lambda permissions: ListFunctions, PutReservedConcurrencyConfiguration
"""

import argparse
import sys
import time
from typing import Dict

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def setup_logging():
    """Configure basic logging for the script."""
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def validate_environment(environment_name: str) -> str:
    """
    Validate and normalize the environment name.
    
    Args:
        environment_name: Environment name to validate
        
    Returns:
        Normalized environment name
        
    Raises:
        ValueError: If environment name is invalid
    """
    if not environment_name:
        raise ValueError("Environment name cannot be empty")
    
    valid_environments = ['test', 'beta', 'prod', 'sandbox']
    
    if environment_name.lower() not in valid_environments:
        raise ValueError(f"Invalid environment '{environment_name}'. Valid options: {valid_environments}")
    
    return environment_name.lower()


def get_lambda_client():
    """
    Create and return a Lambda client with error handling.
    
    Returns:
        boto3.client: Lambda client
        
    Raises:
        NoCredentialsError: If AWS credentials are not configured
    """
    try:
        return boto3.client('lambda')
    except NoCredentialsError:
        print("Error: AWS credentials not found. Please configure your AWS CLI or environment variables.")
        print("Run 'aws configure' or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.")
        sys.exit(1)


def throttle_lambda_functions(environment_name: str, dry_run: bool = False) -> Dict:
    """
    Throttle all Lambda functions for the specified environment except DR functions.
    
    Args:
        environment_name: Environment to throttle functions for
        dry_run: If True, only simulate the actions without making changes
        
    Returns:
        Dict containing results of the operation
    """
    logger = setup_logging()
    
    try:
        environment_name = validate_environment(environment_name)
    except ValueError as e:
        logger.error(f"Environment validation failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'throttled_functions': [],
            'skipped_functions': [],
            'errors': []
        }
    
    lambda_client = get_lambda_client()
    
    # Environment prefix for filtering functions (e.g., "Test-", "Beta-", "Prod-")
    environment_prefix = f"{environment_name.title()}-"
    
    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting maintenance mode for environment: {environment_name}")
    logger.info(f"Function prefix filter: {environment_prefix}")
    
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
                    logger.debug(f"Skipping {function_name} - does not match environment prefix {environment_prefix}")
                    continue
                
                # Skip Disaster Recovery functions to keep them operational
                if 'DisasterRecovery' in function_name:
                    logger.info(f"Skipping DR function: {function_name}")
                    skipped_functions.append({
                        'function_name': function_name,
                        'reason': 'Disaster Recovery function'
                    })
                    continue
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would throttle function: {function_name}")
                    throttled_functions.append(function_name)
                    continue
                
                try:
                    # Set reserved concurrency to 0 to effectively throttle the function
                    lambda_client.put_reserved_concurrency_configuration(
                        FunctionName=function_name,
                        ReservedConcurrencyLimit=0
                    )
                    
                    logger.info(f"Successfully throttled function: {function_name}")
                    throttled_functions.append(function_name)
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    error_message = e.response['Error']['Message']
                    
                    if error_code == 'ResourceConflictException':
                        # Function might already have reserved concurrency set
                        logger.warning(f"Function {function_name} already has reserved concurrency configuration")
                        
                        # Try to update the existing configuration
                        try:
                            lambda_client.put_reserved_concurrency_configuration(
                                FunctionName=function_name,
                                ReservedConcurrencyLimit=0
                            )
                            logger.info(f"Successfully updated reserved concurrency for function: {function_name}")
                            throttled_functions.append(function_name)
                        except ClientError as update_error:
                            error_msg = f"Failed to update reserved concurrency for {function_name}: {str(update_error)}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                    
                    elif error_code == 'TooManyRequestsException':
                        # Rate limiting - wait and retry once
                        logger.warning(f"Rate limited while throttling {function_name}, waiting 5 seconds and retrying...")
                        time.sleep(5)
                        
                        try:
                            lambda_client.put_reserved_concurrency_configuration(
                                FunctionName=function_name,
                                ReservedConcurrencyLimit=0
                            )
                            logger.info(f"Successfully throttled function on retry: {function_name}")
                            throttled_functions.append(function_name)
                        except ClientError as retry_error:
                            error_msg = f"Failed to throttle {function_name} on retry: {str(retry_error)}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                    
                    else:
                        error_msg = f"Error throttling {function_name}: {error_code} - {error_message}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                except Exception as e:
                    error_msg = f"Unexpected error throttling {function_name}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Maintenance mode activation completed")
        logger.info(f"Total functions checked: {total_functions_checked}")
        logger.info(f"Functions {'would be ' if dry_run else ''}throttled: {len(throttled_functions)}")
        logger.info(f"Functions skipped: {len(skipped_functions)}")
        
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during throttling process")
        
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
            'dry_run': dry_run
        }
        
    except ClientError as e:
        error_msg = f"Failed to list Lambda functions: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'throttled_functions': throttled_functions,
            'skipped_functions': skipped_functions,
            'errors': errors + [error_msg]
        }
    
    except Exception as e:
        error_msg = f"Unexpected error during maintenance mode activation: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'throttled_functions': throttled_functions,
            'skipped_functions': skipped_functions,
            'errors': errors + [error_msg]
        }


def main():
    """Main script execution."""
    parser = argparse.ArgumentParser(
        description="Start maintenance mode by throttling Lambda functions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_maintenance_mode.py --environment Test
  python start_maintenance_mode.py --environment Prod --dry-run
  python start_maintenance_mode.py -e Beta --confirm
        """
    )
    
    parser.add_argument(
        '-e', '--environment',
        required=True,
        help='Environment name (test, beta, prod, sandbox)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    # Confirmation prompt unless --confirm or --dry-run is used
    if not args.confirm and not args.dry_run:
        print(f"\n⚠️  WARNING: This will throttle ALL Lambda functions in the {args.environment} environment!")
        print("This action will effectively stop all application functionality.")
        print("Only Disaster Recovery functions will remain operational.")
        print("\nThis action should only be performed during disaster recovery operations.")
        
        response = input(f"\nAre you sure you want to start maintenance mode for {args.environment}? (yes/no): ")
        
        if response.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            sys.exit(0)
    
    # Execute the throttling operation
    result = throttle_lambda_functions(args.environment, dry_run=args.dry_run)
    

    if result['success']:
        action = "would be throttled" if args.dry_run else "throttled"
        print(f"\n✅ Maintenance mode {'simulation' if args.dry_run else 'activation'} completed successfully!")
        print(f"   Functions {action}: {result['throttled_count']}")
        print(f"   Functions skipped: {result['skipped_count']}")
        
        if result['errors']:
            print(f"   Errors encountered: {len(result['errors'])}")
            
        if not args.dry_run:
            print(f"\n🔒 Environment '{args.environment}' is now in maintenance mode.")
            print("Remember to run 'end_maintenance_mode.py' when disaster recovery is complete!")
    else:
        print(f"\n❌ Maintenance mode activation failed: {result.get('error', 'Unknown error')}")
        if result.get('errors'):
            print("\nDetailed errors:")
            for error in result['errors']:
                print(f"  - {error}")
        sys.exit(1)


if __name__ == '__main__':
    main()
