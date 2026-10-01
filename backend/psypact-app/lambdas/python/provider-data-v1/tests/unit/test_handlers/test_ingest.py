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

    def _run_preprocessor_with_previous_ssn(self, mock_config, *, ssn: str, previous_ssn: str) -> dict:
        """Run preprocess_license_ingest on a message carrying a previousSSN and return the published event detail."""
        from handlers.ingest import preprocess_license_ingest

        with open('../common/tests/resources/ingest/preprocessor-sqs-message.json') as f:
            message = json.load(f)
        message['ssn'] = ssn
        message['previousSSN'] = previous_ssn

        event = {'Records': [{'messageId': '123', 'body': json.dumps(message)}]}

        resp = preprocess_license_ingest(event, self.mock_context)
        self.assertEqual({'batchItemFailures': []}, resp)

        entries = mock_config.events_client.put_events.call_args.kwargs['Entries']
        self.assertEqual(1, len(entries))
        self.assertEqual('license.ingest', entries[0]['DetailType'])
        return json.loads(entries[0]['Detail'])

    @patch('handlers.ingest.config', autospec=False)
    def test_preprocess_license_ingest_forwards_previous_provider_id_and_never_the_ssns(self, mock_config):
        new_provider_id = 'new-provider-id'
        previous_provider_id = 'previous-provider-id'
        # the first call resolves the current ssn, the second call resolves the previous ssn
        mock_config.data_client.get_or_create_provider_id.side_effect = [new_provider_id, previous_provider_id]

        detail = self._run_preprocessor_with_previous_ssn(mock_config, ssn='123-12-1234', previous_ssn='123-12-9876')

        self.assertEqual(new_provider_id, detail['providerId'])
        self.assertEqual(previous_provider_id, detail['previousProviderId'])
        self.assertEqual('1234', detail['ssnLastFour'])
        # neither SSN may ever reach the event bus
        self.assertNotIn('ssn', detail)
        self.assertNotIn('previousSSN', detail)

    @patch('handlers.ingest.config', autospec=False)
    def test_preprocess_license_ingest_omits_previous_provider_id_when_it_resolves_to_same_provider(self, mock_config):
        # both SSNs resolve to the same provider id, so there is nothing to migrate
        mock_config.data_client.get_or_create_provider_id.side_effect = ['same-provider-id', 'same-provider-id']

        detail = self._run_preprocessor_with_previous_ssn(mock_config, ssn='123-12-1234', previous_ssn='123-12-9876')

        self.assertEqual('same-provider-id', detail['providerId'])
        self.assertNotIn('previousProviderId', detail)
        self.assertNotIn('ssn', detail)
        self.assertNotIn('previousSSN', detail)

    @patch('handlers.ingest.config', autospec=False)
    def test_preprocess_license_ingest_ignores_previous_ssn_equal_to_current_ssn(self, mock_config):
        mock_config.data_client.get_or_create_provider_id.return_value = 'provider-id'

        detail = self._run_preprocessor_with_previous_ssn(mock_config, ssn='123-12-1234', previous_ssn='123-12-1234')

        # only the current ssn should have been resolved; a matching previousSSN is a no-op
        mock_config.data_client.get_or_create_provider_id.assert_called_once_with(compact='aslp', ssn='123-12-1234')
        self.assertNotIn('previousProviderId', detail)
        self.assertNotIn('ssn', detail)
        self.assertNotIn('previousSSN', detail)
