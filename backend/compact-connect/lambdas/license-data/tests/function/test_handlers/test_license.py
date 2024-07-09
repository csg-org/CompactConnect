import json

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestLicense(TstFunction):
    def test_query_one_ssn(self):
        # Pre-load our license into the db
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema

        with open('tests/resources/api/license.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        with open('tests/resources/dynamo/license.json', 'r') as f:
            provider_id = json.load(f)['provider_id']

        self._table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=LicenseRecordSchema().dump({
                'provider_id': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'co',
                **license_data
            })
        )

        # Run the API query
        from handlers.license import query_licenses

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'ssn': '123-12-1234'
        })

        resp = query_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('tests/resources/api/license.json', 'r') as f:
            expected_license = json.load(f)

        body = json.loads(resp['body'])
        # Drop generated fields
        for o in body['items']:
            del o['date_of_update']
            del o['birth_month_day']
        self.assertEqual(
            {
                'items': [
                    {
                        'provider_id': provider_id,
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

        with open('tests/resources/api/license.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        with open('tests/resources/dynamo/license.json', 'r') as f:
            provider_id = json.load(f)['provider_id']

        self._table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=LicenseRecordSchema().dump({
                'provider_id': provider_id,
                'compact': 'aslp',
                'jurisdiction': 'co',
                **license_data
            })
        )

        # Run the API query
        from handlers.license import query_licenses

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'provider_id': provider_id
        })

        resp = query_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('tests/resources/api/license.json', 'r') as f:
            expected_license = json.load(f)

        body = json.loads(resp['body'])
        # Drop generated fields
        for o in body['items']:
            del o['date_of_update']
            del o['birth_month_day']
        self.assertEqual(
            {
                'items': [
                    {
                        'provider_id': provider_id,
                        'compact': 'aslp',
                        'jurisdiction': 'co',
                        'type': 'license-home',
                        **expected_license
                    }
                ]
            },
            body
        )

    def test_query_licenses_updated(self):
        from handlers.license import query_licenses

        # 100 licenses homed in co with privileges in fl
        self._generate_licensees('co', 'al', 9999)
        # 100 licenses homed in fl with privileges in co
        self._generate_licensees('al', 'co', 9899)

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'sorting': {
                'key': 'date_of_update'
            },
            'compact': 'aslp',
            'jurisdiction': 'co'
        })

        resp = query_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(100, len(body['items']))
        self.assertEqual({'items', 'lastKey'}, body.keys())

    def test_query_licenses_family_name(self):
        from handlers.license import query_licenses

        # 100 licenses homed in co with privileges in fl
        self._generate_licensees('co', 'al', 9999)
        # 100 licenses homed in fl with privileges in co
        self._generate_licensees('al', 'co', 9899)

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'sorting': {
                'key': 'family_name'
            },
            'compact': 'aslp',
            'jurisdiction': 'co'
        })

        resp = query_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(100, len(body['items']))
        self.assertEqual({'items', 'lastKey'}, body.keys())

    def test_query_licenses_missing_sorting(self):
        from handlers.license import query_licenses

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'compact': 'aslp',
            'jurisdiction': 'co'
        })

        resp = query_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertTrue(
            json.loads(resp['body'])['message'].startswith("'sorting' must be specified")
        )

    def test_query_licenses_invalid_sorting(self):
        from handlers.license import query_licenses

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

        resp = query_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {'message': "Invalid sort key: 'invalid'"},
            json.loads(resp['body'])
        )
