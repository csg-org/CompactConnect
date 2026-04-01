import json
from datetime import datetime
from unittest.mock import patch

from moto import mock_aws

from .. import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPublicGetProvider(TstFunction):
    def setUp(self):
        super().setUp()
        self.set_live_compact_jurisdictions_for_test({'cosm': ['ne']})

    def test_public_get_provider_response_with_expected_fields_filtered(self):
        self._load_provider_data()

        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'cosm', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        # ProviderPublicResponseSchema + LicensePublicResponseSchema + PrivilegePublicResponseSchema
        expected_provider = {
            'type': 'provider',
            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
            'dateOfUpdate': '2024-07-08T23:59:59+00:00',
            'compact': 'cosm',
            'licenseJurisdiction': 'oh',
            'licenseStatus': 'active',
            'compactEligibility': 'eligible',
            'givenName': 'Björk',
            'middleName': 'Gunnar',
            'familyName': 'Guðmundsdóttir',
            'licenses': [
                {
                    'type': 'license',
                    'compact': 'cosm',
                    'jurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
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
                    'compact': 'cosm',
                    'jurisdiction': 'ne',
                    'licenseJurisdiction': 'oh',
                    'licenseType': 'cosmetologist',
                    'dateOfExpiration': '2025-04-04',
                    'administratorSetStatus': 'active',
                    'status': 'active',
                }
            ],
        }

        self.assertEqual(expected_provider, provider_data)

    def test_public_get_provider_missing_provider_id(self):
        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        # providerId _should_ be included in these pathParameters. We're leaving it out for this test.
        event['pathParameters'] = {'compact': 'cosm'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
