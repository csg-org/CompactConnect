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
        from cc_common.data_model.schema.compact.record import CompactRecordSchema

        with open('tests/resources/dynamo/compact.json') as f:
            expected_compact = json.load(f, parse_float=Decimal)
            del expected_compact['compactAbbr']

        with self.assertRaises(ValidationError):
            CompactRecordSchema().load(expected_compact.copy())

    def test_compact_config_raises_validation_error_for_invalid_configured_state_jurisdiction(self):
        """Test that an invalid jurisdiction postal abbreviation in configuredStates raises a ValidationError"""
        from cc_common.data_model.schema.compact.record import CompactRecordSchema

        with open('tests/resources/dynamo/compact.json') as f:
            expected_compact = json.load(f, parse_float=Decimal)
            expected_compact['configuredStates'][0]['postalAbbreviation'] = 'invalid'

        with self.assertRaises(ValidationError) as context:
            CompactRecordSchema().load(expected_compact.copy())

        self.assertIn("{'configuredStates': {0: {'postalAbbreviation': ['Must be one of:", str(context.exception))

    def test_compact_config_raises_validation_error_for_missing_configured_state_fields(self):
        """Test that missing required fields in configuredStates raises a ValidationError"""
        from cc_common.data_model.schema.compact.record import CompactRecordSchema

        with open('tests/resources/dynamo/compact.json') as f:
            expected_compact = json.load(f, parse_float=Decimal)
            del expected_compact['configuredStates'][0]['isLive']

        with self.assertRaises(ValidationError) as context:
            CompactRecordSchema().load(expected_compact.copy())

        self.assertIn('configuredStates', str(context.exception))
        self.assertIn('isLive', str(context.exception))

    def test_compact_config_allows_empty_configured_states(self):
        """Test that an empty configuredStates list is valid"""
        from cc_common.data_model.schema.compact.record import CompactRecordSchema

        with open('tests/resources/dynamo/compact.json') as f:
            expected_compact = json.load(f, parse_float=Decimal)
            expected_compact['configuredStates'] = []

        schema = CompactRecordSchema()
        loaded_schema = schema.load(expected_compact.copy())

        compact_data = schema.dump(loaded_schema)
        self.assertEqual([], compact_data['configuredStates'])
