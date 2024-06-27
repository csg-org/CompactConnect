import json

from moto import mock_aws
from tests.function import TstFunction


@mock_aws
class TestMain(TstFunction):
    def test_get_bulk_upload_url(self):
        from main import bulk_upload_url_handler

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)

        resp = bulk_upload_url_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        body = json.loads(resp['body'])
        self.assertEqual({'url', 'fields'}, body['upload'].keys())

    def test_get_bulk_upload_url_forbidden(self):
        from main import bulk_upload_url_handler

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff'

        resp = bulk_upload_url_handler(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])

    def test_get_no_auth_bulk_upload_url(self):
        from main import no_auth_bulk_upload_url_handler

        with open('tests/resources/api-event.json', 'r') as f:
            event = json.load(f)
        del event['requestContext']['authorizer']

        resp = no_auth_bulk_upload_url_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        body = json.loads(resp['body'])
        self.assertEqual({'url', 'fields'}, body['upload'].keys())
