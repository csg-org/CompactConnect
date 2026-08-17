from marshmallow import ValidationError

from tests import TstLambdas


class TestTransactionRecordSchema(TstLambdas):
    def setUp(self):
        from common_test.test_data_generator import TestDataGenerator

        self.test_data_generator = TestDataGenerator

    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.transaction.record import TransactionRecordSchema

        expected_transaction = self.test_data_generator.generate_default_transaction().serialize_to_database_record()

        schema = TransactionRecordSchema()
        loaded_schema = schema.load(expected_transaction.copy())

        transaction_data = schema.dump(loaded_schema)

        # Drop dynamic fields
        del expected_transaction['dateOfUpdate']
        del transaction_data['dateOfUpdate']

        self.assertEqual(expected_transaction, transaction_data)

    def test_invalid(self):
        from cc_common.data_model.schema.transaction.record import TransactionRecordSchema

        transaction_data = self.test_data_generator.generate_default_transaction().to_dict()
        transaction_data.pop('transactionId')

        with self.assertRaises(ValidationError):
            TransactionRecordSchema().load(transaction_data)

    def test_invalid_transaction_processor(self):
        from cc_common.data_model.schema.transaction import TransactionData

        transaction_data = self.test_data_generator.generate_default_transaction()
        transaction_record = transaction_data.serialize_to_database_record()
        transaction_record['transactionProcessor'] = 'invalid-processor'

        with self.assertRaises(ValidationError):
            TransactionData.from_database_record(transaction_record)


class TestTransactionDataClass(TstLambdas):
    def setUp(self):
        from common_test.test_data_generator import TestDataGenerator

        self.test_data_generator = TestDataGenerator

    def test_transaction_data_class_getters_return_expected_values(self):
        from cc_common.data_model.schema.transaction import TransactionData

        transaction_data = self.test_data_generator.generate_default_transaction().serialize_to_database_record()

        transaction = TransactionData.from_database_record(transaction_data)
        self.assertEqual(transaction.transactionProcessor, transaction_data['transactionProcessor'])
        self.assertEqual(transaction.transactionId, transaction_data['transactionId'])
        self.assertEqual(transaction.batch, transaction_data['batch'])
        self.assertEqual(transaction.lineItems, transaction_data['lineItems'])
        self.assertEqual(transaction.compact, transaction_data['compact'])
        self.assertEqual(transaction.licenseeId, transaction_data['licenseeId'])
        self.assertEqual(transaction.responseCode, transaction_data['responseCode'])
        self.assertEqual(transaction.settleAmount, transaction_data['settleAmount'])
        self.assertEqual(transaction.submitTimeUTC, transaction_data['submitTimeUTC'])
        self.assertEqual(transaction.transactionStatus, transaction_data['transactionStatus'])
        self.assertEqual(transaction.transactionType, transaction_data['transactionType'])

    def test_transaction_data_class_outputs_expected_database_object(self):
        # check final snapshot of expected data
        transaction_data = self.test_data_generator.generate_default_transaction().serialize_to_database_record()
        # remove dynamic field
        del transaction_data['dateOfUpdate']

        self.assertEqual(
            {
                'batch': {
                    'batchId': '67890',
                    'settlementState': 'settledSuccessfully',
                    'settlementTimeLocal': '2024-01-01T09:00:00',
                    'settlementTimeUTC': '2024-01-01T13:00:00.000Z',
                },
                'compact': 'aslp',
                'licenseeId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                'lineItems': [
                    {
                        'description': 'Compact Privilege for Ohio',
                        'itemId': 'priv:aslp-oh',
                        'name': 'Ohio Compact Privilege',
                        'quantity': '1.0',
                        'taxable': 'False',
                        'unitPrice': '100.00',
                        'privilegeId': 'mock-privilege-id-oh',
                    },
                    {
                        'description': 'Compact fee applied for each privilege purchased',
                        'itemId': 'aslp-compact-fee',
                        'name': 'ASLP Compact Fee',
                        'quantity': '1',
                        'taxable': 'False',
                        'unitPrice': '10.50',
                    },
                    {
                        'description': 'credit card transaction fee',
                        'itemId': 'credit-card-transaction-fee',
                        'name': 'Credit Card Transaction Fee',
                        'quantity': '1',
                        'taxable': 'False',
                        'unitPrice': '3.00',
                    },
                ],
                'pk': 'COMPACT#aslp#TRANSACTIONS#MONTH#2024-01',
                'responseCode': '1',
                'settleAmount': '113.50',
                'sk': 'COMPACT#aslp#TIME#1704114000#BATCH#67890#TX#1234567890',
                'submitTimeUTC': '2024-01-01T12:00:00.000Z',
                'transactionId': '1234567890',
                'transactionProcessor': 'authorize.net',
                'transactionStatus': 'settledSuccessfully',
                'transactionType': 'authCaptureTransaction',
                'type': 'transaction',
            },
            transaction_data,
        )
