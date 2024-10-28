from datetime import date
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from exceptions import CCAwsServiceException
from tests import TstLambdas

class TestDataClient(TstLambdas):
    """Testing that the api_handler decorator is working as expected."""

    def test_data_client_deletes_records_if_exception_during_create_privilege_records(self):
        from data_model import client

        mock_dynamo_db_table = MagicMock(name='provider-table')
        mock_batch_writer = MagicMock(name='batch_writer')

        # Ensure the context manager returns the mock_batch_writer
        mock_dynamo_db_table.batch_writer.return_value.__enter__.return_value = mock_batch_writer

        # Set the side effect to raise ClientError on put_item
        mock_batch_writer.put_item.side_effect = ClientError(
            error_response={
                "Error": {
                    "Code": "InternalServerError",
                    "Message": "DynamoDB Internal Server Error"
                }
            },
            operation_name='PutItem'
        )

        mock_config = MagicMock(spec=client._Config)
        mock_config.provider_table = mock_dynamo_db_table

        test_data_client = client.DataClient(mock_config)

        with self.assertRaises(CCAwsServiceException):
            test_data_client.create_provider_privileges(
                "aslp",
                "test_provider_id",
                ["CA"],
                date.fromisoformat("2024-10-31"),
                "test_transaction_id"
            )

        mock_batch_writer.delete_item.assert_called_with(
            Key={'pk': 'aslp#PROVIDER#test_provider_id', 'sk': 'aslp#PROVIDER#privilege/ca'})
