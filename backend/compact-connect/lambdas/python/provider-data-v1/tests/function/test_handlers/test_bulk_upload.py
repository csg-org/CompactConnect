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

    def test_bulk_upload_strips_whitespace_from_string_fields(self):
        """Test that whitespace is stripped from all string fields in CSV data."""
        from handlers.bulk_upload import parse_bulk_upload_file

        # Create CSV content with whitespace in string fields
        csv_content = (
            'ssn,npi,licenseNumber,givenName,middleName,familyName,suffix,dateOfBirth,dateOfIssuance'
            ',dateOfRenewal,dateOfExpiration,licenseStatus,compactEligibility,homeAddressStreet1'
            ',homeAddressStreet2,homeAddressCity,homeAddressState,homeAddressPostalCode'
            ',emailAddress,phoneNumber,licenseType,licenseStatusName\n'
            '123-45-6789,1234567890,'
            '  LICENSE123  ,'
            '  John  ,'
            '  Middle  ,'
            '  Doe  ,'
            '  Jr.  ,'
            '1990-01-01,'
            '2020-01-01,'
            '2021-01-01,'
            '2023-01-01,'
            '  active  ,'
            '  eligible  ,'
            '  123 Main St  ,'
            '  Apt 1  ,'
            '  Columbus  ,'
            '  OH  ,'
            '  43215  ,'
            '  test@example.com,'
            '+15551234567,'
            '  audiologist  ,'
            '  Active  '
        )

        # Upload the CSV content directly to the mock S3 bucket
        object_key = f'aslp/oh/{uuid4().hex}'
        self._bucket.put_object(Key=object_key, Body=csv_content)

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

        # Verify that one message was sent to the preprocessing queue
        messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(1, len(messages))

        message_data = json.loads(messages[0].body)

        # Verify that whitespace was stripped from all string fields
        self.assertEqual('LICENSE123', message_data['licenseNumber'])  # Should be trimmed
        self.assertEqual('John', message_data['givenName'])  # Should be trimmed
        self.assertEqual('Middle', message_data['middleName'])  # Should be trimmed
        self.assertEqual('Doe', message_data['familyName'])  # Should be trimmed
        self.assertEqual('Jr.', message_data['suffix'])  # Should be trimmed
        self.assertEqual('123 Main St', message_data['homeAddressStreet1'])  # Should be trimmed
        self.assertEqual('Apt 1', message_data['homeAddressStreet2'])  # Should be trimmed
        self.assertEqual('Columbus', message_data['homeAddressCity'])  # Should be trimmed
        self.assertEqual('OH', message_data['homeAddressState'])  # Should be trimmed
        self.assertEqual('43215', message_data['homeAddressPostalCode'])  # Should be trimmed
        self.assertEqual('test@example.com', message_data['emailAddress'])  # Should be trimmed
        self.assertEqual('audiologist', message_data['licenseType'])  # Should be trimmed
        self.assertEqual('Active', message_data['licenseStatusName'])  # Should be trimmed

        # Verify that other fields remain unchanged
        self.assertEqual('aslp', message_data['compact'])
        self.assertEqual('oh', message_data['jurisdiction'])
        self.assertEqual('123-45-6789', message_data['ssn'])
        self.assertEqual('1234567890', message_data['npi'])
        self.assertEqual('active', message_data['licenseStatus'])
        self.assertEqual('eligible', message_data['compactEligibility'])
