import json
from urllib.parse import quote

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestQueryProviders(TstFunction):
    def test_query_by_ssn(self):
        self._load_provider_data()

        from handlers.providers import query_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps({'query': {'ssn': '123-12-1234'}})

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('../common/tests/resources/api/provider-response.json') as f:
            expected_provider = json.load(f)

        body = json.loads(resp['body'])

        self.assertEqual(
            {
                'providers': [expected_provider],
                'pagination': {'pageSize': 100, 'lastKey': None, 'prevLastKey': None},
                'query': {'ssn': '123-12-1234'},
            },
            body,
        )

    def test_query_by_provider_id(self):
        self._load_provider_data()

        from handlers.providers import query_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps({'query': {'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}})

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('../common/tests/resources/api/provider-response.json') as f:
            expected_provider = json.load(f)

        body = json.loads(resp['body'])
        self.assertEqual(
            {
                'providers': [expected_provider],
                'pagination': {'pageSize': 100, 'lastKey': None, 'prevLastKey': None},
                'query': {'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'},
            },
            body,
        )

    def test_query_providers_updated_sorting(self):
        from handlers.providers import query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        self._generate_providers(home='ne', privilege='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {'sorting': {'key': 'dateOfUpdate'}, 'query': {'jurisdiction': 'oh'}, 'pagination': {'pageSize': 10}},
        )

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(10, len(body['providers']))
        self.assertEqual({'providers', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertIsInstance(body['pagination']['lastKey'], str)
        # Check we're actually sorted
        dates_of_update = [provider['dateOfUpdate'] for provider in body['providers']]
        self.assertListEqual(sorted(dates_of_update), dates_of_update)

    def test_query_providers_family_name_sorting(self):
        from handlers.providers import query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        self._generate_providers(home='ne', privilege='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {'sorting': {'key': 'familyName'}, 'query': {'jurisdiction': 'oh'}, 'pagination': {'pageSize': 10}},
        )

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(10, len(body['providers']))
        self.assertEqual({'providers', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertEqual({'key': 'familyName', 'direction': 'ascending'}, body['sorting'])
        self.assertIsInstance(body['pagination']['lastKey'], str)
        # Check we're actually sorted
        family_names = [provider['familyName'] for provider in body['providers']]
        self.assertListEqual(sorted(family_names, key=quote), family_names)

    def test_query_providers_by_family_name(self):
        from handlers.providers import query_providers

        # 10 providers, licenses in oh, and privileges in ne, including a Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            privilege='ne',
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {
                'sorting': {'key': 'familyName'},
                'query': {'jurisdiction': 'oh', 'familyName': 'Testerly'},
                'pagination': {'pageSize': 10},
            },
        )

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(2, len(body['providers']))

    def test_query_providers_given_name_only_not_allowed(self):
        from handlers.providers import query_providers

        # 10 providers, licenses in oh, and privileges in ne, including a Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            privilege='ne',
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {
                'sorting': {'key': 'familyName'},
                'query': {'jurisdiction': 'oh', 'givenName': 'Tess'},
                'pagination': {'pageSize': 10},
            },
        )

        resp = query_providers(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_query_providers_default_sorting(self):
        """If sorting is not specified, familyName is default"""
        from handlers.providers import query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        self._generate_providers(home='ne', privilege='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps({'query': {}})

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(20, len(body['providers']))
        self.assertEqual({'providers', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertEqual({'key': 'familyName', 'direction': 'ascending'}, body['sorting'])
        self.assertIsNone(body['pagination']['lastKey'])
        # Check we're actually sorted
        family_names = [provider['familyName'] for provider in body['providers']]
        self.assertListEqual(sorted(family_names, key=quote), family_names)

    def test_query_providers_invalid_sorting(self):
        from handlers.providers import query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        self._generate_providers(home='ne', privilege='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps({'query': {'jurisdiction': 'oh'}, 'sorting': {'key': 'invalid'}})

        resp = query_providers(event, self.mock_context)

        # Should reject the query, with 400
        self.assertEqual(400, resp['statusCode'])


@mock_aws
class TestGetProvider(TstFunction):
    def test_get_provider(self):
        """Provider detail response"""
        self._load_provider_data()

        from handlers.providers import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'
        event['pathParameters'] = {'compact': 'aslp', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        resp = get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])
        self.assertEqual(expected_provider, provider_data)

    def test_get_provider_wrong_compact(self):
        """Provider detail response"""
        self._load_provider_data()

        from handlers.providers import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'
        event['pathParameters'] = {'compact': 'octp', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = get_provider(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])

    def test_get_provider_missing_provider_id(self):
        from handlers.providers import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'
        # providerId _should_ be included in these pathParameters. We're leaving it out for this test.
        event['pathParameters'] = {'compact': 'aslp'}
        event['queryStringParameters'] = None

        resp = get_provider(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
