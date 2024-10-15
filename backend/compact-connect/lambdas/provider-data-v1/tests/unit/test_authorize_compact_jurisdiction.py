import json

from aws_lambda_powertools.utilities.typing import LambdaContext

from tests import TstLambdas


class TestAuthorizeCompactJurisdiction(TstLambdas):
    def test_scope_by_path(self):
        from handlers.utils import authorize_compact_jurisdiction

        @authorize_compact_jurisdiction(action='write')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/oh.write'
        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'oh',
        }

        self.assertEqual({'body': 'Hurray!'}, example_entrypoint(event, self.mock_context))

    def test_no_path_param(self):
        from exceptions import CCInvalidRequestException
        from handlers.utils import authorize_compact_jurisdiction

        @authorize_compact_jurisdiction(action='write')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/oh.write'
        event['pathParameters'] = {}

        with self.assertRaises(CCInvalidRequestException):
            example_entrypoint(event, self.mock_context)

    def test_no_authorizer(self):
        from exceptions import CCUnauthorizedException
        from handlers.utils import authorize_compact_jurisdiction

        @authorize_compact_jurisdiction(action='write')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        del event['requestContext']['authorizer']
        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'oh',
        }

        with self.assertRaises(CCUnauthorizedException):
            example_entrypoint(event, self.mock_context)

    def test_missing_scope(self):
        from exceptions import CCAccessDeniedException
        from handlers.utils import authorize_compact_jurisdiction

        @authorize_compact_jurisdiction(action='write')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff'
        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'oh',
        }

        with self.assertRaises(CCAccessDeniedException):
            example_entrypoint(event, self.mock_context)


class TestAuthorizeCompact(TstLambdas):
    def test_authorize_compact(self):
        from handlers.utils import authorize_compact

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/read'
        event['pathParameters'] = {
            'compact': 'aslp',
        }

        self.assertEqual({'body': 'Hurray!'}, example_entrypoint(event, self.mock_context))

    def test_no_path_param(self):
        from exceptions import CCInvalidRequestException
        from handlers.utils import authorize_compact

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/read'
        event['pathParameters'] = {}

        with self.assertRaises(CCInvalidRequestException):
            example_entrypoint(event, self.mock_context)

    def test_no_authorizer(self):
        from exceptions import CCUnauthorizedException
        from handlers.utils import authorize_compact

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        del event['requestContext']['authorizer']
        event['pathParameters'] = {
            'compact': 'aslp'
        }

        with self.assertRaises(CCUnauthorizedException):
            example_entrypoint(event, self.mock_context)

    def test_missing_scope(self):
        from exceptions import CCAccessDeniedException
        from handlers.utils import authorize_compact

        @authorize_compact(action='read')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff'
        event['pathParameters'] = {
            'compact': 'aslp'
        }

        with self.assertRaises(CCAccessDeniedException):
            example_entrypoint(event, self.mock_context)
