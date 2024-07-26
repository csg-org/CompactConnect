import json

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestProviders(TstFunction):
    def test_query_one_ssn(self):
        # Pre-load our license into the db
        with open('tests/resources/dynamo/license.json', 'r') as f:
            license_data = json.load(f)

        self._table.put_item(Item=license_data)

        # Run the API query
        from handlers.providers import query_providers

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'query': {
                'ssn': '123-12-1234'
            }
        })

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('tests/resources/api/license-response.json', 'r') as f:
            expected_license = json.load(f)

        body = json.loads(resp['body'])

        self.assertEqual(
            {
                'items': [expected_license],
                'pagination': {
                    'pageSize': 100,
                    'lastKey': None,
                    'prevLastKey': None
                },
                'query': {
                    'ssn': '123-12-1234'
                }
            },
            body
        )

    def test_query_one_provider(self):
        # Pre-load our license into the db
        with open('tests/resources/dynamo/license.json', 'r') as f:
            license_data = json.load(f)
        provider_id = license_data['providerId']

        self._table.put_item(Item=license_data)

        # Run the API query
        from handlers.providers import query_providers

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'query': {
                'providerId': provider_id
            }
        })

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('tests/resources/api/license-response.json', 'r') as f:
            expected_license = json.load(f)

        body = json.loads(resp['body'])
        self.assertEqual(
            {
                'items': [expected_license],
                'pagination': {
                    'pageSize': 100,
                    'lastKey': None,
                    'prevLastKey': None
                },
                'query': {
                    'providerId': provider_id
                }
            },
            body
        )

    def test_query_providers_updated(self):
        from handlers.providers import query_providers

        # 100 licenses homed in co with privileges in al
        self._generate_licensees('co', 'al', 9999)
        # 100 licenses homed in al with privileges in co
        self._generate_licensees('al', 'co', 9899)

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'sorting': {
                'key': 'dateOfUpdate'
            },
            'query': {
                'compact': 'aslp',
                'jurisdiction': 'co'
            }
        })

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(100, len(body['items']))
        self.assertEqual({'items', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertIsInstance(body['pagination']['lastKey'], str)
        # Check we're actually sorted
        last_date_of_update = body['items'][0]['dateOfUpdate']
        for item in body['items'][1:]:
            self.assertGreaterEqual(item['dateOfUpdate'], last_date_of_update)

    def test_query_providers_family_name(self):
        from handlers.providers import query_providers

        # 100 licenses homed in co with privileges in al
        self._generate_licensees('co', 'al', 9999)
        # 100 licenses homed in al with privileges in co
        self._generate_licensees('al', 'co', 9899)

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'sorting': {
                'key': 'familyName'
            },
            'query': {
                'compact': 'aslp',
                'jurisdiction': 'co'
            }
        })

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(100, len(body['items']))
        self.assertEqual({'items', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertIsInstance(body['pagination']['lastKey'], str)
        # Check we're actually sorted
        last_family_name = body['items'][0]['familyName']
        for item in body['items'][1:]:
            self.assertGreaterEqual(item['familyName'], last_family_name)

    def test_query_providers_default_sorting(self):
        # 100 licenses homed in co with privileges in al
        self._generate_licensees('co', 'al', 9999)
        # 100 licenses homed in al with privileges in co
        self._generate_licensees('al', 'co', 9899)

        from handlers.providers import query_providers

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'query': {
                'compact': 'aslp',
                'jurisdiction': 'co'
            }
        })

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        body = json.loads(resp['body'])
        # Should default to familyName
        self.assertEqual(
            {
                'key': 'familyName',
                'direction': 'ascending'
            },
            body['sorting']
        )
        # Check we're actually sorted
        last_family_name = body['items'][0]['familyName']
        for item in body['items'][1:]:
            self.assertGreaterEqual(item['familyName'], last_family_name)

    def test_query_providers_invalid_sorting(self):
        from handlers.providers import query_providers

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'sorting': {
                'key': 'invalid'
            },
            'query': {
                'compact': 'aslp',
                'jurisdiction': 'co'
            }
        })

        resp = query_providers(event, self.mock_context)

        # Should reject the query, with 400
        self.assertEqual(400, resp['statusCode'])

    def test_get_provider(self):
        # Pre-load our license into the db
        with open('tests/resources/dynamo/license.json', 'r') as f:
            license_data = json.load(f)
        provider_id = license_data['providerId']

        self._table.put_item(Item=license_data)

        from handlers.providers import get_provider

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {
            'providerId': provider_id
        }
        event['queryStringParameters'] = {}

        with open('tests/resources/api/license-response.json', 'r') as f:
            expected_license = json.load(f)

        resp = get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        license_data = json.loads(resp['body'])['items'][0]

        self.assertEqual(expected_license, license_data)

    def test_get_provider_missing_provider_id(self):
        # Pre-load our license into the db
        with open('tests/resources/dynamo/license.json', 'r') as f:
            license_data = json.load(f)

        self._table.put_item(Item=license_data)

        from handlers.providers import get_provider

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['queryStringParameters'] = None

        resp = get_provider(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
