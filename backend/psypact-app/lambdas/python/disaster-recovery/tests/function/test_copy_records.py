import os
from unittest.mock import patch

import boto3
from moto import mock_aws

from . import TstFunction


@mock_aws
class TestCopyRecords(TstFunction):
    """Test suite for DR copy records step."""

    def _generate_test_event(self) -> dict:
        return {
            'sourceTableArn': self.mock_source_table_arn,
            'destinationTableArn': self.mock_destination_table_arn,
            'tableNameRecoveryConfirmation': self.mock_destination_table_name,
        }

    def test_copy_records_returns_complete_status_when_records_copied_over(self):
        from handlers.copy_records import copy_records

        event = self._generate_test_event()

        response = copy_records(event, self.mock_context)

        self.assertEqual(
            'COMPLETE',
            response['copyStatus'],
        )

    def test_lambda_returns_failed_copy_status_when_guard_rail_fails(self):
        from handlers.copy_records import copy_records

        event = self._generate_test_event()
        event['tableNameRecoveryConfirmation'] = 'invalid-table-name'
        response = copy_records(event, self.mock_context)

        self.assertEqual(
            {
                'copyStatus': 'FAILED',
                'error': 'Invalid table name specified. tableNameRecoveryConfirmation field must be set to '
                'Test-PersistentStack-ProviderTableEC5D0597-TQ2RIO6VVBRE',
            },
            response,
        )

    def test_copy_records_copies_all_records_over_from_source_to_destination_table(self):
        from handlers.copy_records import copy_records

        source_items = []
        for i in range(5000):
            source_item = {
                'pk': str(i),
                'sk': str(i),
                'data': f'test_{i}',
            }
            source_items.append(source_item)
            self.mock_source_table.put_item(Item=source_item)

        event = self._generate_test_event()

        response = copy_records(event, self.mock_context)

        self.assertEqual(
            {
                'copyStatus': 'COMPLETE',
                'copiedCount': 5000,
                'sourceTableArn': self.mock_source_table_arn,
                'destinationTableArn': self.mock_destination_table_arn,
                'tableNameRecoveryConfirmation': self.mock_destination_table_name,
            },
            response,
        )

        # now get all records from destination table using pagination
        last_evaluated_key = None
        copied_items = []
        while True:
            scan_kwargs = {}
            if last_evaluated_key:
                scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

            # get all records from destination table
            response = self.mock_destination_table.scan(**scan_kwargs)
            items = response.get('Items', [])

            if not items:
                break

            copied_items.extend(items)
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break

        self.assertEqual(5000, len(copied_items))
        source_items.sort(key=lambda x: x['pk'])
        copied_items.sort(key=lambda x: x['pk'])
        self.assertEqual(source_items, copied_items)

    @patch('handlers.copy_records.time')
    def test_copy_records_returns_in_progress_with_pagination_key_if_max_time_elapsed(self, mock_time):
        from handlers.copy_records import copy_records

        source_items = []
        for i in range(5000):
            source_item = {
                'pk': str(i),
                'sk': str(i),
                'data': f'test_{i}',
            }
            source_items.append(source_item)
            self.mock_source_table.put_item(Item=source_item)

        # Lambda functions have a timeout of 15 minutes, so we set a cutoff of 12 minutes before we loop around
        # the step function to reset the timeout. This mock allows us to test that branch of logic.
        # the first time the mock_time function is called, it will return current time
        # the second time the mock_time function is called, it will return + 1 second
        # the third time the mock_time function is called, it will return 12 minutes + 1 second (cutoff is 12 minutes)
        # this should cause the lambda to return an IN_PROGRESS status with a pagination key
        mock_time.time.side_effect = [0, 1, 12 * 60 + 2]  # current time, 12 minutes + 2 seconds

        event = self._generate_test_event()

        response = copy_records(event, self.mock_context)

        self.assertEqual(
            {
                'copyStatus': 'IN_PROGRESS',
                # in this test cases, the table items are very small, so we expect all 2000 to be returned within the
                # single page (under the 1MB page limit)
                'copiedCount': 2000,
                'copyLastEvaluatedKey': 'eyJwayI6ICIyNzk4IiwgInNrIjogIjI3OTgifQ==',
                'sourceTableArn': self.mock_source_table_arn,
                'destinationTableArn': self.mock_destination_table_arn,
                'tableNameRecoveryConfirmation': self.mock_destination_table_name,
            },
            response,
        )

    def test_copy_records_uses_pagination_key_if_provided(self):
        from handlers.copy_records import copy_records

        source_items = []
        for i in range(5000):
            source_item = {
                'pk': str(i),
                'sk': str(i),
                'data': f'test_{i}',
            }
            source_items.append(source_item)
            self.mock_source_table.put_item(Item=source_item)

        event = self._generate_test_event()
        # this is the key generated by the previous test, in which only 2000 records were processed
        # by using this same key, we expect the remaining 3000 should be processed in this test.
        event['copyLastEvaluatedKey'] = 'eyJwayI6ICIyNzk4IiwgInNrIjogIjI3OTgifQ=='
        event['copiedCount'] = 2000

        response = copy_records(event, self.mock_context)

        self.assertEqual(
            {
                'copyStatus': 'COMPLETE',
                # the 2000 that is passed into the event should be added to the remaining 3000 that get copied over
                'copiedCount': 5000,
                'sourceTableArn': self.mock_source_table_arn,
                'destinationTableArn': self.mock_destination_table_arn,
                'tableNameRecoveryConfirmation': self.mock_destination_table_name,
            },
            response,
        )

    def test_pagination_key_can_be_encrypted_and_decrypted(self):
        from handlers.copy_records import decrypt_pagination_key, encrypt_pagination_key

        # Create a mock KMS key
        kms_client = boto3.client('kms', region_name='us-east-1')
        key_response = kms_client.create_key(Description='Test SSN encryption key')
        key_id = key_response['KeyMetadata']['KeyId']

        # Test data
        test_key_data = {'pk': 'test-ssn-123', 'sk': 'test-sk-456'}

        # Encrypt then decrypt
        encrypted_key = encrypt_pagination_key(test_key_data, key_id)
        decrypted_key = decrypt_pagination_key(encrypted_key, key_id)

        # Verify the decrypted data matches the original
        self.assertEqual(test_key_data, decrypted_key)

    @patch('handlers.copy_records.time')
    def test_copy_records_encrypts_pagination_key_when_ssn_encryption_enabled_and_time_limit_reached(self, mock_time):
        from handlers.copy_records import copy_records, decrypt_pagination_key

        # Create a mock KMS key
        kms_client = boto3.client('kms', region_name='us-east-1')
        key_response = kms_client.create_key(Description='Test SSN encryption key')
        key_id = key_response['KeyMetadata']['KeyId']

        # Add test data
        source_items = []
        for i in range(3000):
            source_item = {
                'pk': str(i),
                'sk': str(i),
                'data': f'test_{i}',
            }
            source_items.append(source_item)
            self.mock_source_table.put_item(Item=source_item)

        # Mock time to trigger timeout on third call, then reset it back for the subsequent call
        mock_time.time.side_effect = [0, 1, 12 * 60 + 2, 0, 1]

        with patch.dict(os.environ, {'SSN_ENCRYPTION_KMS_KEY_ID': key_id}):
            event = self._generate_test_event()
            response = copy_records(event, self.mock_context)

            self.assertEqual('IN_PROGRESS', response['copyStatus'])
            encrypted_pagination_key = response['copyLastEvaluatedKey']
            decrypted_key = decrypt_pagination_key(encrypted_pagination_key, key_id)
            # because we use strings for the keys, the keys are sorted in lexicographical order
            # this key is the 2000th record by that order
            self.assertEqual({'pk': '2798', 'sk': '2798'}, decrypted_key)

            # now call again with the key and expect to get back the remaining records
            second_call_response = copy_records(response, self.mock_context)

            # Should copy over the remaining records successfully
            self.assertEqual('COMPLETE', second_call_response['copyStatus'])
            self.assertEqual(3000, second_call_response['copiedCount'])
