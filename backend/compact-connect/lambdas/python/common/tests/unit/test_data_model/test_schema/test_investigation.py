from marshmallow import ValidationError

from tests import TstLambdas


class TestInvestigationRecordSchema(TstLambdas):
    def setUp(self):
        from common_test.test_data_generator import TestDataGenerator

        self.test_data_generator = TestDataGenerator

    def test_serde(self):
        """Test round-trip deserialization/serialization"""
        from cc_common.data_model.schema.investigation.record import InvestigationRecordSchema

        expected_investigation = (
            self.test_data_generator.generate_default_investigation().serialize_to_database_record()
        )

        schema = InvestigationRecordSchema()
        loaded_schema = schema.load(expected_investigation.copy())

        investigation_data = schema.dump(loaded_schema)

        # Pop dynamic fields
        expected_investigation.pop('dateOfUpdate')
        investigation_data.pop('dateOfUpdate')

        self.assertEqual(expected_investigation, investigation_data)

    def test_invalid(self):
        from cc_common.data_model.schema.investigation.record import InvestigationRecordSchema

        investigation_data = self.test_data_generator.generate_default_investigation().to_dict()
        investigation_data.pop('providerId')

        with self.assertRaises(ValidationError):
            InvestigationRecordSchema().load(investigation_data)

    def test_invalid_investigation_against(self):
        from cc_common.data_model.schema.common import CompactEligibilityStatus
        from cc_common.data_model.schema.investigation import InvestigationData

        investigation_data = self.test_data_generator.generate_default_investigation()

        # setting to an invalid value from another enum
        investigation_data.investigationAgainst = CompactEligibilityStatus.ELIGIBLE

        with self.assertRaises(ValidationError):
            InvestigationData.from_database_record(investigation_data.serialize_to_database_record())

    def test_invalid_license_type(self):
        from cc_common.data_model.schema.investigation import InvestigationData

        investigation_data = self.test_data_generator.generate_default_investigation()

        # setting to an invalid license type name
        investigation_data.licenseType = 'foobar'

        with self.assertRaises(ValidationError):
            InvestigationData.from_database_record(investigation_data.serialize_to_database_record())


class TestInvestigationDataClass(TstLambdas):
    def setUp(self):
        from common_test.test_data_generator import TestDataGenerator

        self.test_data_generator = TestDataGenerator

    def test_investigation_data_class_getters_return_expected_values(self):
        from cc_common.data_model.schema.investigation import InvestigationData

        investigation_data = self.test_data_generator.generate_default_investigation()

        investigation = InvestigationData.from_database_record(investigation_data.serialize_to_database_record())

        # Use to_dict() method to get expected values
        expected_investigation = investigation.to_dict()

        # Create actual object with all fields from database record
        actual_investigation = {
            'providerId': investigation_data.providerId,
            'jurisdiction': investigation_data.jurisdiction,
            'investigationAgainst': investigation_data.investigationAgainst,
            'submittingUser': investigation_data.submittingUser,
            'investigationId': investigation_data.investigationId,
            'compact': investigation_data.compact,
            'creationDate': investigation_data.creationDate,
            'licenseType': investigation_data.licenseType,
            'type': investigation_data.type,
        }

        # Pop dynamic fields from expected object
        expected_investigation.pop('dateOfUpdate')

        self.assertEqual(expected_investigation, actual_investigation)

    def test_investigation_data_class_outputs_expected_database_object(self):
        # check final snapshot of expected data
        investigation_data = self.test_data_generator.generate_default_investigation().serialize_to_database_record()
        # Pop dynamic field
        investigation_data.pop('dateOfUpdate')

        self.assertEqual(
            {
                'investigationAgainst': 'privilege',
                'investigationId': '98765432-9876-9876-9876-987654321098',
                'compact': 'aslp',
                'creationDate': '2024-11-08T23:59:59+00:00',
                'jurisdiction': 'ne',
                'licenseType': 'speech-language pathologist',
                'pk': 'aslp#PROVIDER#89a6377e-c3a5-40e5-bca5-317ec854c570',
                'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                'sk': 'aslp#PROVIDER#privilege/ne/slp#INVESTIGATION#98765432-9876-9876-9876-987654321098',
                'submittingUser': '12a6377e-c3a5-40e5-bca5-317ec854c556',
                'type': 'investigation',
            },
            investigation_data,
        )


class TestInvestigationPatchRequestSchema(TstLambdas):
    def test_validate_patch(self):
        """Test validation of a PATCH request (empty body is valid)"""
        from cc_common.data_model.schema.investigation.api import InvestigationPatchRequestSchema

        # PATCH schema has no required fields
        result = InvestigationPatchRequestSchema().load({})
        self.assertIsInstance(result, dict)

    def test_validate_patch_with_encumbrance(self):
        """Test validation of a PATCH request with encumbrance"""
        from cc_common.data_model.schema.investigation.api import InvestigationPatchRequestSchema

        investigation_data = {
            'encumbrance': {
                'encumbranceEffectiveDate': '2024-03-15',
                'encumbranceType': 'suspension',
                'clinicalPrivilegeActionCategory': 'Unsafe Practice or Substandard Care',
            }
        }
        result = InvestigationPatchRequestSchema().load(investigation_data)
        self.assertIsInstance(result, dict)

    def test_validate_patch_with_unknown_fields(self):
        """Test validation passes even with unknown fields (ForgivingSchema)"""
        from cc_common.data_model.schema.investigation.api import InvestigationPatchRequestSchema

        # ForgivingSchema allows unknown fields
        investigation_data = {'unsupportedField': 'bad'}

        # This should not raise an error
        result = InvestigationPatchRequestSchema().load(investigation_data)
        self.assertIsInstance(result, dict)
