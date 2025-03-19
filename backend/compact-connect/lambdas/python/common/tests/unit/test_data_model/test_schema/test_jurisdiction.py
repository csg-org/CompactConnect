import json
from decimal import Decimal
from unittest.mock import patch

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
        from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema

        with open('tests/resources/dynamo/jurisdiction.json') as f:
            expected_jurisdiction_config = json.load(f, parse_float=Decimal)
            del expected_jurisdiction_config['postalAbbreviation']

        with self.assertRaises(ValidationError):
            JurisdictionRecordSchema().load(expected_jurisdiction_config.copy())

    @patch('cc_common.config._Config.environment_name', 'sandbox')
    def test_jurisdiction_config_accepts_sandbox_environment_names(self):
        from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema

        with open('tests/resources/dynamo/jurisdiction.json') as f:
            expected_jurisdiction_config = json.load(f, parse_float=Decimal)
            expected_jurisdiction_config['licenseeRegistrationEnabledForEnvironments'] = ['sandbox']

        JurisdictionRecordSchema().load(expected_jurisdiction_config.copy())
