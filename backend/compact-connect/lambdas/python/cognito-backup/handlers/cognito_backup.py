"""
Cognito user pool backup handlers.

This module contains the CognitoBackupExporter class and related functionality
for exporting Cognito user pool data to S3 for backup purposes.
"""

import json
from datetime import UTC, datetime
from typing import Any

import boto3
from aws_lambda_powertools.logging import Logger
from botocore.exceptions import ClientError

# Configure logging
logger = Logger()


class CognitoBackupExporter:
    """
    Exports Cognito user pool data to S3 for backup purposes.

    This class handles the export of all users from a single Cognito user pool,
    storing each user as a separate JSON file with comprehensive user data
    including attributes, status, and metadata.
    """

    def __init__(self, user_pool_id: str, backup_bucket_name: str):
        """
        Initialize the Cognito backup exporter.

        :param user_pool_id: The ID of the Cognito user pool to export
        :param backup_bucket_name: The name of the S3 bucket to store exports
        """
        self.user_pool_id = user_pool_id
        self.backup_bucket_name = backup_bucket_name

        # Initialize AWS clients
        self.cognito_client = boto3.client('cognito-idp')
        self.s3_client = boto3.client('s3')

        logger.info('Initialized Cognito backup exporter', user_pool_id=user_pool_id, backup_bucket=backup_bucket_name)

    def export_user_pool(self) -> dict[str, Any]:
        """
        Export all users from the specified user pool to S3.

        :return: Dictionary containing export results and metadata
        """
        logger.info('Starting user pool export', user_pool_id=self.user_pool_id)

        export_timestamp = datetime.now(tz=UTC).isoformat()
        users_exported = 0

        try:
            # Export all users from the user pool
            users_exported = self._export_user_pool(export_timestamp)

            logger.info(
                'Successfully exported users from user pool',
                users_exported=users_exported,
                user_pool_id=self.user_pool_id,
            )

            return {
                'user_pool_id': self.user_pool_id,
                'users_exported': users_exported,
                'export_timestamp': export_timestamp,
                'backup_bucket': self.backup_bucket_name,
                'status': 'success',
            }

        except Exception as e:
            logger.error('Failed to export user pool', user_pool_id=self.user_pool_id, error=str(e))
            raise

    def _export_user_pool(self, export_timestamp: str) -> int:
        """
        Export all users from the user pool with pagination support.

        :param export_timestamp: ISO timestamp for the export
        :return: Number of users exported
        """
        users_exported = 0
        pagination_token = None

        while True:
            # List users with pagination
            list_params = {
                'UserPoolId': self.user_pool_id,
                'Limit': 60,  # Maximum allowed by Cognito
            }

            if pagination_token:
                list_params['PaginationToken'] = pagination_token

            try:
                response = self.cognito_client.list_users(**list_params)
                users = response.get('Users', [])

                # Export each user
                for user in users:
                    try:
                        self._export_single_user(user, export_timestamp)
                        users_exported += 1
                    except (ClientError, ValueError) as e:
                        logger.error('Failed to export user', username=user.get('Username', 'unknown'), error=str(e))
                        raise

                # Check for more pages
                pagination_token = response.get('PaginationToken')
                if not pagination_token:
                    break

            except ClientError as e:
                logger.error('Cognito API error', error=str(e))
                raise

        return users_exported

    def _export_single_user(self, user_data: dict[str, Any], export_timestamp: str) -> None:
        """
        Export a single user to S3 as a JSON file.

        :param user_data: User data from Cognito
        :param export_timestamp: ISO timestamp for the export
        """
        username = user_data.get('Username')
        if not username:
            logger.warning('Skipping user without username')
            return

        # Create object key based on username
        object_key = f'cognito-exports/{username}.json'

        # Prepare export data
        export_data = {
            'export_metadata': {
                'export_timestamp': export_timestamp,
                'user_pool_id': self.user_pool_id,
                'export_version': '1.0',
            },
            'user_data': {
                'username': username,
                'user_status': user_data.get('UserStatus'),
                'enabled': user_data.get('Enabled', False),
                'user_create_date': user_data['UserCreateDate'].isoformat(),
                'user_last_modified_date': user_data['UserLastModifiedDate'].isoformat(),
                'mfa_options': user_data.get('MFAOptions', []),
                'attributes': self._extract_user_attributes(user_data.get('Attributes', [])),
            },
        }

        # Upload to S3
        try:
            self.s3_client.put_object(
                Bucket=self.backup_bucket_name,
                Key=object_key,
                Body=json.dumps(export_data, indent=2, default=str),
                ContentType='application/json',
                Metadata={
                    'export-timestamp': export_timestamp,
                    'user-pool-id': self.user_pool_id,
                    'username': username,
                },
            )

            logger.debug('Exported user to S3', username=username, object_key=object_key)

        except ClientError as e:
            logger.error('Failed to upload user to S3', username=username, error=str(e))
            raise

    def _extract_user_attributes(self, attributes: list[dict[str, str]]) -> dict[str, str]:
        """
        Extract user attributes from Cognito format to a simple key-value dictionary.

        :param attributes: List of Cognito user attributes
        :return: Dictionary of attribute names to values
        """
        return {attr['Name']: attr['Value'] for attr in attributes}


def backup_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ARG001 unused-argument
    """
    Handler for Cognito user pool backup export.

    Expected event format:
    {
        "user_pool_id": "us-east-1_xxxxxxxxx",
        "backup_bucket_name": "my-cognito-backup-bucket"
    }

    :param event: Lambda event containing user pool and bucket information
    :param context: Lambda context
    :return: Response with export results
    """
    logger.info('Received backup request', event=event)

    try:
        # Extract parameters from event
        user_pool_id = event.get('user_pool_id')
        backup_bucket_name = event.get('backup_bucket_name')

        if not all([user_pool_id, backup_bucket_name]):
            raise ValueError('Missing required parameters: user_pool_id, backup_bucket_name')

        # Create exporter and run export
        exporter = CognitoBackupExporter(user_pool_id, backup_bucket_name)
        results = exporter.export_user_pool()

        logger.info('Export completed successfully', results=results)

        return {
            'statusCode': 200,
            'message': 'Cognito backup export completed successfully',
            'results': results,
        }

    except Exception as e:
        logger.error('Export failed', error=str(e))
        raise
