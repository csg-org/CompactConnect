import json

from aws_lambda_powertools.utilities.typing import LambdaContext

from tests import TstLambdas


class TestScopeByPath(TstLambdas):
    def test_scope_by_path(self):
        from utils import scope_by_path

        @scope_by_path(scope_parameter='jurisdiction', resource_parameter='compact')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        self.assertEqual({'body': 'Hurray!'}, example_entrypoint(event, self.mock_context))

    def test_no_path_param(self):
        from utils import scope_by_path

        @scope_by_path(scope_parameter='jurisdiction', resource_parameter='compact')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)
        event['pathParameters'] = {}

        resp = example_entrypoint(event, self.mock_context)
        self.assertEqual(401, resp['statusCode'])

    def test_no_authorizer(self):
        from utils import scope_by_path

        @scope_by_path(scope_parameter='jurisdiction', resource_parameter='compact')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)
        del event['requestContext']['authorizer']

        resp = example_entrypoint(event, self.mock_context)
        self.assertEqual(401, resp['statusCode'])

    def test_missing_scope(self):
        from utils import scope_by_path

        @scope_by_path(scope_parameter='jurisdiction', resource_parameter='compact')
        def example_entrypoint(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
            return {
                'body': 'Hurray!'
            }

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff'

        resp = example_entrypoint(event, self.mock_context)
        self.assertEqual(403, resp['statusCode'])
