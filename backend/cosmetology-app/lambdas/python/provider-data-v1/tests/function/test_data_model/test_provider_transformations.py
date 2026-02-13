import json
from datetime import datetime
from unittest.mock import patch

from cc_common.data_model.update_tier_enum import UpdateTierEnum
from moto import mock_aws

from .. import TstFunction

MOCK_CURRENT_DATETIME_STRING = '2024-11-08T23:59:59+00:00'


@mock_aws
class TestTransformations(TstFunction):
    # Yes, this is an excessively long method. We're going with it for sake of a single illustrative test.
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_DATETIME_STRING))
    @patch('cc_common.config._Config.license_preprocessing_queue')
    def test_transformations(self, mock_license_preprocessing_queue):
        """Provider data undergoes several transformations from when a license is first posted, stored into the
        database, then returned via the API. We will specifically test that chain, end to end, to make sure the
        transformations all happen as expected.
        """
        # Before we get started, we'll pre-set the SSN/providerId association we expect
        with open('../common/tests/resources/dynamo/provider-ssn.json') as f:
            provider_ssn = json.load(f)

        self._ssn_table.put_item(Item=provider_ssn)
        expected_provider_id = provider_ssn['providerId']

        # license data as it comes in from a board, in this case, as POSTed through the API
        with open('../common/tests/resources/api/license-post.json') as f:
            license_post = json.load(f)
        license_ssn = license_post['ssn']

        # The API Gateway event, as it is presented to the API lambda
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # Pack an array of one license into the request body
        event['body'] = json.dumps([license_post])

        # Compact and jurisdiction are provided via path parameters
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}
        # Authorize ourselves to write the license
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/cosm.write'

        from handlers.licenses import post_licenses

        # POST the license via the API
        post_licenses(event, self.mock_context)

        # Capture the message sent to the preprocessing queue
        preprocessing_message = json.loads(
            mock_license_preprocessing_queue.send_messages.call_args.kwargs['Entries'][0]['MessageBody']
        )

        # Now we need to simulate the preprocessing step
        # Mock EventBatchWriter so we can intercept the EventBridge event
        with patch('handlers.ingest.config.events_client', autospec=True) as mock_event_client:
            from handlers.ingest import preprocess_license_ingest

            # Create an SQS event with our preprocessing message
            preprocess_event = {'Records': [{'messageId': '123', 'body': json.dumps(preprocessing_message)}]}

            # Run the preprocessing step
            preprocess_license_ingest(preprocess_event, self.mock_context)

            # Capture the event the preprocessor will produce for the event bus
            event_bridge_event = json.loads(mock_event_client.put_events.call_args.kwargs['Entries'][0]['Detail'])

        # A sample SQS message from EventBridge
        with open('../common/tests/resources/ingest/event-bridge-message.json') as f:
            message = json.load(f)

        # Pack our license.ingest event into the sample message
        message['detail'] = event_bridge_event
        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        from handlers.ingest import ingest_license_message

        # This should fully ingest the license, which will result in it being written to the DB
        ingest_license_message(event, self.mock_context)

        # We'll fetch the provider id from the ssn table
        provider_id = self._ssn_table.get_item(Key={'pk': f'cosm#SSN#{license_ssn}', 'sk': f'cosm#SSN#{license_ssn}'})[
            'Item'
        ]['providerId']
        self.assertEqual(expected_provider_id, provider_id)

        # Get the provider and all update records straight from the table, to inspect them
        provider_user_records = self.config.data_client.get_provider_user_records(
            compact='cosm', provider_id=provider_id, include_update_tier=UpdateTierEnum.TIER_THREE
        )

        # One record for each of: provider and license (no privileges in cosmetology model)
        self.assertEqual(2, len(provider_user_records.provider_records))
        records = {item['type']: item for item in provider_user_records.provider_records}

        # Expected representation of each record in the database
        with open('../common/tests/resources/dynamo/provider.json') as f:
            expected_provider = json.load(f)
            expected_provider['licenseStatus'] = 'active'
            expected_provider['compactEligibility'] = 'eligible'

        with open('../common/tests/resources/dynamo/license.json') as f:
            expected_license = json.load(f)
            # license should be active and compact eligible
            expected_license['licenseStatus'] = 'active'
            expected_license['compactEligibility'] = 'eligible'
            expected_license['firstUploadDate'] = MOCK_CURRENT_DATETIME_STRING
            expected_license['licenseUploadDateGSIPK'] = 'C#cosm#J#oh#D#2024-11'
            expected_license['licenseUploadDateGSISK'] = (
                'TIME#1731110399#LT#cos#PID#89a6377e-c3a5-40e5-bca5-317ec854c570'
            )

        # each record has a dynamic dateOfUpdate field that we'll remove for comparison
        for record in [expected_provider, expected_license, *records.values()]:
            del record['dateOfUpdate']
        del expected_provider['providerDateOfUpdate']
        del records['provider']['providerDateOfUpdate']

        # Make sure each is represented the way we expect, in the db
        self.assertEqual(expected_provider, records['provider'])
        self.assertEqual(expected_license, records['license'])

        from handlers.providers import get_provider

        # Get a fresh API Gateway event
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['pathParameters'] = {'compact': 'cosm', 'providerId': provider_id}
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral cosm/readPrivate'

        resp = get_provider(event, self.mock_context)

        # If we get a 200, our full ingest chain was successful
        self.assertEqual(200, resp['statusCode'])

        provider_data = json.loads(resp['body'])

        # Expected representation of our provider coming _out_ via the API
        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        # Force the provider id to match
        expected_provider['providerId'] = provider_id
        # privileges tied to active states
        expected_provider['privileges'] = []

        # Drop dynamic fields from comparison
        del provider_data['dateOfUpdate']
        del provider_data['licenses'][0]['dateOfUpdate']
        del expected_provider['dateOfUpdate']
        del expected_provider['licenses'][0]['dateOfUpdate']

        # Phew! We've loaded the data all the way in via the ingest chain and back out via the API!
        self.maxDiff = None
        self.assertEqual(expected_provider, provider_data)
