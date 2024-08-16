import json

from botocore.exceptions import ClientError

from exceptions import CCInvalidRequestException
from tests import TstLambdas


class TestApiHandler(TstLambdas):
    def test_happy_path(self):
        from handlers.utils import api_handler

        @api_handler
        def lambda_handler(event, context):  # pylint: disable=unused-argument
            return {'message': 'OK'}

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        resp = lambda_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual('{"message": "OK"}', resp['body'])

    def test_invalid_request(self):
        from handlers.utils import api_handler

        @api_handler
        def lambda_handler(event, context):
            raise CCInvalidRequestException("You can't do that")

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {'message': "You can't do that"},
            json.loads(resp['body'])
        )

    def test_client_error(self):
        from handlers.utils import api_handler

        @api_handler
        def lambda_handler(event, context):
            raise ClientError(
                error_response={
                    'Error': {
                        'Code': "CantDoThatException"
                    }
                },
                operation_name='DoAWSThing'
            )

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        with self.assertRaises(ClientError):
            lambda_handler(event, self.mock_context)

    def test_runtime_error(self):
        from handlers.utils import api_handler

        @api_handler
        def lambda_handler(event, context):
            raise RuntimeError('Egads!')

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        with self.assertRaises(RuntimeError):
            lambda_handler(event, self.mock_context)

    def test_null_headers(self):
        from handlers.utils import api_handler

        @api_handler
        def lambda_handler(event, context):  # pylint: disable=unused-argument
            return {'message': 'OK'}

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)
        event['headers'] = None

        resp = lambda_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual('{"message": "OK"}', resp['body'])
