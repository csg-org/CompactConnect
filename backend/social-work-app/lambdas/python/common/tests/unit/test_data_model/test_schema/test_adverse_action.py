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

    def test_home_jurisdiction_is_not_exposed_in_any_adverse_action_api_response(self):
        """
        This field exists to route records during an SSN correction, and nothing outside the backend needs
        it. Keeping it out of both response schemas means no frontend work to absorb, so the test covers the
        general schema as well as the public one - the general schema is the one someone would reach for
        first if they wanted to surface it.
        """
        from cc_common.data_model.schema.adverse_action.api import (
            AdverseActionGeneralResponseSchema,
            AdverseActionPublicResponseSchema,
        )

        adverse_action = self.test_data_generator.generate_default_adverse_action().to_dict()
        adverse_action['dateOfUpdate'] = adverse_action.get('dateOfUpdate', '2024-11-08T23:59:59+00:00')

        for schema_class in (AdverseActionPublicResponseSchema, AdverseActionGeneralResponseSchema):
            with self.subTest(schema=schema_class.__name__):
                response = schema_class().dump(schema_class().load(adverse_action))
                self.assertNotIn('homeJurisdictionAtTimeOfCreation', response)

    def test_home_jurisdiction_at_time_of_creation_is_required(self):
        """
        The migration reads this field to decide whether a privilege's records follow a corrected
        multi-state license, so a record without it cannot be placed. Required rather than defaulted.
        """
        from cc_common.data_model.schema.adverse_action.record import AdverseActionRecordSchema

        adverse_action_data = self.test_data_generator.generate_default_adverse_action().to_dict()
        adverse_action_data.pop('homeJurisdictionAtTimeOfCreation')

        with self.assertRaises(ValidationError) as context:
            AdverseActionRecordSchema().load(adverse_action_data)

        self.assertIn('homeJurisdictionAtTimeOfCreation', context.exception.messages)

    def test_home_jurisdiction_at_time_of_creation_must_be_a_valid_jurisdiction(self):
        from cc_common.data_model.schema.adverse_action.record import AdverseActionRecordSchema

        adverse_action_data = self.test_data_generator.generate_default_adverse_action().to_dict()
        adverse_action_data['homeJurisdictionAtTimeOfCreation'] = 'not-a-jurisdiction'

        with self.assertRaises(ValidationError) as context:
            AdverseActionRecordSchema().load(adverse_action_data)

        self.assertIn('homeJurisdictionAtTimeOfCreation', context.exception.messages)

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
        adverse_action_data.licenseTypeAbbreviation = 'lcsw'

        with self.assertRaises(ValidationError):
            AdverseActionData.from_database_record(adverse_action_data.serialize_to_database_record())

    def test_invalid_license_type_abbreviation(self):
        from cc_common.data_model.schema.adverse_action import AdverseActionData

        adverse_action_data = self.test_data_generator.generate_default_adverse_action()

        # setting to a valid license type name, and an invalid abbreviation
        adverse_action_data.licenseType = 'licensed clinical social worker'
        adverse_action_data.licenseTypeAbbreviation = 'foo'

        with self.assertRaises(ValidationError):
            AdverseActionData.from_database_record(adverse_action_data.serialize_to_database_record())


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
            adverse_action.clinicalPrivilegeActionCategories, adverse_action_data['clinicalPrivilegeActionCategories']
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
                'encumbranceType': 'suspension',
                'clinicalPrivilegeActionCategories': ['Fraud, Deception, or Misrepresentation'],
                'compact': 'socw',
                'creationDate': '2024-11-08T23:59:59+00:00',
                'effectiveStartDate': '2024-02-15',
                'jurisdiction': 'ne',
                'licenseType': 'licensed clinical social worker',
                'licenseTypeAbbreviation': 'lcsw',
                'homeJurisdictionAtTimeOfCreation': 'oh',
                'pk': 'socw#PROVIDER#89a6377e-c3a5-40e5-bca5-317ec854c570',
                'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                'licenseScope': 'single-state',
                'sk': 'socw#PROVIDER#privilege/ne/lcsw/single-state#ADVERSE_ACTION#98765432-9876-9876-9876-987654321098',  # noqa: E501
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

    def test_validate_post_with_multiple_categories(self):
        """Test that multiple clinical privilege action categories are accepted"""
        from cc_common.data_model.schema.adverse_action.api import AdverseActionPostRequestSchema

        with open('tests/resources/api/adverse-action-post.json') as f:
            adverse_action_data = json.load(f)
        adverse_action_data['clinicalPrivilegeActionCategories'] = [
            'Fraud, Deception, or Misrepresentation',
            'Substandard Care or Patient Neglect/Abuse',
        ]

        result = AdverseActionPostRequestSchema().load(adverse_action_data)
        self.assertEqual(
            [
                'Fraud, Deception, or Misrepresentation',
                'Substandard Care or Patient Neglect/Abuse',
            ],
            result['clinicalPrivilegeActionCategories'],
        )

    def test_invalid_post_with_empty_categories(self):
        """Test validation error when clinical privilege action categories list is empty"""
        from cc_common.data_model.schema.adverse_action.api import AdverseActionPostRequestSchema

        with open('tests/resources/api/adverse-action-post.json') as f:
            adverse_action_data = json.load(f)
        adverse_action_data['clinicalPrivilegeActionCategories'] = []

        with self.assertRaises(ValidationError):
            AdverseActionPostRequestSchema().load(adverse_action_data)

    def test_invalid_post(self):
        """Test validation error when required field is missing"""
        from cc_common.data_model.schema.adverse_action.api import AdverseActionPostRequestSchema

        with open('tests/resources/api/adverse-action-post.json') as f:
            adverse_action_data = json.load(f)
        adverse_action_data.pop('encumbranceEffectiveDate')

        with self.assertRaises(ValidationError):
            AdverseActionPostRequestSchema().load(adverse_action_data)
