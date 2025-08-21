# ruff: noqa: ARG002 unused-argument
import json
from datetime import datetime
from unittest.mock import patch

from cc_common.exceptions import CCInternalException

from tests import TstLambdas


class TestPostLicenses(TstLambdas):
    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.licenses.config', autospec=False)
    @patch('handlers.licenses.send_licenses_to_preprocessing_queue')
    @patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction')
    def test_post_licenses(self, mock_get_configured_keys, mock_send_licenses_to_preprocessing_queue, mock_config):
        from handlers.licenses import post_licenses

        mock_config.current_standard_datetime = datetime.fromisoformat('2024-11-08T23:59:59+00:00')
        # this method returns any license numbers that failed, so we return an empty list for this test
        mock_send_licenses_to_preprocessing_queue.return_value = []
        # Mock HMAC authentication to return no configured keys (allows request to proceed without HMAC)
        mock_get_configured_keys.return_value = {}

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has scopes for oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/aslp.write'

        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}

        with open('../common/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual({'message': 'OK'}, json.loads(resp['body']))

        # get expected sqs body from common resource file
        with open('../common/tests/resources/ingest/preprocessor-sqs-message.json') as f:
            expected_sqs_body = json.load(f)
            # set the event time to the mock time
            expected_sqs_body['eventTime'] = '2024-11-08T23:59:59+00:00'

        # Collect events put for inspection
        # There should be one successful ingest event
        license_data_records = mock_send_licenses_to_preprocessing_queue.call_args.kwargs['licenses_data']
        # add the event time to the record, which is performed by the common code
        license_data_records[0]['eventTime'] = mock_send_licenses_to_preprocessing_queue.call_args.kwargs['event_time']
        self.assertEqual(1, len(license_data_records))
        self.assertEqual(expected_sqs_body, license_data_records[0])

    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.licenses.config', autospec=False)
    @patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction')
    def test_cross_compact(self, mock_get_configured_keys, mock_config):
        from handlers.licenses import post_licenses

        # Mock HMAC authentication to return no configured keys (allows request to proceed without HMAC)
        mock_get_configured_keys.return_value = {}

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has scopes for aslp, not octp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/aslp.write'

        event['pathParameters'] = {'compact': 'octp', 'jurisdiction': 'oh'}

        with open('../common/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])

    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.licenses.config', autospec=False)
    @patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction')
    def test_wrong_jurisdiction(self, mock_get_configured_keys, mock_config):  # noqa: ARG001 unused-argument
        from handlers.licenses import post_licenses

        # Mock HMAC authentication to return no configured keys (allows request to proceed without HMAC)
        mock_get_configured_keys.return_value = {}

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has scopes for oh, not ne
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/aslp.write'

        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'ne'}

        with open('../common/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])

    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.licenses.config', autospec=False)
    @patch('handlers.licenses.send_licenses_to_preprocessing_queue')
    @patch('cc_common.hmac_auth._get_configured_keys_for_jurisdiction')
    def test_event_error(self, mock_get_configured_keys, mock_send_licenses_to_preprocessing_queue, mock_config):
        """If we have trouble publishing our events to AWS EventBridge, we should
        return a 500 (raise a CCInternalException).
        """
        from handlers.licenses import post_licenses

        mock_config.current_standard_datetime = datetime.fromisoformat('2024-11-08T23:59:59+00:00')
        # this method returns any license numbers that failed, so we return one here
        mock_send_licenses_to_preprocessing_queue.return_value = ['mock-license-number']
        # Mock HMAC authentication to return no configured keys (allows request to proceed without HMAC)
        mock_get_configured_keys.return_value = {}

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has scopes for oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email oh/aslp.write'

        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}

        with open('../common/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        with self.assertRaises(CCInternalException):
            post_licenses(event, self.mock_context)
