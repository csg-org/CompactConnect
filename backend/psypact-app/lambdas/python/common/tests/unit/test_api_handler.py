# ruff: noqa: ARG001 unused-argument
import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from tests import TstLambdas


class TestApiHandler(TstLambdas):
    """Testing that the api_handler decorator is working as expected."""

    def test_happy_path(self):
        from cc_common.utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):
            return {'message': 'OK'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        resp = lambda_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual('{"message": "OK"}', resp['body'])
        self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])

    def test_unauthorized(self):
        from cc_common.exceptions import CCUnauthorizedException
        from cc_common.utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):
            raise CCUnauthorizedException("You can't do that")

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(401, resp['statusCode'])
        self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])

    def test_invalid_request(self):
        from cc_common.exceptions import CCInvalidRequestException
        from cc_common.utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):
            raise CCInvalidRequestException("You can't do that")

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        self.assertEqual({'message': "You can't do that"}, json.loads(resp['body']))
        self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])

    def test_client_error(self):
        from cc_common.utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):
            raise ClientError(error_response={'Error': {'Code': 'CantDoThatException'}}, operation_name='DoAWSThing')

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        with self.assertRaises(ClientError):
            lambda_handler(event, self.mock_context)

    def test_runtime_error(self):
        from cc_common.utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):
            raise RuntimeError('Egads!')

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        with self.assertRaises(RuntimeError):
            lambda_handler(event, self.mock_context)

    def test_null_headers(self):
        from cc_common.utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'message': 'OK'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['headers'] = None

        resp = lambda_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual('{"message": "OK"}', resp['body'])
        self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])

    def test_local_ui(self):
        from cc_common.utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'message': 'OK'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['headers']['origin'] = 'http://localhost:1234'

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        self.assertEqual('http://localhost:1234', resp['headers']['Access-Control-Allow-Origin'])

    def test_disallowed_origin(self):
        from cc_common.utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'message': 'OK'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['headers']['origin'] = 'https://example.com'  # not in ALLOWED_ORIGINS

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])

    def test_no_origin(self):
        from cc_common.utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'message': 'OK'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        del event['headers']['origin']

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        self.assertEqual('https://example.org', resp['headers']['Access-Control-Allow-Origin'])

    def test_unsupported_media_type(self):
        from cc_common.utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'message': 'OK'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        # We only accept json
        event['headers']['Content-Type'] = 'text/plain'
        event['body'] = 'not json'

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(415, resp['statusCode'])

    def test_json_decode_error(self):
        from cc_common.utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return json.loads(event['body'])

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        event['headers']['Content-Type'] = 'application/json'
        event['body'] = 'not json'

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
