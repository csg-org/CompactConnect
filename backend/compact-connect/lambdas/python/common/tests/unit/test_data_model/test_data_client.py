from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from cc_common.exceptions import CCNotFoundException

from tests import TstLambdas


class TestDataClient(TstLambdas):
    def setUp(self):
        from cc_common.config import _Config
        from cc_common.data_model.data_client import DataClient

        self.mock_provider_table = MagicMock(name='provider-table')
        self.mock_ssn_table = MagicMock(name='ssn-table')
        self.mock_batch_writer = MagicMock(name='batch_writer')

        # Ensure the context manager returns the mock_batch_writer
        self.mock_provider_table.batch_writer.return_value.__enter__.return_value = self.mock_batch_writer

        self.mock_config = MagicMock(spec=_Config)  # noqa: SLF001 protected-access
        self.mock_config.provider_table = self.mock_provider_table
        self.mock_config.ssn_table = self.mock_ssn_table

        self.client = DataClient(self.mock_config)

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


class TestCollectTransactionIds(TstLambdas):
    """
    Tests for the collection of payment transaction ids from the privilege records an SSN-correction
    migration is moving. These are the transactions whose licenseeId has to follow the practitioner.
    """

    def setUp(self):
        from cc_common.data_model.data_client import DataClient

        self.collect = DataClient._collect_transaction_ids  # noqa: SLF001 protected-access

    def test_collects_the_privilege_records_transaction_id(self):
        privilege = self.test_data_generator.generate_default_privilege({'compactTransactionId': 'tx-current'})

        self.assertEqual({'tx-current'}, self.collect([privilege]))

    def test_privilege_without_a_transaction_id_does_not_raise_exception_and_logs_an_error(self):
        """compactTransactionId is optional on load, so a record read from the table may not carry one.
        Its transaction cannot be re-pointed, which leaves the practitioner reporting as UNKNOWN until
        someone corrects it by hand - so it is surfaced as an error rather than passed over quietly.
        """
        from cc_common.data_model.schema.privilege import PrivilegeData

        database_record = self.test_data_generator.generate_default_privilege().serialize_to_database_record()
        database_record.pop('compactTransactionId')
        privilege_without_transaction_id = PrivilegeData.from_database_record(database_record)

        with patch('cc_common.data_model.data_client.logger') as mock_logger:
            collected = self.collect([privilege_without_transaction_id])

        self.assertEqual(set(), collected)
        # the message states what is wrong, and the context identifies which privilege needs correcting
        mock_logger.error.assert_called_once_with(
            'Migrated privilege record has no compactTransactionId; its transaction cannot be '
            're-pointed to the new provider id',
            compact=privilege_without_transaction_id.compact,
            provider_id=privilege_without_transaction_id.providerId,
            jurisdiction=privilege_without_transaction_id.jurisdiction,
            license_type=privilege_without_transaction_id.licenseType,
        )

    def test_collects_the_previous_transaction_id_from_an_update_record(self):
        """Only the `previous` snapshot is read. A renewal's own transaction id is written to the privilege
        record in the same db transaction, so it is collected from there rather than from `updatedValues`.
        """
        privilege_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={'updatedValues': {'compactTransactionId': 'tx-new'}},
            previous_privilege=self.test_data_generator.generate_default_privilege({'compactTransactionId': 'tx-old'}),
        )

        self.assertEqual({'tx-old'}, self.collect([privilege_update]))

    def test_ignores_records_that_are_not_privileges(self):
        records = [
            self.test_data_generator.generate_default_license(),
            self.test_data_generator.generate_default_license_update(),
            self.test_data_generator.generate_default_adverse_action(),
            self.test_data_generator.generate_default_investigation(),
            self.test_data_generator.generate_default_military_affiliation(),
            self.test_data_generator.generate_default_provider(),
            self.test_data_generator.generate_default_provider_update(),
        ]

        self.assertEqual(set(), self.collect(records))

    def test_shared_transaction_id_is_collected_once(self):
        privilege = self.test_data_generator.generate_default_privilege({'compactTransactionId': 'tx-shared'})
        privilege_update = self.test_data_generator.generate_default_privilege_update(
            value_overrides={'updatedValues': {'compactTransactionId': 'tx-shared'}},
            previous_privilege=privilege,
        )

        self.assertEqual({'tx-shared'}, self.collect([privilege, privilege_update]))
