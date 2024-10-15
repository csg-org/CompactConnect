import json
from unittest.mock import patch

from exceptions import CCInternalException

from tests import TstLambdas


class TestPostLicenses(TstLambdas):
    @patch('handlers.licenses.config', autospec=True)
    def test_post_licenses(self, mock_config):
        from handlers.licenses import post_licenses

        mock_config.events_client.put_events.return_value = {
            'FailedEntryCount': 0,
            'Entries': [{'EventId': '123'}]
        }

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'al'
        }

        with open('tests/resources/api/license-post.json', 'r') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual({'message': 'OK'}, json.loads(resp['body']))

        # Collect events put for inspection
        # There should be one successful ingest event
        entries = [
            entry
            for call in mock_config.events_client.put_events.call_args_list
            for entry in call.kwargs['Entries']
        ]
        self.assertEqual(1, len(entries))
        self.assertEqual('license-ingest', entries[0]['DetailType'])

    @patch('handlers.licenses.config', autospec=True)
    def test_not_authorized(self, mock_config):  # pylint: disable=unused-argument
        from handlers.licenses import post_licenses

        # The sample event has scopes for aslp/al not aslp/co
        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'co'
        }

        with open('tests/resources/api/license-post.json', 'r') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])

    @patch('handlers.licenses.config', autospec=True)
    def test_event_error(self, mock_config):
        """
        If we have trouble publishing our events to AWS EventBridge, we should
        return a 500 (raise a CCInternalException).
        """
        from handlers.licenses import post_licenses

        mock_config.events_client.put_events.return_value = {
            'FailedEntryCount': 1,
            'Entries': [
                {
                    'EventId': '123',
                    'ErrorCode': 'SomethingBad',
                    'ErrorMessage': 'There is something wrong with this event'
                }
            ]
        }

        # The sample event has scopes for aslp/al not aslp/co
        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'al'
        }

        with open('tests/resources/api/license-post.json', 'r') as f:
            event['body'] = json.dumps([json.load(f)])

        with self.assertRaises(CCInternalException):
            post_licenses(event, self.mock_context)
