"""
Functional tests for the Cognito backup Lambda function.

This module tests the complete backup functionality with mocked AWS services
using moto to verify the end-to-end behavior.
"""

import json

from moto import mock_aws

from . import TstFunction


@mock_aws
class TestCognitoBackupFunctional(TstFunction):
    """Functional tests for Cognito backup export functionality."""

    def test_lambda_handler_success(self):
        """Test successful lambda handler execution with real AWS service mocks."""
        from handlers.cognito_backup import backup_handler as lambda_handler

        event = self.get_test_event()
        result = lambda_handler(event, self.mock_context)

        # Verify response structure
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('message', result)
        self.assertIn('results', result)
        self.assertIn('Cognito backup export completed successfully', result['message'])

        # Verify results
        results = result['results']
        self.assertEqual(results['user_pool_id'], self.user_pool_id)
        self.assertEqual(results['users_exported'], 2)  # We created 2 test users
        self.assertEqual(results['backup_bucket'], self.bucket_name)
        self.assertEqual(results['status'], 'success')
        self.assertIn('export_timestamp', results)

    def test_cognito_backup_exports_all_users(self):
        """Test that all users in the user pool are exported to S3."""
        from handlers.cognito_backup import CognitoBackupExporter

        exporter = CognitoBackupExporter(self.user_pool_id, self.bucket_name)
        results = exporter.export_user_pool()

        # Verify export results
        self.assertEqual(results['users_exported'], 2)

        # Verify S3 objects were created
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        self.assertIn('Contents', s3_objects)
        self.assertEqual(len(s3_objects['Contents']), 2)

        # Verify object keys
        object_keys = [obj['Key'] for obj in s3_objects['Contents']]
        expected_keys = [
            'cognito-exports/test-user-1.json',
            'cognito-exports/test-user-2.json',
        ]
        self.assertEqual(sorted(object_keys), sorted(expected_keys))

    def test_exported_user_data_structure(self):
        """Test the structure and content of exported user data."""
        from handlers.cognito_backup import CognitoBackupExporter

        exporter = CognitoBackupExporter(self.user_pool_id, self.bucket_name)
        exporter.export_user_pool()

        # Get exported data from S3
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        first_object_key = s3_objects['Contents'][0]['Key']

        obj_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=first_object_key)
        export_data = json.loads(obj_response['Body'].read().decode('utf-8'))

        # Verify top-level structure
        self.assertIn('export_metadata', export_data)
        self.assertIn('user_data', export_data)

        # Verify export metadata
        metadata = export_data['export_metadata']
        self.assertEqual(metadata['user_pool_id'], self.user_pool_id)
        self.assertEqual(metadata['export_version'], '1.0')
        self.assertIn('export_timestamp', metadata)

        # Verify user data structure
        user_data = export_data['user_data']
        required_fields = [
            'username',
            'user_status',
            'enabled',
            'user_create_date',
            'user_last_modified_date',
            'mfa_options',
            'attributes',
        ]
        for field in required_fields:
            self.assertIn(field, user_data)

        # Verify attributes were properly extracted
        self.assertIsInstance(user_data['attributes'], dict)
        self.assertIn('email', user_data['attributes'])

    def test_s3_object_metadata(self):
        """Test that S3 objects have correct metadata."""
        from handlers.cognito_backup import CognitoBackupExporter

        exporter = CognitoBackupExporter(self.user_pool_id, self.bucket_name)
        exporter.export_user_pool()

        # Get object metadata
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        first_object_key = s3_objects['Contents'][0]['Key']

        head_response = self.s3_client.head_object(Bucket=self.bucket_name, Key=first_object_key)
        metadata = head_response['Metadata']

        # Verify metadata fields
        self.assertIn('export-timestamp', metadata)
        self.assertEqual(metadata['user-pool-id'], self.user_pool_id)
        self.assertIn('username', metadata)

        # Verify content type
        self.assertEqual(head_response['ContentType'], 'application/json')

    def test_backup_export_basic_functionality(self):
        """Test basic export functionality."""
        from handlers.cognito_backup import CognitoBackupExporter

        exporter = CognitoBackupExporter(self.user_pool_id, self.bucket_name)
        results = exporter.export_user_pool()

        # Verify results
        self.assertEqual(results['users_exported'], 2)
        self.assertEqual(results['status'], 'success')

        # Verify S3 object paths
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        object_keys = [obj['Key'] for obj in s3_objects['Contents']]

        for key in object_keys:
            self.assertTrue(key.startswith('cognito-exports/'))

    def test_empty_user_pool(self):
        """Test export of an empty user pool."""
        from handlers.cognito_backup import CognitoBackupExporter

        # Create an empty user pool
        empty_pool_response = self.cognito_client.create_user_pool(PoolName='empty-test-pool')
        empty_pool_id = empty_pool_response['UserPool']['Id']

        exporter = CognitoBackupExporter(empty_pool_id, self.bucket_name)
        results = exporter.export_user_pool()

        # Verify results
        self.assertEqual(results['users_exported'], 0)
        self.assertEqual(results['status'], 'success')

        # Verify no S3 objects were created
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        self.assertNotIn('Contents', s3_objects)

    def test_user_with_custom_attributes(self):
        """Test export of user with custom attributes."""
        from handlers.cognito_backup import CognitoBackupExporter

        # The second test user has a custom attribute
        exporter = CognitoBackupExporter(self.user_pool_id, self.bucket_name)
        exporter.export_user_pool()

        # Find and verify the user with custom attributes
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)

        for obj in s3_objects['Contents']:
            if 'test-user-2' in obj['Key']:
                obj_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=obj['Key'])
                export_data = json.loads(obj_response['Body'].read().decode('utf-8'))

                attributes = export_data['user_data']['attributes']
                self.assertIn('custom:providerId', attributes)
                self.assertEqual(attributes['custom:providerId'], 'provider123')
                break
        else:
            self.fail('Could not find test-user-2 export')

    def test_pagination_handling(self):
        """Test that pagination is handled correctly for large user pools."""
        from handlers.cognito_backup import CognitoBackupExporter

        # Create many users to test pagination (moto may not enforce the 60 limit, but we can test the logic)
        for i in range(5):
            self.cognito_client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=f'pagination-user-{i}',
                UserAttributes=[
                    {'Name': 'email', 'Value': f'paguser{i}@example.com'},
                ],
                MessageAction='SUPPRESS',
                TemporaryPassword='TempPass123!',
            )

        exporter = CognitoBackupExporter(self.user_pool_id, self.bucket_name)
        results = exporter.export_user_pool()

        # Verify all users were exported (2 original + 5 new = 7 total)
        self.assertEqual(results['users_exported'], 7)

        # Verify all users are in S3
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        self.assertEqual(len(s3_objects['Contents']), 7)

    def test_lambda_handler_multiple_executions(self):
        """Test lambda handler with multiple executions."""
        from handlers.cognito_backup import backup_handler as lambda_handler

        # Run export multiple times to ensure consistency
        for i in range(3):
            with self.subTest(execution=i):
                # Clear bucket between tests
                s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
                if 'Contents' in s3_objects:
                    for obj in s3_objects['Contents']:
                        self.s3_client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])

                event = self.get_test_event()
                result = lambda_handler(event, self.mock_context)

                # Verify response
                self.assertEqual(result['statusCode'], 200)
                self.assertEqual(result['results']['users_exported'], 2)

                # Verify S3 paths
                s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
                if 'Contents' in s3_objects:
                    for obj in s3_objects['Contents']:
                        self.assertTrue(obj['Key'].startswith('cognito-exports/'))


@mock_aws
class TestCognitoBackupErrorHandling(TstFunction):
    """Test error handling in Cognito backup functionality."""

    def test_invalid_user_pool_id(self):
        """Test handling of invalid user pool ID."""
        from botocore.exceptions import ClientError
        from handlers.cognito_backup import CognitoBackupExporter

        exporter = CognitoBackupExporter('invalid-pool-id', self.bucket_name)

        with self.assertRaises(ClientError):
            exporter.export_user_pool()

    def test_invalid_bucket_name(self):
        """Test handling of invalid S3 bucket."""
        from botocore.exceptions import ClientError
        from handlers.cognito_backup import CognitoBackupExporter

        exporter = CognitoBackupExporter(self.user_pool_id, 'invalid-bucket-name')

        # Should raise an exception like invalid user pool ID test
        with self.assertRaises(ClientError):
            exporter.export_user_pool()

    def test_lambda_handler_invalid_event(self):
        """Test lambda handler with invalid event parameters."""
        from handlers.cognito_backup import backup_handler as lambda_handler

        invalid_events = [
            {},  # Empty event
            {'user_pool_id': 'test'},  # Missing backup_bucket_name
            {'backup_bucket_name': 'test'},  # Missing user_pool_id
        ]

        for event in invalid_events:
            with self.subTest(event=event):
                with self.assertRaises(ValueError):
                    lambda_handler(event, self.mock_context)

    def test_extract_user_attributes_functionality(self):
        """Test user attributes extraction with real Cognito user data."""
        from handlers.cognito_backup import CognitoBackupExporter

        # Create a user with various attribute types
        self.cognito_client.admin_create_user(
            UserPoolId=self.user_pool_id,
            Username='attribute-test-user',
            UserAttributes=[
                {'Name': 'email', 'Value': 'attr@example.com'},
                {'Name': 'given_name', 'Value': 'Attribute'},
                {'Name': 'family_name', 'Value': 'Tester'},
                {'Name': 'custom:providerId', 'Value': 'attr123'},
                {'Name': 'phone_number', 'Value': '+1234567890'},
            ],
            MessageAction='SUPPRESS',
            TemporaryPassword='TempPass123!',
        )

        exporter = CognitoBackupExporter(self.user_pool_id, self.bucket_name)
        exporter.export_user_pool()

        # Find and verify the attributes were extracted correctly
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)

        for obj in s3_objects['Contents']:
            if 'attribute-test-user' in obj['Key']:
                obj_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=obj['Key'])
                export_data = json.loads(obj_response['Body'].read().decode('utf-8'))

                attributes = export_data['user_data']['attributes']

                # Verify all attributes are properly extracted
                self.assertEqual(attributes['email'], 'attr@example.com')
                self.assertEqual(attributes['given_name'], 'Attribute')
                self.assertEqual(attributes['family_name'], 'Tester')
                self.assertEqual(attributes['custom:providerId'], 'attr123')
                self.assertEqual(attributes['phone_number'], '+1234567890')
                break
        else:
            self.fail('Could not find attribute-test-user export')

    def test_export_initialization_and_datetime_formatting(self):
        """Test CognitoBackupExporter initialization and datetime handling with real data."""
        from handlers.cognito_backup import CognitoBackupExporter

        # Test initialization
        exporter = CognitoBackupExporter(self.user_pool_id, self.bucket_name)
        self.assertEqual(exporter.user_pool_id, self.user_pool_id)
        self.assertEqual(exporter.backup_bucket_name, self.bucket_name)

        # Test datetime formatting by running export and checking timestamp formats
        exporter.export_user_pool()

        # Get an exported file and verify datetime formats
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        first_object_key = s3_objects['Contents'][0]['Key']

        obj_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=first_object_key)
        export_data = json.loads(obj_response['Body'].read().decode('utf-8'))

        # Verify export timestamp format (ISO format)
        export_timestamp = export_data['export_metadata']['export_timestamp']
        self.assertRegex(export_timestamp, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+(\+00:00|Z)')

        # Verify user datetime fields are properly formatted or None
        user_data = export_data['user_data']

        # These should be properly formatted ISO strings or None
        create_date = user_data['user_create_date']
        modified_date = user_data['user_last_modified_date']

        if create_date is not None:
            # Should be a valid ISO timestamp
            self.assertRegex(create_date, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')

        if modified_date is not None:
            # Should be a valid ISO timestamp
            self.assertRegex(modified_date, r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')

    def test_malformed_user_handling(self):
        """Test graceful handling of users with missing or malformed data."""
        from handlers.cognito_backup import CognitoBackupExporter

        # This test verifies the system handles edge cases gracefully
        # We can't easily create a malformed user in Cognito, but we can test
        # the edge case of no users and verify no exceptions are raised

        # Create an empty user pool
        empty_pool_response = self.cognito_client.create_user_pool(PoolName='malformed-test-pool')
        empty_pool_id = empty_pool_response['UserPool']['Id']

        exporter = CognitoBackupExporter(empty_pool_id, self.bucket_name)

        # This should complete without errors even with no users
        results = exporter.export_user_pool()

        self.assertEqual(results['users_exported'], 0)
        self.assertEqual(results['status'], 'success')

        # Test with users that have minimal attributes
        self.cognito_client.admin_create_user(
            UserPoolId=empty_pool_id,
            Username='minimal-user',
            UserAttributes=[],  # No attributes
            MessageAction='SUPPRESS',
            TemporaryPassword='TempPass123!',
        )

        # Clear bucket first
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        if 'Contents' in s3_objects:
            for obj in s3_objects['Contents']:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])

        # Export should handle user with no attributes gracefully
        results = exporter.export_user_pool()

        self.assertEqual(results['users_exported'], 1)
        self.assertEqual(results['status'], 'success')

        # Verify the exported data structure is still valid
        s3_objects = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        self.assertEqual(len(s3_objects['Contents']), 1)

        obj_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_objects['Contents'][0]['Key'])
        export_data = json.loads(obj_response['Body'].read().decode('utf-8'))

        # Should have proper structure even with minimal data
        self.assertIn('export_metadata', export_data)
        self.assertIn('user_data', export_data)
        self.assertEqual(export_data['user_data']['username'], 'minimal-user')

        # Cognito automatically adds 'sub' attribute, so we expect at least that
        attributes = export_data['user_data']['attributes']
        self.assertIsInstance(attributes, dict)
        self.assertIn('sub', attributes)  # Cognito always adds this
        # Should not have any other user-defined attributes
        self.assertLessEqual(len(attributes), 1)
