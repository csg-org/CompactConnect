from datetime import date, datetime
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from cc_common.exceptions import CCAwsServiceException, CCNotFoundException

from tests import TstLambdas


class TestDataClient(TstLambdas):
    def setUp(self):
        from cc_common.data_model import client

        self.mock_provider_table = MagicMock(name='provider-table')
        self.mock_ssn_table = MagicMock(name='ssn-table')
        self.mock_batch_writer = MagicMock(name='batch_writer')

        # Ensure the context manager returns the mock_batch_writer
        self.mock_provider_table.batch_writer.return_value.__enter__.return_value = self.mock_batch_writer

        self.mock_config = MagicMock(spec=client._Config)  # noqa: SLF001 protected-access
        self.mock_config.provider_table = self.mock_provider_table
        self.mock_config.ssn_table = self.mock_ssn_table

        self.client = client.DataClient(self.mock_config)

    def test_get_provider_id_success(self):
        # Mock response from DynamoDB
        self.mock_ssn_table.get_item.return_value = {
            'Item': {'pk': 'aslp#SSN#123456789', 'sk': 'aslp#SSN#123456789', 'providerId': 'test_provider_id'}
        }

        # Call the method
        provider_id = self.client.get_provider_id(compact='aslp', ssn='123456789')

        # Verify the result
        self.assertEqual(provider_id, 'test_provider_id')
        self.mock_ssn_table.get_item.assert_called_once_with(
            Key={'pk': 'aslp#SSN#123456789', 'sk': 'aslp#SSN#123456789'}, ConsistentRead=True
        )

    def test_get_provider_id_not_found(self):
        # Mock response from DynamoDB for non-existent item
        self.mock_ssn_table.get_item.return_value = {}

        # Verify it raises CCNotFoundException
        with self.assertRaises(CCNotFoundException):
            self.client.get_provider_id(compact='aslp', ssn='123456789')

    def test_get_or_create_provider_id_existing(self):
        # Mock ClientError for existing provider
        error_response = {
            'Error': {'Code': 'ConditionalCheckFailedException'},
            'Item': {'providerId': {'S': 'existing_provider_id'}},
        }
        self.mock_ssn_table.put_item.side_effect = ClientError(error_response, 'PutItem')

        # Call the method
        provider_id = self.client.get_or_create_provider_id(compact='aslp', ssn='123456789')

        # Verify the result
        self.assertEqual(provider_id, 'existing_provider_id')

    def test_get_provider_not_found(self):
        # Mock response from DynamoDB for non-existent provider
        self.mock_provider_table.query.return_value = {'Items': []}

        # Verify it raises CCNotFoundException
        with self.assertRaises(CCNotFoundException):
            self.client.get_provider(compact='aslp', provider_id='test_id', detail=True, consistent_read=False)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_data_client_deletes_records_if_exception_during_create_privilege_records(self):
        # Set the side effect to raise ClientError on put_item
        self.mock_batch_writer.put_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'InternalServerError', 'Message': 'DynamoDB Internal Server Error'}},
            operation_name='PutItem',
        )

        with self.assertRaises(CCAwsServiceException):
            self.client.create_provider_privileges(
                compact_name='aslp',
                provider_id='test_provider_id',
                jurisdiction_postal_abbreviations=['CA'],
                license_expiration_date=date.fromisoformat('2024-10-31'),
                existing_privileges=[],
                attestations=[],
                compact_transaction_id='test_transaction_id',
            )

        self.mock_batch_writer.delete_item.assert_called_with(
            Key={
                'pk': 'aslp#PROVIDER#test_provider_id',
                'sk': 'aslp#PROVIDER#privilege/ca#2024-11-08',
            }
        )
