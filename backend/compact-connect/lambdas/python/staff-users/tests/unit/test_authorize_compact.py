import json

from aws_lambda_powertools.utilities.typing import LambdaContext

from tests import TstLambdas


class TestAuthorizeCompact(TstLambdas):
    def test_authorize_compact(self):
        from cc_common.utils import authorize_compact

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/read'
        event['pathParameters'] = {
            'compact': 'aslp',
        }

        self.assertEqual({'body': 'Hurray!'}, example_entrypoint(event, self.mock_context))

    def test_no_path_param(self):
        from cc_common.exceptions import CCInvalidRequestException
        from cc_common.utils import authorize_compact

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/read'
        event['pathParameters'] = {}

        with self.assertRaises(CCInvalidRequestException):
            example_entrypoint(event, self.mock_context)

    def test_no_authorizer(self):
        from cc_common.exceptions import CCUnauthorizedException
        from cc_common.utils import authorize_compact

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp'}

        with self.assertRaises(CCUnauthorizedException):
            example_entrypoint(event, self.mock_context)

    def test_missing_scope(self):
        from cc_common.exceptions import CCAccessDeniedException
        from cc_common.utils import authorize_compact

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff'
        event['pathParameters'] = {'compact': 'aslp'}

        with self.assertRaises(CCAccessDeniedException):
            example_entrypoint(event, self.mock_context)
