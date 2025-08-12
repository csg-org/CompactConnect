#!/usr/bin/env python3
"""
Disaster Recovery - End Maintenance Mode Script

This script removes reserved concurrency throttling from all Lambda functions in the account
to restore normal operations after disaster recovery maintenance mode.

Usage:
    python end_maintenance_mode.py --environment <environment_name>

Example:
    python end_maintenance_mode.py --environment Test
    python end_maintenance_mode.py --environment Beta
    python end_maintenance_mode.py --environment Prod

Requirements:
    - AWS CLI configured with appropriate credentials
    - boto3 installed
    - Lambda permissions: ListFunctions, GetReservedConcurrencyConfiguration, DeleteReservedConcurrencyConfiguration
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Tuple

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


def unthrottle_lambda_functions(environment_name: str) -> Dict:
    """
    Remove reserved concurrency throttling from Lambda functions for the specified environment.
    
    Args:
        environment_name: Environment to unthrottle functions for
        
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
            'unthrottled_functions': [],
            'skipped_functions': [],
            'errors': []
        }
    
    lambda_client = get_lambda_client()
    
    # Environment prefix for filtering functions (e.g., "Test-", "Beta-", "Prod-")
    environment_prefix = f"{environment_name.title()}-"
    
    logger.info(f"Ending maintenance mode for environment: {environment_name}")
    logger.info(f"Function prefix filter: {environment_prefix}")
    
    unthrottled_functions = []
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
                
                # Skip Disaster Recovery functions as they weren't throttled
                if 'DisasterRecovery' in function_name or 'DR-' in function_name:
                    logger.debug(f"Skipping DR function: {function_name}")
                    continue
                
                try:
                    # First, check if the function has reserved concurrency configuration
                    try:
                        get_response = lambda_client.get_reserved_concurrency_configuration(
                            FunctionName=function_name
                        )
                        
                        # If we get here, the function has reserved concurrency configuration
                        reserved_concurrency = get_response.get('ReservedConcurrencyLimit', 'unknown')
                        logger.info(f"Function {function_name} has reserved concurrency: {reserved_concurrency}")
                        
                        # Remove the reserved concurrency configuration
                        lambda_client.delete_reserved_concurrency_configuration(
                            FunctionName=function_name
                        )
                        
                        logger.info(f"Successfully unthrottled function: {function_name}")
                        unthrottled_functions.append(function_name)
                        
                    except ClientError as get_error:
                        if get_error.response['Error']['Code'] == 'ResourceNotFoundException':
                            # Function doesn't have reserved concurrency configuration - this is expected for many functions
                            logger.debug(f"Function {function_name} has no reserved concurrency configuration - skipping")
                            skipped_functions.append({
                                'function_name': function_name,
                                'reason': 'No reserved concurrency configuration'
                            })
                        else:
                            # Some other error occurred while checking
                            error_msg = f"Error checking reserved concurrency for {function_name}: {str(get_error)}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    error_message = e.response['Error']['Message']
                    
                    if error_code == 'ResourceNotFoundException':
                        # Function doesn't have reserved concurrency or function doesn't exist
                        logger.debug(f"No reserved concurrency configuration found for function: {function_name}")
                        skipped_functions.append({
                            'function_name': function_name,
                            'reason': 'No reserved concurrency configuration'
                        })
                    
                    elif error_code == 'TooManyRequestsException':
                        # Rate limiting - wait and retry once
                        logger.warning(f"Rate limited while unthrottling {function_name}, waiting 5 seconds and retrying...")
                        time.sleep(5)
                        
                        try:
                            lambda_client.delete_reserved_concurrency_configuration(
                                FunctionName=function_name
                            )
                            logger.info(f"Successfully unthrottled function on retry: {function_name}")
                            unthrottled_functions.append(function_name)
                        except ClientError as retry_error:
                            if retry_error.response['Error']['Code'] == 'ResourceNotFoundException':
                                logger.debug(f"No reserved concurrency found for {function_name} on retry")
                                skipped_functions.append({
                                    'function_name': function_name,
                                    'reason': 'No reserved concurrency configuration'
                                })
                            else:
                                error_msg = f"Failed to unthrottle {function_name} on retry: {str(retry_error)}"
                                logger.error(error_msg)
                                errors.append(error_msg)
                    
                    else:
                        error_msg = f"Error unthrottling {function_name}: {error_code} - {error_message}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                
                except Exception as e:
                    error_msg = f"Unexpected error unthrottling {function_name}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
        
        logger.info(f"Maintenance mode deactivation completed")
        logger.info(f"Total functions checked: {total_functions_checked}")
        logger.info(f"Functions unthrottled: {len(unthrottled_functions)}")
        logger.info(f"Functions skipped: {len(skipped_functions)}")
        
        if errors:
            logger.warning(f"Encountered {len(errors)} errors during unthrottling process")
        
        return {
            'success': True,
            'unthrottled_functions': unthrottled_functions,
            'unthrottled_count': len(unthrottled_functions),
            'skipped_functions': skipped_functions,
            'skipped_count': len(skipped_functions),
            'errors': errors,
            'environment_name': environment_name,
            'environment_prefix': environment_prefix,
            'total_functions_checked': total_functions_checked
        }
        
    except ClientError as e:
        error_msg = f"Failed to list Lambda functions: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'unthrottled_functions': unthrottled_functions,
            'skipped_functions': skipped_functions,
            'errors': errors + [error_msg]
        }
    
    except Exception as e:
        error_msg = f"Unexpected error during maintenance mode deactivation: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'unthrottled_functions': unthrottled_functions,
            'skipped_functions': skipped_functions,
            'errors': errors + [error_msg]
        }


def main():
    """Main script execution."""
    parser = argparse.ArgumentParser(
        description="End maintenance mode by unthrottling Lambda functions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python end_maintenance_mode.py --environment Test
  python end_maintenance_mode.py -e Beta --confirm
        """
    )
    
    parser.add_argument(
        '-e', '--environment',
        required=True,
        help='Environment name (test, beta, prod, sandbox)'
    )
    
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    # Confirmation prompt unless --confirm is used
    if not args.confirm:
        print(f"\n🔓 This will restore normal Lambda function operations for the {args.environment} environment.")
        print("All reserved concurrency throttling will be removed.")
        print("Application functionality will be restored.")
        
        response = input(f"\nAre you sure you want to end maintenance mode for {args.environment}? (yes/no): ")
        
        if response.lower() not in ['yes', 'y']:
            print("Operation cancelled.")
            sys.exit(0)
    
    # Execute the unthrottling operation
    result = unthrottle_lambda_functions(args.environment)
    

    if result['success']:
        print(f"\n✅ Maintenance mode deactivation completed successfully!")
        print(f"   Functions unthrottled: {result['unthrottled_count']}")
        print(f"   Functions skipped: {result['skipped_count']}")
        
        if result['errors']:
            print(f"   Errors encountered: {len(result['errors'])}")
            
        print(f"\n🔓 Environment '{args.environment}' maintenance mode has been ended.")
        print("Normal application operations have been restored!")
    else:
        print(f"\n❌ Maintenance mode deactivation failed: {result.get('error', 'Unknown error')}")
        if result.get('errors'):
            print("\nDetailed errors:")
            for error in result['errors']:
                print(f"  - {error}")
        sys.exit(1)


if __name__ == '__main__':
    main()
