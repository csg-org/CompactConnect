import json

from marshmallow import ValidationError

from tests import TstLambdas


class TestAdverseActionRecordSchema(TstLambdas):
    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.adverse_action.record import AdverseActionRecordSchema

        with open('tests/resources/dynamo/adverse-action-license.json') as f:
            expected_adverse_action = json.load(f)

        schema = AdverseActionRecordSchema()
        loaded_schema = schema.load(expected_adverse_action.copy())

        adverse_action_data = schema.dump(loaded_schema)

        # Drop dynamic fields
        del expected_adverse_action['dateOfUpdate']
        del adverse_action_data['dateOfUpdate']

        self.assertEqual(expected_adverse_action, adverse_action_data)

    def test_invalid(self):
        from cc_common.data_model.schema.adverse_action.record import AdverseActionRecordSchema

        with open('tests/resources/dynamo/adverse-action-license.json') as f:
            adverse_action_data = json.load(f)
        adverse_action_data.pop('providerId')

        with self.assertRaises(ValidationError):
            AdverseActionRecordSchema().load(adverse_action_data)

    def test_invalid_action_against(self):
        from cc_common.data_model.schema.adverse_action.record import AdverseActionRecordSchema

        with open('tests/resources/dynamo/adverse-action-license.json') as f:
            adverse_action_data = json.load(f)
        adverse_action_data['actionAgainst'] = 'invalid'

        with self.assertRaises(ValidationError):
            AdverseActionRecordSchema().load(adverse_action_data)

    def test_adverse_action_id_is_generated_if_not_provided(self):
        """Test that an adverseActionId is generated if not provided during dump()"""
        from cc_common.data_model.schema.adverse_action.record import AdverseActionRecordSchema

        with open('tests/resources/dynamo/adverse-action-license.json') as f:
            adverse_action_data = json.load(f)

        # Load the data to convert strings to proper types
        schema = AdverseActionRecordSchema()
        loaded_data = schema.load(adverse_action_data)

        # Verify adverseActionId is not in the loaded data
        loaded_data.pop('adverseActionId')

        # Dump the data and verify adverseActionId is generated
        dumped_data = schema.dump(loaded_data)
        self.assertIn('adverseActionId', dumped_data)
        self.assertIsInstance(dumped_data['adverseActionId'], str)


class TestAdverseActionPostRequestSchema(TstLambdas):
    def test_validate_post(self):
        """Test validation of a POST request"""
        from cc_common.data_model.schema.adverse_action.api import AdverseActionPostRequestSchema

        with open('tests/resources/api/adverse-action-post.json') as f:
            AdverseActionPostRequestSchema().load(json.load(f))

    def test_invalid_post(self):
        """Test validation error when required field is missing"""
        from cc_common.data_model.schema.adverse_action.api import AdverseActionPostRequestSchema

        with open('tests/resources/api/adverse-action-post.json') as f:
            adverse_action_data = json.load(f)
        adverse_action_data.pop('encumberanceEffectiveDate')

        with self.assertRaises(ValidationError):
            AdverseActionPostRequestSchema().load(adverse_action_data)
