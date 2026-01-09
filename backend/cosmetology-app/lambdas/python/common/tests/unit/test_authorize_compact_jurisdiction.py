import json

from aws_lambda_powertools.utilities.typing import LambdaContext

from tests import TstLambdas


class TestAuthorizeCompactJurisdiction(TstLambdas):
    def test_scope_by_path(self):
        from cc_common.utils import authorize_compact_jurisdiction

        @authorize_compact_jurisdiction(action='write')
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff oh/aslp.write'
        event['pathParameters'] = {
            'compact': 'aslp',
            'jurisdiction': 'oh',
        }

        self.assertEqual({'body': 'Hurray!'}, example_entrypoint(event, self.mock_context))

    def test_no_path_param(self):
        from cc_common.exceptions import CCInvalidRequestException
        from cc_common.utils import authorize_compact_jurisdiction

        @authorize_compact_jurisdiction(action='write')
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff oh/aslp.write'
        event['pathParameters'] = {}

        with self.assertRaises(CCInvalidRequestException):
            example_entrypoint(event, self.mock_context)

    def test_no_authorizer(self):
        from cc_common.exceptions import CCUnauthorizedException
        from cc_common.utils import authorize_compact_jurisdiction

        @authorize_compact_jurisdiction(action='write')
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

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
        from cc_common.exceptions import CCAccessDeniedException
        from cc_common.utils import authorize_compact_jurisdiction

        @authorize_compact_jurisdiction(action='write')
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

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
        from cc_common.data_model.schema.common import CCPermissionsAction
        from cc_common.utils import authorize_compact

        @authorize_compact(action=CCPermissionsAction.READ_GENERAL)
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/readGeneral'
        event['pathParameters'] = {
            'compact': 'aslp',
        }

        self.assertEqual({'body': 'Hurray!'}, example_entrypoint(event, self.mock_context))

    def test_no_path_param(self):
        from cc_common.data_model.schema.common import CCPermissionsAction
        from cc_common.exceptions import CCInvalidRequestException
        from cc_common.utils import authorize_compact

        @authorize_compact(action=CCPermissionsAction.READ_GENERAL)
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/readGeneral'
        event['pathParameters'] = {}

        with self.assertRaises(CCInvalidRequestException):
            example_entrypoint(event, self.mock_context)

    def test_no_authorizer(self):
        from cc_common.data_model.schema.common import CCPermissionsAction
        from cc_common.exceptions import CCUnauthorizedException
        from cc_common.utils import authorize_compact

        @authorize_compact(action=CCPermissionsAction.READ_GENERAL)
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'aslp'}

        with self.assertRaises(CCUnauthorizedException):
            example_entrypoint(event, self.mock_context)

    def test_missing_scope(self):
        from cc_common.data_model.schema.common import CCPermissionsAction
        from cc_common.exceptions import CCAccessDeniedException
        from cc_common.utils import authorize_compact

        @authorize_compact(action=CCPermissionsAction.READ_GENERAL)
        def example_entrypoint(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
            return {'body': 'Hurray!'}

        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff'
        event['pathParameters'] = {'compact': 'aslp'}

        with self.assertRaises(CCAccessDeniedException):
            example_entrypoint(event, self.mock_context)
