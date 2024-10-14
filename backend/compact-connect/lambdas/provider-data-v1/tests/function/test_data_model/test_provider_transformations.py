import json
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestTransformations(TstFunction):
    # Yes, this is an excessively long method. We're going with it for sake of a single illustrative test.
    def test_transformations(self):  # pylint: disable=too-many-statements,too-many-locals
        """
        Provider data undergoes several transformations from when a license is first posted, stored into the database,
        then returned via the API. We will specifically test that chain, end to end, to make sure the transformations
        all happen as expected.
        """
        # Before we get started, we'll pre-set the SSN/providerId association we expect
        with open('tests/resources/dynamo/provider-ssn.json', 'r') as f:
            provider_ssn = json.load(f)

        self._provider_table.put_item(
            Item=provider_ssn
        )
        expected_provider_id = provider_ssn['providerId']

        # license data as it comes in from a board, in this case, as POSTed through the API
        with open('tests/resources/api/license-post.json', 'r') as f:
            license_post = json.load(f)
        license_ssn = license_post['ssn']

        # The API Gateway event, as it is presented to the API lambda
        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        # Pack an array of one license into the request body
        event['body'] = json.dumps([license_post])

        # Compact and jurisdiction are provided via path parameters
        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'oh'
        }
        # Authorize ourselves to write the license
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/write aslp/oh.write'

        from handlers.licenses import post_licenses

        # Mock EventBatchWriter so we can intercept the EventBridge event for later
        with patch('handlers.licenses.EventBatchWriter', autospec=True) as mock_event_batch_writer:
            mock_event_batch_writer.return_value.__enter__.return_value.failed_entry_count = 0
            mock_event_batch_writer.return_value.__enter__.return_value.failed_entries = []

            # POST the license via the API
            post_licenses(event, self.mock_context)

            # Capture the event the API POST will produce
            event_bridge_event = json.loads(
                mock_event_batch_writer.return_value.__enter__.return_value
                .put_event.call_args.kwargs['Entry']['Detail']
            )

        # A sample SQS message from EventBridge
        with open('tests/resources/ingest/message.json', 'r') as f:
            message = json.load(f)

        # Pack our license-ingest event into the sample message
        message['detail'] = event_bridge_event
        event = {
            'Records': [
                {
                    'messageId': '123',
                    'body': json.dumps(message)
                }
            ]
        }

        from handlers.ingest import ingest_license_message

        # This should fully ingest the license, which will result in it being written to the DB
        ingest_license_message(event, self.mock_context)  # pylint: disable=too-many-function-args

        from data_model.client import DataClient

        # We'll use the data client to get the resulting provider id
        client = DataClient(self.config)
        provider_id = client.get_provider_id(  # pylint: disable=missing-kwoa,unexpected-keyword-arg
            compact='aslp',
            ssn=license_ssn
        )
        self.assertEqual(expected_provider_id, provider_id)

        # Add a privilege to practice in Nebraska
        client.create_privilege(compact='aslp', jurisdiction='ne', provider_id=provider_id)

        # Get the provider straight from the table, to inspect them
        resp = self._provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'aslp#PROVIDER#{provider_id}')
            & Key('sk').begins_with('aslp#PROVIDER')
        )
        # One record for reach of: provider, license, privilege
        self.assertEqual(3, len(resp['Items']))
        records = {
            item['type']: item for item in resp['Items']
        }

        # Expected representation of each record in the database
        with open('tests/resources/dynamo/provider.json', 'r') as f:
            expected_provider = json.load(f)
        # Convert this to the data type expected from DynamoDB
        expected_provider['privilegeJurisdictions'] = set(expected_provider['privilegeJurisdictions'])

        with open('tests/resources/dynamo/license.json', 'r') as f:
            expected_license = json.load(f)
        with open('tests/resources/dynamo/privilege.json', 'r') as f:
            expected_privilege = json.load(f)

        # Force the provider id to match
        for record in [expected_provider, expected_license, expected_privilege, *records.values()]:
            # Drop dynamic field
            del record['dateOfUpdate']
        # These fields will be dynamic, so we'll remove them from comparison
        del expected_provider['providerDateOfUpdate']
        del records['provider']['providerDateOfUpdate']
        del expected_privilege['dateOfIssuance']
        del records['privilege']['dateOfIssuance']

        # Make sure each is represented the way we expect, in the db
        self.assertEqual(expected_provider, records['provider'])
        self.assertEqual(expected_license, records['license'])
        self.assertEqual(expected_privilege, records['privilege'])

        from handlers.providers import get_provider

        # Get a fresh API Gateway event
        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {
            'compact': 'aslp',
            'providerId': provider_id
        }
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/read'

        resp = get_provider(event, self.mock_context)

        # If we get a 200, our full ingest chain was successful
        self.assertEqual(200, resp['statusCode'])

        provider_data = json.loads(resp['body'])

        # Expected representation of our provider coming _out_ via the API
        with open('tests/resources/api/provider-detail-response.json', 'r') as f:
            expected_provider = json.load(f)

        # Force the provider id to match
        expected_provider['providerId'] = provider_id

        # Drop dynamic fields from comparison
        del provider_data['dateOfUpdate']
        del provider_data['licenses'][0]['dateOfUpdate']
        del provider_data['privileges'][0]['dateOfUpdate']
        del provider_data['privileges'][0]['dateOfIssuance']
        del expected_provider['dateOfUpdate']
        del expected_provider['licenses'][0]['dateOfUpdate']
        del expected_provider['privileges'][0]['dateOfUpdate']
        del expected_provider['privileges'][0]['dateOfIssuance']

        # Phew! We've loaded the data all the way in via the ingest chain and back out via the API!
        self.assertEqual(expected_provider, provider_data)
