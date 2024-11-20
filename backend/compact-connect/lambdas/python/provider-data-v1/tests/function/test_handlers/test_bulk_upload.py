import json
from uuid import uuid4

from botocore.exceptions import ClientError
from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class TestBulkUpload(TstFunction):
    def test_get_bulk_upload_url(self):
        from handlers.bulk_upload import bulk_upload_url_handler

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/oh.write'
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}
        resp = bulk_upload_url_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        body = json.loads(resp['body'])
        self.assertEqual({'url', 'fields'}, body['upload'].keys())

    def test_get_bulk_upload_url_forbidden(self):
        from handlers.bulk_upload import bulk_upload_url_handler

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
        # User has permission in ne, not oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff aslp/ne.write'
        event['pathParameters'] = {'compact': 'aslp', 'jurisdiction': 'oh'}

        resp = bulk_upload_url_handler(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])


@mock_aws
class TestProcessObjects(TstFunction):
    def test_uploaded_csv(self):
        from handlers.bulk_upload import parse_bulk_upload_file

        # Upload a bulk license csv file
        object_key = f'aslp/co/{uuid4().hex}'
        self._bucket.upload_file('../common/tests/resources/licenses.csv', object_key)

        # Simulate the s3 bucket event
        with open('../common/tests/resources/put-event.json') as f:
            event = json.load(f)

        event['Records'][0]['s3']['bucket'] = {
            'name': self._bucket.name,
            'arn': f'arn:aws:s3:::{self._bucket.name}',
            'ownerIdentity': {'principalId': 'ASDFG123'},
        }
        event['Records'][0]['s3']['object']['key'] = object_key

        parse_bulk_upload_file(event, self.mock_context)

        # The object should be gone, once parsing is complete
        with self.assertRaises(ClientError):
            self._bucket.Object(object_key).get()
