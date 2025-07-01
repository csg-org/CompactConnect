#!/usr/bin/env python3
"""
Backup Operations Smoke Test

This script tests the backup and cross-account copy functionality for CompactConnect tables.
It can test either 'provider' or 'ssn' table backup operations.

Usage:
    python test_backup_operations.py provider
    python test_backup_operations.py ssn

The script will:
1. Find the requested table and backup vaults
2. Initiate a backup job
3. Wait for backup completion
4. Initiate a cross-account copy job
5. Wait for copy completion
6. Report the results
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime

import boto3
from botocore.exceptions import ClientError
from smoke_common import SmokeTestFailureException, load_smoke_test_env, logger


class BackupSmokeTest:
    def __init__(self, table_type: str):
        """Initialize the backup smoke test for the specified table type."""
        self.table_type = table_type.lower()
        if self.table_type not in ['provider', 'ssn']:
            raise ValueError("table_type must be 'provider' or 'ssn'")

        # Load environment variables
        load_smoke_test_env()

        # Initialize AWS clients
        self.backup_client = boto3.client('backup')
        self.dynamodb_client = boto3.client('dynamodb')

        # Get table and vault configuration
        self._load_table_config()
        self._load_vault_config()

        logger.info(f'Initialized backup smoke test for {self.table_type} table')

    def _load_table_config(self):
        """Load table configuration based on table type."""
        if self.table_type == 'provider':
            # Provider table configuration
            self.table_name = self._get_env_var('CC_TEST_PROVIDER_DYNAMO_TABLE_NAME')
            self.backup_role_name = self._get_backup_role_name('BackupServiceRole')
            self.local_vault_suffix = 'BackupVault'
            self.cross_account_vault_suffix = 'BackupVault'
        else:  # ssn
            # SSN table configuration
            self.table_name = self._get_env_var('CC_TEST_SSN_DYNAMO_TABLE_NAME')
            self.backup_role_name = self._get_backup_role_name('SSNBackupRole')
            self.local_vault_suffix = 'SSNBackupVault'
            self.cross_account_vault_suffix = 'SSNBackupVault'

        # Build table ARN
        account_id = boto3.client('sts').get_caller_identity()['Account']
        region = boto3.Session().region_name
        self.table_arn = f'arn:aws:dynamodb:{region}:{account_id}:table/{self.table_name}'

        logger.info(f'Table configuration - Name: {self.table_name}, ARN: {self.table_arn}')

    def _load_vault_config(self):
        """Load backup vault configuration."""
        # Get environment name from context or environment
        with open('cdk.json') as f:
            context = json.load(f)['context']

        # Load environment-specific context if available
        try:
            with open('cdk.context.json') as f:
                env_context = json.load(f)
                context.update(env_context)
        except FileNotFoundError:
            logger.warning('No environment-specific context file found, using base context')

        # Try to determine environment name from various sources
        environment_name = context.get('environment_name') or self._get_env_var('ENVIRONMENT_NAME', required=False)

        # Local vault names (in the same account)
        self.local_vault_name = f'CompactConnect-{environment_name}-{self.local_vault_suffix}'

        # Cross-account vault configuration
        backup_config = context.get('ssm_context', {}).get('backup_config', {})
        backup_account_id = backup_config.get('backup_account_id')
        backup_region = backup_config.get('backup_region', 'us-west-2')

        if self.table_type == 'provider':
            cross_account_vault_name = backup_config.get('general_vault_name', 'CompactConnectBackupVault')
        else:  # ssn
            cross_account_vault_name = backup_config.get('ssn_vault_name', 'CompactConnectBackupVault-SSN')

        if not backup_account_id:
            raise SmokeTestFailureException('backup_account_id not found in CDK context configuration')

        self.cross_account_vault_arn = (
            f'arn:aws:backup:{backup_region}:{backup_account_id}:backup-vault:{cross_account_vault_name}'
        )

        logger.info(
            f'Vault configuration - Local: {self.local_vault_name}, Cross-account: {self.cross_account_vault_arn}'
        )

    def _get_backup_role_name(self, role_suffix: str) -> str:
        """Get the backup role name based on environment."""
        # Get environment name from context (should be loaded by _load_vault_config)
        with open('cdk.json') as f:
            context = json.load(f)['context']

        # Load environment-specific context if available
        try:
            with open('cdk.context.json') as f:
                env_context = json.load(f)
                context.update(env_context)
        except FileNotFoundError:
            pass

        environment_name = context.get('environment_name', 'test')
        return f'CompactConnect-{environment_name}-{role_suffix}'

    def _get_env_var(self, var_name: str, required: bool = True) -> str:
        """Get environment variable with error handling."""
        import os

        value = os.environ.get(var_name)
        if required and not value:
            raise SmokeTestFailureException(f'Required environment variable {var_name} not found')
        return value

    def run_backup_test(self) -> dict:
        """Run the complete backup test and return results."""
        results = {
            'table_type': self.table_type,
            'table_name': self.table_name,
            'start_time': datetime.now(UTC).isoformat(),
            'backup_job': {},
            'copy_job': {},
            'success': False,
            'error': None,
        }

        try:
            logger.info(f'Starting backup smoke test for {self.table_type} table')

            # Step 1: Initiate backup
            backup_job_id, recovery_point_arn = self._initiate_backup()
            results['backup_job']['job_id'] = backup_job_id
            results['backup_job']['recovery_point_arn'] = recovery_point_arn

            # Step 2: Wait for backup completion
            backup_success = self._wait_for_backup_completion(backup_job_id)
            results['backup_job']['success'] = backup_success

            if not backup_success:
                raise SmokeTestFailureException('Backup job failed')

            # Step 3: Initiate cross-account copy
            copy_job_id = self._initiate_copy(recovery_point_arn)
            results['copy_job']['job_id'] = copy_job_id

            # Step 4: Wait for copy completion
            copy_success = self._wait_for_copy_completion(copy_job_id)
            results['copy_job']['success'] = copy_success

            if not copy_success:
                raise SmokeTestFailureException('Copy job failed')

            results['success'] = True
            results['end_time'] = datetime.now(UTC).isoformat()

            logger.info(f'Backup smoke test completed successfully for {self.table_type} table')
            return results

        except (SmokeTestFailureException, ClientError, ValueError) as e:
            results['error'] = str(e)
            results['end_time'] = datetime.now(UTC).isoformat()
            logger.error(f'Backup smoke test failed for {self.table_type} table: {str(e)}')
            return results

    def _initiate_backup(self) -> tuple[str, str]:
        """Initiate a backup job and return the job ID and recovery point ARN."""
        logger.info(f'Initiating backup for {self.table_type} table: {self.table_name}')

        # Get the backup role ARN
        account_id = boto3.client('sts').get_caller_identity()['Account']
        backup_role_arn = f'arn:aws:iam::{account_id}:role/{self.backup_role_name}'

        try:
            response = self.backup_client.start_backup_job(
                BackupVaultName=self.local_vault_name,
                ResourceArn=self.table_arn,
                IamRoleArn=backup_role_arn,
                StartWindowMinutes=480,
                CompleteWindowMinutes=10080,
                Lifecycle={'MoveToColdStorageAfterDays': 30, 'DeleteAfterDays': 365},
                RecoveryPointTags={
                    'Purpose': f'Smoke test {self.table_type} backup',
                    'InitiatedBy': 'BackupSmokeTest',
                    'TableType': self.table_type,
                },
            )

            backup_job_id = response['BackupJobId']
            recovery_point_arn = response['RecoveryPointArn']

            logger.info(f'Backup job initiated - Job ID: {backup_job_id}, Recovery Point: {recovery_point_arn}')
            return backup_job_id, recovery_point_arn

        except ClientError as e:
            raise SmokeTestFailureException(f'Failed to initiate backup: {str(e)}') from e

    def _wait_for_backup_completion(self, backup_job_id: str, max_wait_minutes: int = 10) -> bool:
        """Wait for backup job to complete and return success status."""
        logger.info(f'Waiting for backup job {backup_job_id} to complete (max {max_wait_minutes} minutes)')

        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60

        while time.time() - start_time < max_wait_seconds:
            try:
                response = self.backup_client.describe_backup_job(BackupJobId=backup_job_id)
                job_state = response['State']

                logger.info(f'Backup job {backup_job_id} state: {job_state}')

                if job_state == 'COMPLETED':
                    backup_size = response.get('BackupSizeInBytes', 0)
                    logger.info(f'Backup job completed successfully. Size: {backup_size} bytes')
                    return True
                if job_state in ['FAILED', 'ABORTED', 'EXPIRED']:
                    status_message = response.get('StatusMessage', 'No status message')
                    logger.error(f'Backup job failed with state {job_state}: {status_message}')
                    return False
                if job_state in ['CREATED', 'PENDING', 'RUNNING']:
                    # Job is still in progress
                    time.sleep(30)  # Wait 30 seconds before checking again
                    continue
                logger.warning(f'Unknown backup job state: {job_state}')
                time.sleep(30)

            except ClientError as e:
                logger.error(f'Error checking backup job status: {str(e)}')
                return False

        logger.error(f'Backup job {backup_job_id} did not complete within {max_wait_minutes} minutes')
        return False

    def _initiate_copy(self, recovery_point_arn: str) -> str:
        """Initiate a cross-account copy job and return the copy job ID."""
        logger.info(f'Initiating cross-account copy for recovery point: {recovery_point_arn}')

        # Get the backup role ARN
        account_id = boto3.client('sts').get_caller_identity()['Account']
        backup_role_arn = f'arn:aws:iam::{account_id}:role/{self.backup_role_name}'

        try:
            response = self.backup_client.start_copy_job(
                RecoveryPointArn=recovery_point_arn,
                SourceBackupVaultName=self.local_vault_name,
                DestinationBackupVaultArn=self.cross_account_vault_arn,
                IamRoleArn=backup_role_arn,
                Lifecycle={'MoveToColdStorageAfterDays': 30, 'DeleteAfterDays': 365},
            )

            copy_job_id = response['CopyJobId']
            logger.info(f'Copy job initiated - Job ID: {copy_job_id}')
            return copy_job_id

        except ClientError as e:
            raise SmokeTestFailureException(f'Failed to initiate copy job: {str(e)}') from e

    def _wait_for_copy_completion(self, copy_job_id: str, max_wait_minutes: int = 15) -> bool:
        """Wait for copy job to complete and return success status."""
        logger.info(f'Waiting for copy job {copy_job_id} to complete (max {max_wait_minutes} minutes)')

        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60

        while time.time() - start_time < max_wait_seconds:
            try:
                response = self.backup_client.describe_copy_job(CopyJobId=copy_job_id)
                job_state = response['CopyJob']['State']

                logger.info(f'Copy job {copy_job_id} state: {job_state}')

                if job_state == 'COMPLETED':
                    backup_size = response['CopyJob'].get('BackupSizeInBytes', 0)
                    destination_arn = response['CopyJob'].get('DestinationRecoveryPointArn', 'Unknown')
                    logger.info(
                        f'Copy job completed successfully. Size: {backup_size} bytes, Destination: {destination_arn}'
                    )
                    return True
                if job_state in ['FAILED', 'PARTIAL']:
                    status_message = response['CopyJob'].get('StatusMessage', 'No status message')
                    logger.error(f'Copy job failed with state {job_state}: {status_message}')
                    return False
                if job_state in ['CREATED', 'RUNNING']:
                    # Job is still in progress
                    time.sleep(45)  # Wait 45 seconds before checking again (copy jobs take longer)
                    continue
                logger.warning(f'Unknown copy job state: {job_state}')
                time.sleep(45)

            except ClientError as e:
                logger.error(f'Error checking copy job status: {str(e)}')
                return False

        logger.error(f'Copy job {copy_job_id} did not complete within {max_wait_minutes} minutes')
        return False


def main():
    """Main function to run the backup smoke test."""
    parser = argparse.ArgumentParser(
        description='Run backup operations smoke test for CompactConnect tables',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('table_type', choices=['provider', 'ssn'], help='Type of table to test backup operations for')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        import logging

        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Initialize and run the backup test
        backup_test = BackupSmokeTest(args.table_type)
        results = backup_test.run_backup_test()

        # Log results using logger instead of print
        logger.info('\n' + '=' * 60)
        logger.info(f'BACKUP SMOKE TEST RESULTS - {args.table_type.upper()} TABLE')
        logger.info('=' * 60)
        logger.info(f'Table Name: {results["table_name"]}')
        logger.info(f'Start Time: {results["start_time"]}')
        logger.info(f'End Time: {results.get("end_time", "N/A")}')
        logger.info(f'Overall Success: {results["success"]}')

        if results.get('error'):
            logger.error(f'Error: {results["error"]}')

        logger.info('\nBackup Job:')
        backup_job = results.get('backup_job', {})
        logger.info(f'  Job ID: {backup_job.get("job_id", "N/A")}')
        logger.info(f'  Recovery Point ARN: {backup_job.get("recovery_point_arn", "N/A")}')
        logger.info(f'  Success: {backup_job.get("success", "N/A")}')

        logger.info('\nCopy Job:')
        copy_job = results.get('copy_job', {})
        logger.info(f'  Job ID: {copy_job.get("job_id", "N/A")}')
        logger.info(f'  Success: {copy_job.get("success", "N/A")}')

        logger.info('=' * 60)

        # Exit with appropriate code
        sys.exit(0 if results['success'] else 1)

    except (SmokeTestFailureException, ValueError, FileNotFoundError) as e:
        logger.error(f'Backup smoke test failed with exception: {str(e)}')
        logger.error(f'\nERROR: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
