import json
from decimal import Decimal

from marshmallow import ValidationError

from tests import TstLambdas


class TestCompactRecordSchema(TstLambdas):
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.compact.record import CompactRecordSchema

        with open('tests/resources/dynamo/compact.json') as f:
            expected_compact = json.load(f, parse_float=Decimal)

        schema = CompactRecordSchema()
        loaded_schema = schema.load(expected_compact.copy())

        compact_data = schema.dump(loaded_schema)

        # remove dynamic update fields
        expected_compact.pop('dateOfUpdate')
        compact_data.pop('dateOfUpdate')

        self.assertEqual(expected_compact, compact_data)

    def test_compact_config_removes_unknown_fields_gracefully(self):
        """
        We need these config files to use a forgiving schema, so that adding new fields
        in the future does not cause an outage during deployment.
        """
        from cc_common.data_model.schema.compact.record import CompactRecordSchema

        with open('tests/resources/dynamo/compact.json') as f:
            expected_compact = json.load(f, parse_float=Decimal)
            expected_compact['someNewValue'] = 'Will this break something?'

        schema = CompactRecordSchema()
        loaded_schema = schema.load(expected_compact.copy())

        compact_data = schema.dump(loaded_schema)

        self.assertNotIn('someNewValue', compact_data)

    def test_compact_config_raises_validation_error_if_missing_required_field(self):
        """
        Tests that omitting a required field from the compact record data raises a ValidationError.
        
        Removes the 'compactAbbr' field from the input data and asserts that schema validation fails.
        """
        from cc_common.data_model.schema.compact.record import CompactRecordSchema

        with open('tests/resources/dynamo/compact.json') as f:
            expected_compact = json.load(f, parse_float=Decimal)
            del expected_compact['compactAbbr']

        with self.assertRaises(ValidationError):
            CompactRecordSchema().load(expected_compact.copy())

    def test_compact_config_raises_validation_error_for_negative_commission_fee(self):
        """
        Tests that setting a negative value for the commission fee amount triggers a ValidationError.
        
        This test modifies the 'feeAmount' field in the 'compactCommissionFee' section of the input data to a negative value and asserts that schema validation fails with the appropriate error message.
        """
        from cc_common.data_model.schema.compact.record import CompactRecordSchema

        with open('tests/resources/dynamo/compact.json') as f:
            expected_compact = json.load(f, parse_float=Decimal)
            expected_compact['compactCommissionFee']['feeAmount'] = Decimal('-10.00')

        with self.assertRaises(ValidationError) as context:
            CompactRecordSchema().load(expected_compact.copy())

        self.assertIn(
            "{'compactCommissionFee': {'feeAmount': ['Must be greater than or equal to 0.']", str(context.exception)
        )

    def test_compact_config_raises_validation_error_for_negative_transaction_fee(self):
        """
        Tests that providing a negative chargeAmount in licenseeCharges triggers a ValidationError.
        
        Verifies that the schema rejects negative values for transaction fee amounts and that the
        error message indicates the value must be greater than or equal to zero.
        """
        from cc_common.data_model.schema.compact.record import CompactRecordSchema

        with open('tests/resources/dynamo/compact.json') as f:
            expected_compact = json.load(f, parse_float=Decimal)
            expected_compact['transactionFeeConfiguration']['licenseeCharges']['chargeAmount'] = Decimal('-5.00')

        with self.assertRaises(ValidationError) as context:
            CompactRecordSchema().load(expected_compact.copy())

        self.assertIn(
            "{'transactionFeeConfiguration': {'licenseeCharges': {'chargeAmount': "
            "['Must be greater than or equal to 0.']",
            str(context.exception),
        )
