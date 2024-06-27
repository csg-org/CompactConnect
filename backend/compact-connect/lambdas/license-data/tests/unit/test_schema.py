import json

from marshmallow import ValidationError

from tests import TstLambdas


class TestLicensePostSchema(TstLambdas):
    def test_validate(self):
        from schema import LicensePostSchema

        with open('tests/resources/license.json', 'r') as f:
            LicensePostSchema().load(json.load(f))

    def test_invalid(self):
        from schema import LicensePostSchema

        with open('tests/resources/license.json', 'r') as f:
            license_data = json.load(f)
        license_data.pop('ssn')

        with self.assertRaises(ValidationError):
            LicensePostSchema().load(license_data)
