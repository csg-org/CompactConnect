import json
import os
import unittest
from datetime import date
from uuid import UUID

from marshmallow import ValidationError


def _configure_cc_common_for_tests():
    os.environ.setdefault('AWS_DEFAULT_REGION', 'us-east-1')
    os.environ.setdefault(
        'COMPACTS',
        '["psypact"]',
    )
    os.environ.setdefault(
        'JURISDICTIONS',
        json.dumps(['co', 'oh', 'ut']),
    )
    os.environ.setdefault(
        'LICENSE_TYPES',
        json.dumps(
            {
                'psypact': [
                    {'name': 'Psychologist', 'abbreviation': 'psych'},
                    {'name': 'School Psychologist', 'abbreviation': 'schpsych'},
                ],
            },
        ),
    )
    import cc_common.config

    cc_common.config.config = cc_common.config._Config()  # noqa: SLF001


class TestPsypactLicenseSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _configure_cc_common_for_tests()
        # Load the app record module first so common_lambdas can import BaseRecordSchema without
        # a circular import through cc_common.data_model.schema.__init__.
        import cc_common.data_model.schema.license.record  # noqa: F401

    def test_dump_generates_keys_without_npi(self):
        from uuid import UUID

        from common_lambdas.schema.license import PsypactLicenseSchema

        schema = PsypactLicenseSchema()
        dumped = schema.dump(
            {
                'type': 'license',
                'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                'compact': 'psypact',
                'jurisdiction': 'co',
                'ssnLastFour': '1234',
                'licenseNumber': 'PSY-12345',
                'licenseType': 'Psychologist',
                'professionalType': 'Clinical',
                'givenName': 'Jane',
                'familyName': 'Doe',
                'dateOfIssuance': date.fromisoformat('2010-06-06'),
                'dateOfExpiration': date.fromisoformat('2025-04-04'),
                'dateOfBirth': date.fromisoformat('1985-06-06'),
                'homeAddressStreet1': '123 A St.',
                'homeAddressCity': 'Denver',
                'homeAddressState': 'co',
                'homeAddressPostalCode': '80202',
                'jurisdictionUploadedLicenseStatus': 'active',
                'jurisdictionUploadedCompactEligibility': 'eligible',
            },
        )

        self.assertNotIn('npi', dumped)
        self.assertEqual('psypact#PROVIDER#89a6377e-c3a5-40e5-bca5-317ec854c570', dumped['pk'])
        self.assertEqual('psypact#PROVIDER#license/co/psych#', dumped['sk'])
        self.assertEqual('PSY-12345', dumped['licenseNumber'])
        self.assertEqual('Clinical', dumped['professionalType'])

    def test_license_number_required(self):
        from common_lambdas.schema.license import PsypactLicenseSchema

        with self.assertRaises(ValidationError):
            PsypactLicenseSchema().load(
                {
                    'type': 'license',
                    'providerId': UUID('89a6377e-c3a5-40e5-bca5-317ec854c570'),
                    'compact': 'psypact',
                    'jurisdiction': 'co',
                    'ssnLastFour': '1234',
                    'licenseType': 'Psychologist',
                    'givenName': 'Jane',
                    'familyName': 'Doe',
                    'dateOfIssuance': '2010-06-06',
                    'dateOfExpiration': '2025-04-04',
                    'dateOfBirth': '1985-06-06',
                    'homeAddressStreet1': '123 A St.',
                    'homeAddressCity': 'Denver',
                    'homeAddressState': 'co',
                    'homeAddressPostalCode': '80202',
                    'jurisdictionUploadedLicenseStatus': 'active',
                    'jurisdictionUploadedCompactEligibility': 'eligible',
                    'licenseGSIPK': 'C#psypact#J#co',
                    'licenseGSISK': 'FN#doe#GN#jane',
                },
            )


if __name__ == '__main__':
    unittest.main()
