import json

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestIngest(TstFunction):
    def test_new_provider_ingest(self):
        from handlers.ingest import ingest_license_message
        from handlers.providers import query_providers

        with open('tests/resources/ingest/message.json', 'r') as f:
            message = f.read()

        event = {
            'Records': [
                {
                    'messageId': '123',
                    'body': message
                }
            ]
        }

        resp = ingest_license_message(event, self.mock_context)  # pylint: disable=too-many-function-args

        self.assertEqual(
            {'batchItemFailures': []},
            resp
        )

        # To test full internal consistency, we'll also pull this new license record out
        # via the API to make sure it shows up as expected.
        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {'compact': 'aslp'}
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/read'
        event['body'] = json.dumps({
            'query': {
                'ssn': '123-12-1234'
            }
        })
        resp = query_providers(event, self.mock_context)
        self.assertEqual(resp['statusCode'], 200)

        with open('tests/resources/api/provider-response.json', 'r') as f:
            expected_provider = json.load(f)
        # The canned response resource assumes that the provider will be given a privilege in NE. We didn't do that,
        # so we'll reset the privilege array.
        expected_provider['privilegeJurisdictions'] = []

        provider_data = json.loads(resp['body'])['providers'][0]
        # Removing dynamic fields from comparison
        del expected_provider['providerId']
        del provider_data['providerId']
        del expected_provider['dateOfUpdate']
        del provider_data['dateOfUpdate']

        self.assertEqual(
            expected_provider,
            provider_data
        )

    def test_existing_provider_ingest(self):
        from handlers.ingest import ingest_license_message
        from handlers.providers import query_providers

        # Pre-load the SSN-providerId association
        with open('tests/resources/dynamo/provider-ssn.json', 'r') as f:
            provider_ssn_record = json.load(f)
        provider_id = provider_ssn_record['providerId']

        self._table.put_item(Item=provider_ssn_record)

        with open('tests/resources/ingest/message.json', 'r') as f:
            message = f.read()

        event = {
            'Records': [
                {
                    'messageId': '123',
                    'body': message
                }
            ]
        }

        resp = ingest_license_message(event, self.mock_context)  # pylint: disable=too-many-function-args

        self.assertEqual(
            {'batchItemFailures': []},
            resp
        )

        # To test full internal consistency, we'll also pull this new license record out
        # via the API to make sure it shows up as expected.
        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {'compact': 'aslp'}
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/read'
        event['body'] = json.dumps({
            'query': {
                'providerId': provider_id
            }
        })
        resp = query_providers(event, self.mock_context)
        self.assertEqual(resp['statusCode'], 200)

        with open('tests/resources/api/provider-response.json', 'r') as f:
            expected_provider = json.load(f)
        # The canned response resource assumes that the provider will be given a privilege in NE. We didn't do that,
        # so we'll reset the privilege array.
        expected_provider['privilegeJurisdictions'] = []

        provider_data = json.loads(resp['body'])['providers'][0]
        # Removing dynamic fields from comparison
        del expected_provider['providerId']
        del provider_data['providerId']
        del expected_provider['dateOfUpdate']
        del provider_data['dateOfUpdate']

        self.assertEqual(
            expected_provider,
            provider_data
        )
