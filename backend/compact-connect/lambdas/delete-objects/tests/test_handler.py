import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from aws_lambda_powertools.utilities.typing import LambdaContext


class TestHandler(TestCase):
    @patch('main.s3_client')
    def test_delete_objects(self, mock_s3_client):
        with open('tests/resources/put-event.json', 'r') as f:
            event = json.load(f)
        event['Records'][0]['s3']['object']['key'] = 'SomeUpperCase.json'

        context = MagicMock(spec=LambdaContext)

        from main import delete_objects

        delete_objects(event, context)

        mock_s3_client.delete_object.assert_called_once()
