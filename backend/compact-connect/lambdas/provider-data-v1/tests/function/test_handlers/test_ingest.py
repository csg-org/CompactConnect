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
        from handlers.providers import get_provider

        self._load_provider_data()
        with open('tests/resources/dynamo/provider-ssn.json', 'r') as f:
            provider_id = json.load(f)['providerId']

        with open('tests/resources/ingest/message.json', 'r') as f:
            message = json.load(f)
        # What happens if their license goes inactive?
        message['detail']['status'] = 'inactive'

        event = {
            'Records': [
                {
                    'messageId': '123',
                    'body': json.dumps(message)
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

        event['pathParameters'] = {'compact': 'aslp', 'providerId': provider_id}
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/read'
        resp = get_provider(event, self.mock_context)
        self.assertEqual(resp['statusCode'], 200)

        with open('tests/resources/api/provider-detail-response.json', 'r') as f:
            expected_provider = json.load(f)
        # The license and provider should immediately be inactive
        expected_provider['status'] = 'inactive'
        expected_provider['licenses'][0]['status'] = 'inactive'
        # NOTE: when we are supporting privilege applications officially, they should also be set inactive. That will
        # be captured in the relevant feature work - this is just to help us remember, since it's pretty important.
        # expected_provider['privileges'][0]['status'] = 'inactive'

        provider_data = json.loads(resp['body'])
        # Removing dynamic fields from comparison
        del expected_provider['providerId']
        del provider_data['providerId']
        del expected_provider['dateOfUpdate']
        del provider_data['dateOfUpdate']
        del expected_provider['licenses'][0]['dateOfUpdate']
        del provider_data['licenses'][0]['dateOfUpdate']

        self.assertEqual(
            expected_provider,
            provider_data
        )
