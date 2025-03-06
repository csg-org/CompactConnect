import json
from datetime import datetime
from unittest.mock import patch

from moto import mock_aws

from .. import TstFunction


@mock_aws
class TestLicenses(TstFunction):
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-12-04T08:08:08+00:00'))
    def test_post_licenses_puts_expected_messages_on_the_queue(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral oh/aslp.write'
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            event['body'] = json.dumps([json.load(f)])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        # assert that the message was sent to the preprocessing queue
        queue_messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(1, len(queue_messages))

        expected_message = json.loads(event['body'])[0]
        # add the compact, jurisdiction, and eventTime to the expected message
        expected_message['compact'] = 'aslp'
        expected_message['jurisdiction'] = 'oh'
        expected_message['eventTime'] = '2024-12-04T08:08:08+00:00'
        self.assertEqual(expected_message, json.loads(queue_messages[0].body))

    def test_post_licenses_invalid_license_type(self):
        from handlers.licenses import post_licenses

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for aslp/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral oh/aslp.write'
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}
        with open('../common/tests/resources/api/license-post.json') as f:
            license_data = json.load(f)
        license_data['licenseType'] = 'occupational therapist'
        event['body'] = json.dumps([license_data])

        resp = post_licenses(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])
