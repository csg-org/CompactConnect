# ruff: noqa: ARG002 unused-argument
import json
from unittest.mock import patch

from cc_common.exceptions import CCInternalException

from tests import TstLambdas


class TestPostLicenses(TstLambdas):
    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.licenses.config', autospec=False)
    def test_post_licenses(self, mock_config):
        from handlers.licenses import post_licenses

        mock_config.events_client.put_events.return_value = {'FailedEntryCount': 0, 'Entries': [{'EventId': '123'}]}

        with open('../common-python/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has scopes for oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/write aslp/oh.write'

        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}

        with open('../common-python/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual({'message': 'OK'}, json.loads(resp['body']))

        # Collect events put for inspection
        # There should be one successful ingest event
        entries = [
            entry for call in mock_config.events_client.put_events.call_args_list for entry in call.kwargs['Entries']
        ]
        self.assertEqual(1, len(entries))
        self.assertEqual('license.ingest', entries[0]['DetailType'])

    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.licenses.config', autospec=False)
    def test_cross_compact(self, mock_config):
        from handlers.licenses import post_licenses

        with open('../common-python/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has scopes for aslp, not octp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/write aslp/oh.write'

        event['pathParameters'] = {'compact': 'octp', 'jurisdiction': 'oh'}

        with open('../common-python/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])

    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.licenses.config', autospec=False)
    def test_wrong_jurisdiction(self, mock_config):  # noqa: ARG001 unused-argument
        from handlers.licenses import post_licenses

        with open('../common-python/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has scopes for oh, not ne
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/write aslp/oh.write'

        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'ne'}

        with open('../common-python/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])

    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.licenses.config', autospec=False)
    def test_event_error(self, mock_config):
        """If we have trouble publishing our events to AWS EventBridge, we should
        return a 500 (raise a CCInternalException).
        """
        from handlers.licenses import post_licenses

        mock_config.events_client.put_events.return_value = {
            'FailedEntryCount': 1,
            'Entries': [
                {
                    'EventId': '123',
                    'ErrorCode': 'SomethingBad',
                    'ErrorMessage': 'There is something wrong with this event',
                },
            ],
        }

        with open('../common-python/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has scopes for oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/write aslp/oh.write'

        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}

        with open('../common-python/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        with self.assertRaises(CCInternalException):
            post_licenses(event, self.mock_context)
