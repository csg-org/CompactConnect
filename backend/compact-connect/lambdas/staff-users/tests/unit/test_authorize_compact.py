import json

from aws_lambda_powertools.utilities.typing import LambdaContext

from tests import TstLambdas


class TestAuthorizeCompact(TstLambdas):
    def test_authorize_compact(self):
        from utils import authorize_compact

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/read'
        event['pathParameters'] = {
            'compact': 'aslp',
        }

        self.assertEqual({'body': 'Hurray!'}, example_entrypoint(event, self.mock_context))

    def test_no_path_param(self):
        from utils import authorize_compact
        from exceptions import CCInvalidRequestException

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/read'
        event['pathParameters'] = {}

        with self.assertRaises(CCInvalidRequestException):
            example_entrypoint(event, self.mock_context)

    def test_no_authorizer(self):
        from utils import authorize_compact
        from exceptions import CCUnauthorizedException

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)
        del event['requestContext']['authorizer']
        event['pathParameters'] = {
            'compact': 'aslp'
        }

        with self.assertRaises(CCUnauthorizedException):
            example_entrypoint(event, self.mock_context)

    def test_missing_scope(self):
        from utils import authorize_compact
        from exceptions import CCAccessDeniedException

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff'
        event['pathParameters'] = {
            'compact': 'aslp'
        }

        with self.assertRaises(CCAccessDeniedException):
            example_entrypoint(event, self.mock_context)
