import json
from unittest.mock import Mock
from uuid import uuid4

from tests import TstLambdas


class TestSQSHandler(TstLambdas):
    def test_happy_path(self):
        from handlers.utils import sqs_handler

        @sqs_handler
        def message_handler(message: dict):  # noqa: ARG001 unused-argument
            return

        event = {'Records': [{'messageId': str(uuid4()), 'body': json.dumps({'foo': 'bar'})}]}

        resp = message_handler(event, self.mock_context)  # pylint: disable=too-many-function-args

        self.assertEqual({'batchItemFailures': []}, resp)

    def test_partial_failure(self):
        from handlers.utils import sqs_handler

        mock_partial_failures = Mock(
            # Responses when called - three successes, two failures
            side_effect=[None, RuntimeError('Oh no!'), None, None, RuntimeError('Not again!')],
        )

        @sqs_handler
        def message_handler(message: dict):  # noqa: ARG001 unused-argument
            return mock_partial_failures()

        event = {
            'Records': [
                {'messageId': '1', 'body': json.dumps({'foo': 'bar'})},
                {'messageId': '2', 'body': json.dumps({'foo': 'bar'})},
                {'messageId': '3', 'body': json.dumps({'foo': 'bar'})},
                {'messageId': '4', 'body': json.dumps({'foo': 'bar'})},
                {'messageId': '5', 'body': json.dumps({'foo': 'bar'})},
            ],
        }

        resp = message_handler(event, self.mock_context)  # pylint: disable=too-many-function-args

        self.assertEqual({'batchItemFailures': [{'itemIdentifier': '2'}, {'itemIdentifier': '5'}]}, resp)
