import csv
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

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff oh/aslp.write'
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
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff ne/aslp.write'
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

    def test_bulk_upload_processor_puts_messages_on_preprocessing_queue(self):
        from handlers.bulk_upload import parse_bulk_upload_file

        # Upload a bulk license csv file
        object_key = f'aslp/oh/{uuid4().hex}'
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

        # the test csv file has 5 valid licenses, so we should have 5 messages on the queue
        messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(5, len(messages))

        # load the csv test data into a dict object. Example row:
        csv_licenses = {}
        with open('../common/tests/resources/licenses.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # add compact and jurisdiction to each row since this is injected into the sqs message
                row['compact'] = 'aslp'
                row['jurisdiction'] = 'oh'
                # the event time comes from the test put-event.json file
                row['eventTime'] = '1970-01-01T00:00:00+00:00'
                # some rows have an empty homeAddressStreet2, which we need to remove from the expected object
                if not row['homeAddressStreet2']:
                    row.pop('homeAddressStreet2', None)
                csv_licenses[row['licenseNumber']] = row

        for message in messages:
            message_data = json.loads(message.body)
            self.assertEqual(csv_licenses[message_data['licenseNumber']], message_data)
