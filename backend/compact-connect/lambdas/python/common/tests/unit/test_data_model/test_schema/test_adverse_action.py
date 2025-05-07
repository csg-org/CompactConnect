import json

from marshmallow import ValidationError

from tests import TstLambdas


class TestAdverseActionRecordSchema(TstLambdas):
    def setUp(self):
        from common_test.test_data_generator import TestDataGenerator

        self.test_data_generator = TestDataGenerator

    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.adverse_action.record import AdverseActionRecordSchema

        expected_adverse_action = (
            self.test_data_generator.generate_default_adverse_action().serialize_to_database_record()
        )

        schema = AdverseActionRecordSchema()
        loaded_schema = schema.load(expected_adverse_action.copy())

        adverse_action_data = schema.dump(loaded_schema)

        # Drop dynamic fields
        del expected_adverse_action['dateOfUpdate']
        del adverse_action_data['dateOfUpdate']

        self.assertEqual(expected_adverse_action, adverse_action_data)

    def test_invalid(self):
        from cc_common.data_model.schema.adverse_action.record import AdverseActionRecordSchema

        adverse_action_data = self.test_data_generator.generate_default_adverse_action().to_dict()
        adverse_action_data.pop('providerId')

        with self.assertRaises(ValidationError):
            AdverseActionRecordSchema().load(adverse_action_data)

    def test_invalid_action_against(self):
        from cc_common.data_model.schema.adverse_action import AdverseActionData
        from cc_common.data_model.schema.common import CompactEligibilityStatus

        adverse_action_data = self.test_data_generator.generate_default_adverse_action()

        # setting to an invalid value from another enum
        adverse_action_data.actionAgainst = CompactEligibilityStatus.ELIGIBLE

        with self.assertRaises(ValidationError):
            AdverseActionData.from_database_record(adverse_action_data.serialize_to_database_record())

    def test_invalid_license_type(self):
        from cc_common.data_model.schema.adverse_action import AdverseActionData

        adverse_action_data = self.test_data_generator.generate_default_adverse_action()

        # setting to an invalid license type name, with a valid abbreviation
        adverse_action_data.licenseType = 'foobar'
        adverse_action_data.license_abbreviation = 'slp'

        with self.assertRaises(ValidationError):
            AdverseActionData.from_database_record(adverse_action_data.serialize_to_database_record())

    def test_invalid_license_type_abbreviation(self):
        from cc_common.data_model.schema.adverse_action import AdverseActionData

        adverse_action_data = self.test_data_generator.generate_default_adverse_action()

        # setting to a valid license type name, and an invalid abbreviation
        adverse_action_data.licenseType = 'speech-language pathologist'
        adverse_action_data.licenseTypeAbbreviation = 'foo'

        with self.assertRaises(ValidationError):
            AdverseActionData.from_database_record(adverse_action_data.serialize_to_database_record())

    def test_adverse_action_id_is_generated_if_not_provided(self):
        """Test that an adverseActionId is generated if not provided during dump()"""
        from cc_common.data_model.schema.adverse_action.record import AdverseActionRecordSchema

        adverse_action_data = self.test_data_generator.generate_default_adverse_action().to_dict()

        #  adverseActionId is not in the loaded data
        adverse_action_data.pop('adverseActionId')

        # Dump the data and verify adverseActionId is generated
        dumped_data = AdverseActionRecordSchema().dump(adverse_action_data)
        self.assertIn('adverseActionId', dumped_data)
        self.assertIsInstance(dumped_data['adverseActionId'], str)


class TestAdverseActionDataClass(TstLambdas):
    def setUp(self):
        from common_test.test_data_generator import TestDataGenerator

        self.test_data_generator = TestDataGenerator

    def test_adverse_action_data_class_getters_return_expected_values(self):
        from cc_common.data_model.schema.adverse_action import AdverseActionData

        adverse_action_data = self.test_data_generator.generate_default_adverse_action().serialize_to_database_record()

        adverse_action = AdverseActionData.from_database_record(adverse_action_data)
        self.assertEqual(str(adverse_action.providerId), adverse_action_data['providerId'])
        self.assertEqual(adverse_action.jurisdiction, adverse_action_data['jurisdiction'])
        self.assertEqual(adverse_action.licenseTypeAbbreviation, adverse_action_data['licenseTypeAbbreviation'])
        self.assertEqual(adverse_action.actionAgainst, adverse_action_data['actionAgainst'])
        self.assertEqual(
            adverse_action.clinicalPrivilegeActionCategory, adverse_action_data['clinicalPrivilegeActionCategory']
        )
        self.assertEqual(adverse_action.effectiveStartDate.isoformat(), adverse_action_data['effectiveStartDate'])
        self.assertEqual(str(adverse_action.submittingUser), adverse_action_data['submittingUser'])
        self.assertEqual(adverse_action.creationDate.isoformat(), adverse_action_data['creationDate'])
        self.assertEqual(str(adverse_action.adverseActionId), adverse_action_data['adverseActionId'])

    def test_adverse_action_data_class_outputs_expected_database_object(self):
        # check final snapshot of expected data
        adverse_action_data = self.test_data_generator.generate_default_adverse_action().serialize_to_database_record()
        # remove dynamic field
        del adverse_action_data['dateOfUpdate']

        self.assertEqual(
            {
                'actionAgainst': 'privilege',
                'adverseActionId': '98765432-9876-9876-9876-987654321098',
                'clinicalPrivilegeActionCategory': 'Unsafe Practice or Substandard Care',
                'compact': 'aslp',
                'creationDate': '2024-11-08T23:59:59+00:00',
                'effectiveStartDate': '2024-02-15',
                'jurisdiction': 'ne',
                'licenseType': 'speech-language pathologist',
                'licenseTypeAbbreviation': 'slp',
                'pk': 'aslp#PROVIDER#89a6377e-c3a5-40e5-bca5-317ec854c570',
                'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                'sk': 'aslp#PROVIDER#privilege/ne/slp#ADVERSE_ACTION#98765432-9876-9876-9876-987654321098',
                'submittingUser': '12a6377e-c3a5-40e5-bca5-317ec854c556',
                'type': 'adverseAction',
            },
            adverse_action_data,
        )


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
        adverse_action_data.pop('encumbranceEffectiveDate')

        with self.assertRaises(ValidationError):
            AdverseActionPostRequestSchema().load(adverse_action_data)
