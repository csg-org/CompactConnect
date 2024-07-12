import json

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestProviders(TstFunction):
    def test_query_one_ssn(self):
        # Pre-load our license into the db
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema

        with open('tests/resources/api/license-post.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        with open('tests/resources/dynamo/license.json', 'r') as f:
            provider_id = json.load(f)['providerId']

        self._table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=LicenseRecordSchema().dump({
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'co',
                **license_data
            })
        )

        # Run the API query
        from handlers.providers import query_providers

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'ssn': '123-12-1234'
        })

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('tests/resources/api/license-post.json', 'r') as f:
            expected_license = json.load(f)

        body = json.loads(resp['body'])
        # Drop generated fields
        for o in body['items']:
            del o['dateOfUpdate']
            del o['birthMonthDay']
        self.assertEqual(
            {
                'items': [
                    {
                        'providerId': provider_id,
                        'compact': 'aslp',
                        'jurisdiction': 'co',
                        'type': 'license-home',
                        **expected_license
                    }
                ]
            },
            body
        )

    def test_query_one_provider(self):
        # Pre-load our license into the db
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema

        with open('tests/resources/api/license-post.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        with open('tests/resources/dynamo/license.json', 'r') as f:
            provider_id = json.load(f)['providerId']

        self._table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=LicenseRecordSchema().dump({
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'co',
                **license_data
            })
        )

        # Run the API query
        from handlers.providers import query_providers

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'providerId': provider_id
        })

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('tests/resources/api/license-post.json', 'r') as f:
            expected_license = json.load(f)

        body = json.loads(resp['body'])
        # Drop generated fields
        for o in body['items']:
            del o['dateOfUpdate']
            del o['birthMonthDay']
        self.assertEqual(
            {
                'items': [
                    {
                        'providerId': provider_id,
                        'compact': 'aslp',
                        'jurisdiction': 'co',
                        'type': 'license-home',
                        **expected_license
                    }
                ]
            },
            body
        )

    def test_query_providers_updated(self):
        from handlers.providers import query_providers

        # 100 licenses homed in co with privileges in fl
        self._generate_licensees('co', 'al', 9999)
        # 100 licenses homed in fl with privileges in co
        self._generate_licensees('al', 'co', 9899)

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'sorting': {
                'key': 'dateOfUpdate'
            },
            'compact': 'aslp',
            'jurisdiction': 'co'
        })

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(100, len(body['items']))
        self.assertEqual({'items', 'lastKey'}, body.keys())

    def test_query_providers_family_name(self):
        from handlers.providers import query_providers

        # 100 licenses homed in co with privileges in fl
        self._generate_licensees('co', 'al', 9999)
        # 100 licenses homed in fl with privileges in co
        self._generate_licensees('al', 'co', 9899)

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'sorting': {
                'key': 'familyName'
            },
            'compact': 'aslp',
            'jurisdiction': 'co'
        })

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(100, len(body['items']))
        self.assertEqual({'items', 'lastKey'}, body.keys())

    def test_query_providers_missing_sorting(self):
        from handlers.providers import query_providers

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'compact': 'aslp',
            'jurisdiction': 'co'
        })

        resp = query_providers(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertTrue(
            json.loads(resp['body'])['message'].startswith("'sorting' must be specified")
        )

    def test_query_providers_invalid_sorting(self):
        from handlers.providers import query_providers

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'sorting': {
                'key': 'invalid'
            },
            'compact': 'aslp',
            'jurisdiction': 'co'
        })

        resp = query_providers(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {'message': "Invalid sort key: 'invalid'"},
            json.loads(resp['body'])
        )

    def test_get_provider(self):
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
        from handlers.providers import get_provider

        with open('tests/resources/api/license-post.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        with open('tests/resources/dynamo/license.json', 'r') as f:
            provider_id = json.load(f)['providerId']

        self._table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=LicenseRecordSchema().dump({
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'co',
                **license_data
            })
        )

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['queryStringParameters'] = {
            'providerId': provider_id
        }

        with open('tests/resources/api/license-response.json', 'r') as f:
            expected_license = json.load(f)

        resp = get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        license_data = json.loads(resp['body'])['items'][0]

        # Deleting a dynamic field that won't match canned data
        del expected_license['dateOfUpdate']
        del license_data['dateOfUpdate']

        self.assertEqual(expected_license, license_data)

    def test_get_provider_missing_provider_id(self):
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema
        from handlers.providers import get_provider

        with open('tests/resources/api/license-post.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        with open('tests/resources/dynamo/license.json', 'r') as f:
            provider_id = json.load(f)['providerId']

        self._table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=LicenseRecordSchema().dump({
                'providerId': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'co',
                **license_data
            })
        )

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['queryStringParameters'] = None

        resp = get_provider(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
