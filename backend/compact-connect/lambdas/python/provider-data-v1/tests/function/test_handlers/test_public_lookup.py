import json
from datetime import datetime
from unittest.mock import patch
from urllib.parse import quote

from moto import mock_aws

from .. import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPublicQueryProviders(TstFunction):
    def test_public_query_by_provider_id_returns_public_allowed_fields(self):
        self._load_provider_data()

        from handlers.public_lookup import public_query_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps({'query': {'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}})

        resp = public_query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('../common/tests/resources/api/provider-response.json') as f:
            expected_provider = json.load(f)
            # we do not return the following fields for the public endpoint
            expected_provider.pop('homeAddressStreet1')
            expected_provider.pop('homeAddressStreet2')
            expected_provider.pop('homeAddressCity')
            expected_provider.pop('homeAddressState')
            expected_provider.pop('homeAddressPostalCode')
            expected_provider.pop('emailAddress')
            expected_provider.pop('phoneNumber')
            expected_provider.pop('cognitoSub')
            expected_provider.pop('birthMonthDay')
            expected_provider.pop('compactConnectRegisteredEmailAddress')
            expected_provider.pop('dateOfExpiration')
            expected_provider.pop('jurisdictionStatus')

        body = json.loads(resp['body'])
        self.assertEqual(
            {
                'providers': [expected_provider],
                'pagination': {'pageSize': 100, 'lastKey': None, 'prevLastKey': None},
                'query': {'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'},
            },
            body,
        )

    def test_public_query_providers_updated_sorting(self):
        from handlers.public_lookup import public_query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        self._generate_providers(home='ne', privilege_jurisdiction='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {'sorting': {'key': 'dateOfUpdate'}, 'query': {'jurisdiction': 'oh'}, 'pagination': {'pageSize': 10}},
        )

        resp = public_query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(10, len(body['providers']))
        self.assertEqual({'providers', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertIsInstance(body['pagination']['lastKey'], str)
        # Check we're actually sorted
        dates_of_update = [provider['dateOfUpdate'] for provider in body['providers']]
        self.assertListEqual(sorted(dates_of_update), dates_of_update)

    def test_public_query_providers_updated_sorting_only_returns_matching_providers_which_have_any_privileges(self):
        """Tests that the public endpoint only returns providers with privileges."""
        from handlers.public_lookup import public_query_providers

        # 30 providers:
        # - 10 with licenses in oh and which have privileges
        # - 10 with privileges in oh
        # - 10 with licenses in oh, but which have no privileges
        # We expect only 20 of the 30 to be returned, as we do not return providers which don't have any privileges
        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9999)
        self._generate_providers(home='ne', privilege_jurisdiction='oh', start_serial=9899)
        self._generate_providers(home='oh', privilege_jurisdiction=None, start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {'sorting': {'key': 'dateOfUpdate'}, 'query': {'jurisdiction': 'oh'}, 'pagination': {'pageSize': 20}},
        )

        resp = public_query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(20, len(body['providers']))
        # Check we're actually sorted
        dates_of_update = [provider['dateOfUpdate'] for provider in body['providers']]
        self.assertListEqual(sorted(dates_of_update), dates_of_update)

    def test_public_query_providers_family_name_sorting(self):
        from handlers.public_lookup import public_query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        # We'll force the first 10 names, to be a set of values we know are challenging characters
        names = [
            ('山田', '1'),
            ('後藤', '2'),
            ('清水', '3'),
            ('近藤', '4'),
            ('Anderson', '5'),
            ('Bañuelos', '6'),
            ('de la Fuente', '7'),
            ('Dennis', '8'),
            ('Figueroa', '9'),
            ('Frías', '10'),
        ]
        self._generate_providers(home='ne', privilege_jurisdiction='oh', start_serial=9999, names=names)
        # We'll leave the last 10 names to be randomly generated to let the Faker data set come up with some
        # interesting values, to leave the door open to identify new edge cases.
        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {'sorting': {'key': 'familyName'}, 'query': {'jurisdiction': 'oh'}, 'pagination': {'pageSize': 10}},
        )

        resp = public_query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(10, len(body['providers']))
        self.assertEqual({'providers', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertEqual({'key': 'familyName', 'direction': 'ascending'}, body['sorting'])
        self.assertIsInstance(body['pagination']['lastKey'], str)
        # Check we're actually sorted
        family_names = [provider['familyName'].lower() for provider in body['providers']]
        self.assertListEqual(sorted(family_names, key=quote), family_names)

    def test_public_query_providers_by_family_name(self):
        from handlers.public_lookup import public_query_providers

        # 10 providers, licenses in oh, and privileges in ne, including a Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            privilege_jurisdiction='ne',
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {
                'sorting': {'key': 'familyName'},
                'query': {'jurisdiction': 'oh', 'familyName': 'Testerly'},
                'pagination': {'pageSize': 10},
            },
        )

        resp = public_query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(2, len(body['providers']))

    def test_public_query_providers_by_family_name_filters_providers_without_privileges(self):
        from handlers.public_lookup import public_query_providers

        # 10 providers, licenses in oh, and privileges in ne, including a Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            privilege_jurisdiction='ne',
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )
        # 10 more providers without privileges, licenses in oh, and privileges in ne, including a Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            privilege_jurisdiction=None,
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {
                'sorting': {'key': 'familyName'},
                'query': {'jurisdiction': 'oh', 'familyName': 'Testerly'},
                'pagination': {'pageSize': 10},
            },
        )

        resp = public_query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(2, len(body['providers']))

    def test_public_query_providers_given_name_only_not_allowed(self):
        from handlers.public_lookup import public_query_providers

        # 10 providers, licenses in oh, and privileges in ne, including a Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            privilege_jurisdiction='ne',
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {
                'sorting': {'key': 'familyName'},
                'query': {'jurisdiction': 'oh', 'givenName': 'Tess'},
                'pagination': {'pageSize': 10},
            },
        )

        resp = public_query_providers(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_query_providers_default_sorting(self):
        """If sorting is not specified, familyName is default"""
        from handlers.public_lookup import public_query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        self._generate_providers(home='ne', privilege_jurisdiction='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps({'query': {}})

        resp = public_query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(20, len(body['providers']))
        self.assertEqual({'providers', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertEqual({'key': 'familyName', 'direction': 'ascending'}, body['sorting'])
        self.assertIsNone(body['pagination']['lastKey'])
        # Check we're actually sorted
        family_names = [provider['familyName'].lower() for provider in body['providers']]
        self.assertListEqual(sorted(family_names, key=quote), family_names)

    def test_public_query_providers_invalid_sorting(self):
        from handlers.public_lookup import public_query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        self._generate_providers(home='ne', privilege_jurisdiction='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps({'query': {'jurisdiction': 'oh'}, 'sorting': {'key': 'invalid'}})

        resp = public_query_providers(event, self.mock_context)

        # Should reject the query, with 400
        self.assertEqual(400, resp['statusCode'])


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPublicGetProvider(TstFunction):
    @staticmethod
    def _get_sensitive_hash():
        with open('../common/tests/resources/dynamo/license-update.json') as f:
            sk = json.load(f)['sk']
        # The actual sensitive part is the hash at the end of the key
        return sk.split('/')[-1]

    def test_public_get_provider_response_with_expected_fields_filtered(self):
        self._load_provider_data()

        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)
            # we do not return the following fields from the public endpoint
            expected_provider.pop('ssnLastFour')
            expected_provider.pop('dateOfBirth')
            expected_provider.pop('homeAddressStreet1')
            expected_provider.pop('homeAddressStreet2')
            expected_provider.pop('homeAddressCity')
            expected_provider.pop('homeAddressState')
            expected_provider.pop('homeAddressPostalCode')
            expected_provider.pop('emailAddress')
            expected_provider.pop('phoneNumber')
            expected_provider.pop('cognitoSub')
            expected_provider.pop('birthMonthDay')
            expected_provider.pop('compactConnectRegisteredEmailAddress')
            expected_provider.pop('militaryAffiliations')
            expected_provider.pop('licenses')
            expected_provider['privileges'][0].pop('attestations')
            expected_provider['privileges'][0].pop('compactTransactionId')
            expected_provider['privileges'][0]['history'][0]['previous'].pop('attestations')
            expected_provider['privileges'][0]['history'][0]['previous'].pop('compactTransactionId')
            expected_provider['privileges'][0]['history'][0]['updatedValues'].pop('compactTransactionId')
            expected_provider.pop('homeJurisdictionSelection')
            expected_provider.pop('dateOfExpiration')
            expected_provider.pop('jurisdictionStatus')

        self.maxDiff = None
        self.assertEqual(expected_provider, provider_data)

        # The sk for a license-update record is sensitive so we'll do an extra, pretty broad, check just to make sure
        # we guard against future changes that might accidentally send the key out via the API. See discussion on
        # key generation in the LicenseUpdateRecordSchema for details.
        sensitive_hash = self._get_sensitive_hash()
        self.assertNotIn(sensitive_hash, resp['body'])

    def test_public_get_provider_missing_provider_id(self):
        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        # providerId _should_ be included in these pathParameters. We're leaving it out for this test.
        event['pathParameters'] = {'compact': 'aslp'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
