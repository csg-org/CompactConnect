from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from cc_common.exceptions import CCAwsServiceException

from tests import TstLambdas


class TestDataClient(TstLambdas):
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
    def test_data_client_deletes_records_if_exception_during_create_privilege_records(self):
        from cc_common.data_model import client

        mock_dynamo_db_table = MagicMock(name='provider-table')
        mock_batch_writer = MagicMock(name='batch_writer')

        # Ensure the context manager returns the mock_batch_writer
        mock_dynamo_db_table.batch_writer.return_value.__enter__.return_value = mock_batch_writer

        # Set the side effect to raise ClientError on put_item
        mock_batch_writer.put_item.side_effect = ClientError(
            error_response={'Error': {'Code': 'InternalServerError', 'Message': 'DynamoDB Internal Server Error'}},
            operation_name='PutItem',
        )

        mock_config = MagicMock(spec=client._Config)  # noqa: SLF001 protected-access
        mock_config.provider_table = mock_dynamo_db_table

        test_data_client = client.DataClient(mock_config)

        with self.assertRaises(CCAwsServiceException):
            test_data_client.create_provider_privileges(
                compact_name='aslp',
                provider_id='test_provider_id',
                jurisdiction_postal_abbreviations=['CA'],
                license_expiration_date=date.fromisoformat('2024-10-31'),
                existing_privileges=[],
                compact_transaction_id='test_transaction_id',
            )

        mock_batch_writer.delete_item.assert_called_with(
            Key={
                'pk': 'aslp#PROVIDER#test_provider_id',
                'sk': 'aslp#PROVIDER#privilege/ca#2024-11-08',
            }
        )
