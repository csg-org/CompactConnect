import json

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestIngest(TstFunction):
    def test_new_ingest(self):
        from handlers.ingest import process_license_message
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

        resp = process_license_message(event, self.mock_context)  # pylint: disable=too-many-function-args

        self.assertEqual(
            {'batchItemFailures': []},
            resp
        )

        # To test full internal consistency, we'll also pull this new license record out
        # via the API to make sure it shows up as expected.
        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['body'] = json.dumps({
            'ssn': '123-12-1234'
        })
        resp = query_providers(event, self.mock_context)
        self.assertEqual(resp['statusCode'], 200)

        with open('tests/resources/api/license-response.json', 'r') as f:
            expected_license = json.load(f)

        license_data = json.loads(resp['body'])['items'][0]
        # Removing dynamic fields from comparison
        del expected_license['providerId']
        del license_data['providerId']
        del expected_license['dateOfUpdate']
        del license_data['dateOfUpdate']

        self.assertEqual(
            expected_license,
            license_data
        )
