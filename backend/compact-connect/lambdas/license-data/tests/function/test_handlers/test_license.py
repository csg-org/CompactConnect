import json

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestLicense(TstFunction):
    def test_get_license(self):
        # Pre-load our license into the db
        from data_model.schema.license import LicensePostSchema, LicenseRecordSchema

        with open('tests/resources/api/license.json', 'r') as f:
            license_data = LicensePostSchema().loads(f.read())

        self._table.put_item(
            # We'll use the schema/serializer to populate index fields for us
            Item=LicenseRecordSchema().dump({
                'compact': 'aslp',
                'jurisdiction': 'co',
                **license_data
            })
        )

        # Run the API query
        from handlers.license import query_one_license

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {}
        event['body'] = json.dumps({
            'ssn': '123-12-1234'
        })

        resp = query_one_license(event, self.mock_context)

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
                        'compact': 'aslp',
                        'jurisdiction': 'co',
                        'type': 'license-home',
                        **expected_license
                    }
                ]
            },
            body
        )

    def test_get_licenses_updated(self):
        from handlers.license import query_licenses_updated

        # 100 licenses homed in co with privileges in fl
        self._generate_licensees('co', 'al', 9999)
        # 100 licenses homed in fl with privileges in co
        self._generate_licensees('al', 'co', 9899)

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'co'
        }
        event['body'] = json.dumps({})

        resp = query_licenses_updated(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(100, len(body['items']))
        self.assertEqual({'items', 'lastKey'}, body.keys())

    def test_get_licenses_family_name(self):
        from handlers.license import query_licenses_family

        # 100 licenses homed in co with privileges in fl
        self._generate_licensees('co', 'al', 9999)
        # 100 licenses homed in fl with privileges in co
        self._generate_licensees('al', 'co', 9899)

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'co'
        }
        event['body'] = json.dumps({})

        resp = query_licenses_family(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(100, len(body['items']))
        self.assertEqual({'items', 'lastKey'}, body.keys())
