import json
from decimal import Decimal

from marshmallow import ValidationError

from tests import TstLambdas


class TestJurisdictionRecordSchema(TstLambdas):
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema

        with open('tests/resources/dynamo/jurisdiction.json') as f:
            expected_jurisdiction_config = json.load(f, parse_float=Decimal)

        schema = JurisdictionRecordSchema()
        loaded_schema = schema.load(expected_jurisdiction_config.copy())

        jurisdiction_config_data = schema.dump(loaded_schema)

        # remove dynamic update fields
        expected_jurisdiction_config.pop('dateOfUpdate')
        jurisdiction_config_data.pop('dateOfUpdate')

        self.assertEqual(expected_jurisdiction_config, jurisdiction_config_data)

    def test_jurisdiction_config_removes_unknown_fields_gracefully(self):
        """
        We need these config files to use a forgiving schema, so that adding new fields
        in the future does not cause an outage during deployment.
        """
        from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema

        with open('tests/resources/dynamo/jurisdiction.json') as f:
            expected_jurisdiction_config = json.load(f, parse_float=Decimal)
            expected_jurisdiction_config['someNewValue'] = 'Will this break something?'

        schema = JurisdictionRecordSchema()
        loaded_schema = schema.load(expected_jurisdiction_config.copy())

        jurisdiction_config_data = schema.dump(loaded_schema)

        self.assertNotIn('someNewValue', jurisdiction_config_data)

    def test_jurisdiction_config_raises_validation_error_if_missing_required_field(self):
        """
        Tests that omitting a required field from the jurisdiction config raises a ValidationError.
        
        Removes the 'postalAbbreviation' field from the loaded jurisdiction config and asserts
        that schema validation fails due to the missing required field.
        """
        from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema

        with open('tests/resources/dynamo/jurisdiction.json') as f:
            expected_jurisdiction_config = json.load(f, parse_float=Decimal)
            del expected_jurisdiction_config['postalAbbreviation']

        with self.assertRaises(ValidationError):
            JurisdictionRecordSchema().load(expected_jurisdiction_config.copy())

    def test_jurisdiction_config_raises_validation_error_for_negative_privilege_fee_amount(self):
        """
        Tests that setting a negative amount in the first privilege fee entry triggers a ValidationError.
        
        The test modifies the 'amount' field of the first privilege fee to a negative value and asserts
        that schema validation fails with an error message indicating the amount must be non-negative.
        """
        from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema

        with open('tests/resources/dynamo/jurisdiction.json') as f:
            expected_jurisdiction_config = json.load(f, parse_float=Decimal)
            expected_jurisdiction_config['privilegeFees'][0]['amount'] = Decimal('-25.00')

        with self.assertRaises(ValidationError) as context:
            JurisdictionRecordSchema().load(expected_jurisdiction_config.copy())

        self.assertIn(
            "{'privilegeFees': {0: {'amount': ['Must be greater than or equal to 0.']", str(context.exception)
        )

    def test_jurisdiction_config_raises_validation_error_for_negative_military_rate(self):
        """
        Tests that deserializing a jurisdiction config with a negative militaryRate in privilegeFees raises a ValidationError.
        
        Asserts that the error message indicates the militaryRate must be greater than or equal to zero.
        """
        from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema

        with open('tests/resources/dynamo/jurisdiction.json') as f:
            expected_jurisdiction_config = json.load(f, parse_float=Decimal)
            expected_jurisdiction_config['privilegeFees'][0]['militaryRate'] = Decimal('-15.00')

        with self.assertRaises(ValidationError) as context:
            JurisdictionRecordSchema().load(expected_jurisdiction_config.copy())

        self.assertIn(
            "{'privilegeFees': {0: {'militaryRate': ['Must be greater than or equal to 0.']", str(context.exception)
        )
