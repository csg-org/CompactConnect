import json
from datetime import date, datetime
from unittest.mock import patch

from moto import mock_aws

from .. import TstFunction

# ProviderPublicResponseSchema + LicensePublicResponseSchema + PrivilegePublicResponseSchema
EXPECTED_PROVIDER_RESPONSE = {
    'type': 'provider',
    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
    'dateOfUpdate': '2024-07-08T23:59:59+00:00',
    'compact': 'socw',
    'licenseJurisdiction': 'oh',
    'licenseStatus': 'active',
    'compactEligibility': 'eligible',
    'givenName': 'Björk',
    'middleName': 'Gunnar',
    'familyName': 'Guðmundsdóttir',
    'licenses': [
        {
            'type': 'license',
            'compact': 'socw',
            'jurisdiction': 'oh',
            'licenseType': 'licensed clinical social worker',
            'licenseScope': 'single-state',
            'licenseStatus': 'active',
            'compactEligibility': 'eligible',
            'dateOfExpiration': '2025-04-04',
            'licenseNumber': 'A0608337260',
        }
    ],
    'privileges': [
        {
            'type': 'privilege',
            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
            'compact': 'socw',
            'jurisdiction': 'ne',
            'licenseJurisdiction': 'oh',
            'licenseType': 'licensed clinical social worker',
            'dateOfExpiration': '2025-04-04',
            'administratorSetStatus': 'active',
            'status': 'active',
        }
    ],
}


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPublicGetProvider(TstFunction):
    def setUp(self):
        super().setUp()
        self.set_live_compact_jurisdictions_for_test({'socw': ['ne']})

    def test_public_get_provider_response_with_expected_fields_filtered(self):
        self._load_provider_data()

        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'socw', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        self.assertEqual(EXPECTED_PROVIDER_RESPONSE, provider_data)

    def test_public_get_provider_response_only_returns_most_recent_licenses(self):
        self._load_provider_data()
        # adding another license for same license type from another state, with an older issuance and renewal date
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'dateOfIssuance': date(2019, 1, 1),
                'dateOfRenewal': date(2020, 1, 1),
                'licenseNumber': 'olderCosmLicense',
                'jurisdiction': 'az',
            }
        )

        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'socw', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        # the older license should not be included in the response
        self.assertEqual(EXPECTED_PROVIDER_RESPONSE, provider_data)

    def test_public_get_provider_response_returns_multiple_license_types(self):
        self._load_provider_data()
        # adding another license for same license type from another state, with an older issuance and renewal date
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'dateOfIssuance': date(2019, 1, 1),
                'dateOfRenewal': date(2020, 1, 1),
                'licenseNumber': 'olderCosmLicense',
                'jurisdiction': 'az',
            }
        )

        # add two more licenses for another license type
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'licenseType': 'licensed master social worker',
                'dateOfIssuance': date(2019, 1, 1),
                'dateOfRenewal': date(2020, 1, 1),
                'licenseNumber': 'olderEstLicense',
                'jurisdiction': 'az',
            }
        )
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'licenseType': 'licensed master social worker',
                'dateOfIssuance': date(2024, 1, 1),
                'dateOfRenewal': date(2025, 1, 1),
                'jurisdiction': 'oh',
                'licenseNumber': 'mostRecentEstLicense',
                'dateOfExpiration': date(2026, 1, 1),
            }
        )

        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'socw', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        # the older license should not be included in the response
        expected_licenses = [
            {
                'type': 'license',
                'compact': 'socw',
                'jurisdiction': 'oh',
                'licenseType': 'licensed clinical social worker',
                'licenseScope': 'single-state',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
                'dateOfExpiration': '2025-04-04',
                'licenseNumber': 'A0608337260',
            },
            {
                'type': 'license',
                'compact': 'socw',
                'jurisdiction': 'oh',
                'licenseType': 'licensed master social worker',
                'licenseScope': 'single-state',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
                'dateOfExpiration': '2026-01-01',
                'licenseNumber': 'mostRecentEstLicense',
            },
        ]
        self.assertEqual(expected_licenses, provider_data['licenses'])

    def test_public_get_provider_missing_provider_id(self):
        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        # providerId _should_ be included in these pathParameters. We're leaving it out for this test.
        event['pathParameters'] = {'compact': 'socw'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
