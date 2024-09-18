import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from tests import TstLambdas


class TestApiHandler(TstLambdas):
    """
    Testing that the api_handler decorator is working as expected.
    """

    def test_happy_path(self):
        from utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {'message': 'OK'}

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        resp = lambda_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual('{"message": "OK"}', resp['body'])

    def test_unauthorized(self):
        from utils import api_handler
        from exceptions import CCUnauthorizedException

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):
            raise CCUnauthorizedException("You can't do that")

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(401, resp['statusCode'])

    def test_access_denied(self):
        from utils import api_handler
        from exceptions import CCAccessDeniedException

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):
            raise CCAccessDeniedException("You can't do that")

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(403, resp['statusCode'])

    def test_not_found(self):
        from utils import api_handler
        from exceptions import CCNotFoundException

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):
            raise CCNotFoundException("I don't see it.")

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(404, resp['statusCode'])
        self.assertEqual(
            {'message': "I don't see it."},
            json.loads(resp['body'])
        )

    def test_invalid_request(self):
        from utils import api_handler
        from exceptions import CCInvalidRequestException

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):
            raise CCInvalidRequestException("Your request is wrong.")

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        resp = lambda_handler(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])
        self.assertEqual(
            {'message': "Your request is wrong."},
            json.loads(resp['body'])
        )

    def test_client_error(self):
        from utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):
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
        from utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):
            raise RuntimeError('Egads!')

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        with self.assertRaises(RuntimeError):
            lambda_handler(event, self.mock_context)

    def test_null_headers(self):
        from utils import api_handler

        @api_handler
        def lambda_handler(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {'message': 'OK'}

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)
        event['headers'] = None

        resp = lambda_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual('{"message": "OK"}', resp['body'])
