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
        from cc_common.data_model.schema.adverse_action import AdverseAction

        with open('tests/resources/dynamo/adverse-action-license.json') as f:
            adverse_action_data = json.load(f)

        test_invalid_adverse_action = AdverseAction.from_dict(adverse_action_data)
        test_invalid_adverse_action.action_against = 'invalid'

        with self.assertRaises(ValidationError):
            AdverseAction.from_dict(test_invalid_adverse_action.serialize_to_data())

    def test_adverse_action_id_is_generated_if_not_provided(self):
        """Test that an adverseActionId is generated if not provided during dump()"""
        from cc_common.data_model.schema.adverse_action import AdverseAction


        with open('tests/resources/dynamo/adverse-action-license.json') as f:
            adverse_action_data = json.load(f)

        # Load the data to convert strings to proper types
        test_adverse_action = AdverseAction.from_dict(adverse_action_data)

        # Verify adverseActionId is not in the loaded data
        test_adverse_action._data.pop('adverseActionId')

        # Dump the data and verify adverseActionId is generated
        dumped_data = test_adverse_action.serialize_to_data()
        self.assertIn('adverseActionId', dumped_data)
        self.assertIsInstance(dumped_data['adverseActionId'], str)


class TestAdverseActionDataClass(TstLambdas):
    def test_adverse_action_data_class_serde_round_trip(self):
        from cc_common.data_model.schema.adverse_action import AdverseAction

        with open('tests/resources/dynamo/adverse-action-license.json') as f:
            adverse_action_data = json.load(f)

        adverse_action = AdverseAction.from_dict(adverse_action_data)
        self.assertIsInstance(adverse_action, AdverseAction)

        dumped_data = adverse_action.serialize_to_data()
        # Drop dynamic fields
        del adverse_action_data['dateOfUpdate']
        del dumped_data['dateOfUpdate']
        self.assertEqual(adverse_action_data, dumped_data)

    def test_adverse_action_data_class_getters_return_expected_values(self):
        from cc_common.data_model.schema.adverse_action import AdverseAction

        with open('tests/resources/dynamo/adverse-action-license.json') as f:
            adverse_action_data = json.load(f)

        adverse_action = AdverseAction.from_dict(adverse_action_data)
        self.assertEqual(str(adverse_action.provider_id), adverse_action_data['providerId'])
        self.assertEqual(adverse_action.jurisdiction, adverse_action_data['jurisdiction'])
        self.assertEqual(adverse_action.license_type, adverse_action_data['licenseType'])
        self.assertEqual(adverse_action.action_against, adverse_action_data['actionAgainst'])
        self.assertEqual(adverse_action.blocks_future_privileges, adverse_action_data['blocksFuturePrivileges'])
        self.assertEqual(adverse_action.clinical_privilege_action_category, adverse_action_data['clinicalPrivilegeActionCategory'])
        self.assertEqual(adverse_action.creation_effective_date.isoformat(), adverse_action_data['creationEffectiveDate'])
        self.assertEqual(str(adverse_action.submitting_user), adverse_action_data['submittingUser'])
        self.assertEqual(adverse_action.creation_date.isoformat(), adverse_action_data['creationDate'])
        self.assertEqual(str(adverse_action.adverse_action_id), adverse_action_data['adverseActionId'])
        

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
