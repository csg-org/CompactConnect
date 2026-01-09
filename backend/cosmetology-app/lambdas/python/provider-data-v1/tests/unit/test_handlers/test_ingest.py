import json
from unittest.mock import patch

from tests import TstLambdas


class TestIngest(TstLambdas):
    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.ingest.config', autospec=False)
    def test_preprocess_license_ingest_removes_ssn_from_record(self, mock_config):
        from handlers.ingest import preprocess_license_ingest

        test_ssn = '123-12-1234'
        test_provider_id = 'test_id'
        test_event_bus_name = 'test-event-bus'

        mock_config.event_bus_name = test_event_bus_name
        # this method returns any license numbers that failed, so we return an empty list for this test
        mock_config.data_client.get_or_create_provider_id.return_value = test_provider_id

        with open('../common/tests/resources/ingest/preprocessor-sqs-message.json') as f:
            message = json.load(f)
            # set fixed ssn here to ensure we are checking the expected value
            message['ssn'] = test_ssn

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = preprocess_license_ingest(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        expected_event_bus_message = json.loads(json.dumps(message))
        expected_event_bus_message.pop('ssn')
        expected_event_bus_message['providerId'] = test_provider_id
        expected_event_bus_message['ssnLastFour'] = '1234'

        # Because this was a failure due to invalid data, we will fire a failure event
        mock_config.events_client.put_events.assert_called_once_with(
            Entries=[
                {
                    'Source': 'org.compactconnect.provider-data',
                    'DetailType': 'license.ingest',
                    'Detail': json.dumps(expected_event_bus_message),
                    'EventBusName': test_event_bus_name,
                }
            ]
        )
