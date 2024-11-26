import json
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestTransformations(TstFunction):
    def test_transformations(self):
        """License data undergoes several transformations from when it is first posted, stored into the database,
        then returned via the API. We will specifically test that chain, end to end, to make sure the transformations
        all happen as expected.
        """
        # license data as it comes in from a board, in this case, as POSTed through the API
        with open('tests/resources/api/license-post.json') as f:
            license_post = json.load(f)
        license_ssn = license_post['ssn']

        # The API Gateway event, as it is presented to the API lambda
        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # Pack an array of one license into the request body
        event['body'] = json.dumps([license_post])

        # Compact and jurisdiction are provided via path parameters
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'co'}
        # Authorize ourselves to write an aslp/co license
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/co.write'

        from handlers.licenses import post_licenses

        # Mock EventBatchWriter so we can intercept the EventBridge event for later
        with patch('handlers.licenses.EventBatchWriter', autospec=True) as mock_event_batch_writer:
            mock_event_batch_writer.return_value.__enter__.return_value.failed_entry_count = 0
            mock_event_batch_writer.return_value.__enter__.return_value.failed_entries = []

            # POST the license via the API
            post_licenses(event, self.mock_context)

            # Capture the event the API POST will produce
            event_bridge_event = json.loads(
                mock_event_batch_writer.return_value.__enter__.return_value.put_event.call_args.kwargs['Entry'][
                    'Detail'
                ],
            )

        # A sample SQS message from EventBridge
        with open('tests/resources/ingest/message.json') as f:
            message = json.load(f)

        # Pack our license-ingest event into the sample message
        message['detail'] = event_bridge_event
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        from handlers.ingest import ingest_license_message

        # This should fully ingest the license, which will result in it being written to the DB
        ingest_license_message(event, self.mock_context)

        from data_model.client import DataClient

        # We'll use the data client to get the resulting provider id
        client = DataClient(self.config)
        provider_id = client.get_provider_id(ssn=license_ssn)

        # Get the license straight from the table, to inspect it
        resp = self._table.query(Select='ALL_ATTRIBUTES', KeyConditionExpression=Key('pk').eq(provider_id))
        self.assertEqual(1, len(resp['Items']))
        db_license = resp['Items'][0]

        # Expected representation of the license in the database
        with open('tests/resources/dynamo/license.json') as f:
            expected_license = json.load(f)

        # Force the provider id to match
        expected_license['pk'] = provider_id
        expected_license['providerId'] = provider_id
        expected_license['licenseHomeProviderId'] = provider_id

        # Drop dynamic fields from comparison
        del db_license['dateOfUpdate']
        del expected_license['dateOfUpdate']

        self.assertEqual(expected_license, db_license)

        from handlers.providers import get_provider

        # Get a fresh API Gateway event
        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        event['pathParameters'] = {'providerId': provider_id}

        resp = get_provider(event, self.mock_context)

        # If we get a 200, our full ingest chain was successful
        self.assertEqual(200, resp['statusCode'])

        license_data = json.loads(resp['body'])['items'][0]

        # Expected representation of our license coming _out_ via the API
        with open('tests/resources/api/license-response.json') as f:
            expected_license = json.load(f)

        # Force the provider id to match
        expected_license['providerId'] = provider_id

        # Drop dynamic fields from comparison
        del license_data['dateOfUpdate']
        del expected_license['dateOfUpdate']

        # Phew! We've loaded the data all the way in via the ingest chain and back out via the API!
        self.assertEqual(expected_license, license_data)
