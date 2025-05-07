import json

from tests import TstLambdas


class TestRegistration(TstLambdas):
    def test_license_privilege_lookup(self):
        from cc_common.data_model.schema import LicenseRecordSchema, PrivilegeRecordSchema, ProviderRecordSchema
        from cc_common.data_model.schema.base_record import BaseRecordSchema

        with open('tests/resources/dynamo/privilege.json') as f:
            privilege_data = json.load(f)

        with open('tests/resources/dynamo/license.json') as f:
            license_data = json.load(f)

        with open('tests/resources/dynamo/provider.json') as f:
            provider_data = json.load(f)

        privilege_schema = BaseRecordSchema.get_schema_by_type(privilege_data['type'])
        self.assertIsInstance(privilege_schema, PrivilegeRecordSchema)

        license_schema = BaseRecordSchema.get_schema_by_type(license_data['type'])
        self.assertIsInstance(license_schema, LicenseRecordSchema)

        provider_schema = BaseRecordSchema.get_schema_by_type(provider_data['type'])
        self.assertIsInstance(provider_schema, ProviderRecordSchema)

    def test_invalid_type(self):
        from cc_common.data_model.schema.base_record import BaseRecordSchema
        from cc_common.exceptions import CCInternalException

        with self.assertRaises(CCInternalException):
            BaseRecordSchema.get_schema_by_type('some-unsupported-type')


class TestCalculatedStatusRecordSchema(TstLambdas):
    def test_compact_eligibility_set_to_ineligible_if_license_encumbered(self):
        from cc_common.data_model.schema.base_record import CalculatedStatusRecordSchema
        from cc_common.data_model.schema.common import (
            ActiveInactiveStatus,
            CompactEligibilityStatus,
            LicenseEncumberedStatusEnum,
        )

        schema = CalculatedStatusRecordSchema()

        # test a provider which has an encumbered status as a result of their license being encumbered
        # this should force the compactEligibility field to calculate as ineligible
        test_record = {
            'jurisdictionUploadedLicenseStatus': ActiveInactiveStatus.ACTIVE,
            'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
            'encumberedStatus': LicenseEncumberedStatusEnum.ENCUMBERED,
            'dateOfExpiration': '2050-01-01',
            'pk': 'alsp#PROVIDER#1234567890',
            'sk': 'alsp#PROVIDER',
            'type': 'provider',
            'dateOfUpdate': '2025-01-01T00:00:00Z',
        }

        result = schema.load(test_record)
        self.assertEqual(CompactEligibilityStatus.INELIGIBLE.value, result['compactEligibility'])

    def test_license_status_set_to_inactive_if_license_encumbered(self):
        from cc_common.data_model.schema.base_record import CalculatedStatusRecordSchema
        from cc_common.data_model.schema.common import (
            ActiveInactiveStatus,
            CompactEligibilityStatus,
            LicenseEncumberedStatusEnum,
        )

        schema = CalculatedStatusRecordSchema()

        # test a provider which has an encumbered status as a result of their license being encumbered
        # this should force the licenseStatus field to calculate as ineligible
        test_record = {
            'jurisdictionUploadedLicenseStatus': ActiveInactiveStatus.ACTIVE,
            'jurisdictionUploadedCompactEligibility': CompactEligibilityStatus.ELIGIBLE,
            'encumberedStatus': LicenseEncumberedStatusEnum.ENCUMBERED,
            'dateOfExpiration': '2050-01-01',
            'pk': 'alsp#PROVIDER#1234567890',
            'sk': 'alsp#PROVIDER',
            'type': 'provider',
            'dateOfUpdate': '2025-01-01T00:00:00Z',
        }

        result = schema.load(test_record)
        self.assertEqual(ActiveInactiveStatus.INACTIVE.value, result['licenseStatus'])
