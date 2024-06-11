import json
import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

from aws_lambda_powertools.utilities.typing import LambdaContext


@patch.dict(os.environ, {'DEBUG': 'true'})
class TestHandler(TestCase):

    def test_customize_scopes(self):
        context = MagicMock(spec=LambdaContext)

        from main import customize_scopes

        with open('tests/resources/pre-token-event.json', 'r') as f:
            event = json.load(f)
        resp = customize_scopes(event, context)

        self.assertEqual(
            ['aslp/al'],
            resp['response']['claimsAndScopeOverrideDetails']['accessTokenGeneration']['scopesToAdd']
        )

    def test_no_attributes(self):
        context = MagicMock(spec=LambdaContext)

        from main import customize_scopes

        with open('tests/resources/pre-token-event.json', 'r') as f:
            event = json.load(f)
        del event['request']['userAttributes']['custom:compact']
        del event['request']['userAttributes']['custom:jurisdiction']

        resp = customize_scopes(event, context)

        self.assertEqual(
            None,
            resp['response']['claimsAndScopeOverrideDetails']
        )
