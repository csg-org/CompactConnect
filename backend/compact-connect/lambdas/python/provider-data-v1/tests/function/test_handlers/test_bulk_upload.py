import csv
import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

from botocore.exceptions import ClientError
from moto import mock_aws

from tests.function import TstFunction

mock_flag_client = MagicMock()
mock_flag_client.return_value = True


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
@patch('cc_common.feature_flag_client.is_feature_enabled', mock_flag_client)
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

    def test_bulk_upload_prevents_compact_jurisdiction_overwrites(self):
        """Test that CSV compact/jurisdiction fields cannot overwrite URL path values."""
        from handlers.bulk_upload import parse_bulk_upload_file

        # Create CSV content that includes compact and jurisdiction fields
        # These should NOT be allowed to overwrite the values from the URL path
        csv_content = (
            'ssn,npi,licenseNumber,givenName,middleName,familyName,suffix,dateOfBirth,dateOfIssuance'
            ',dateOfRenewal,dateOfExpiration,licenseStatus,compactEligibility,homeAddressStreet1'
            ',homeAddressStreet2,homeAddressCity,homeAddressState,homeAddressPostalCode'
            ',emailAddress,phoneNumber,licenseType,licenseStatusName,compact,jurisdiction\n'
            '123-45-6789,1234567890,LICENSE123,John,Middle,Doe,Jr.,1990-01-01,2020-01-01,2021-01-01,2023-01-01,active,'
            'eligible,123 Main St,Apt 1,Columbus,OH,43215,test@example.com,+15551234567,audiologist,Active,'
            'malicious_compact,malicious_jurisdiction'
        )

        # Upload the CSV content directly to the mock S3 bucket
        # URL path indicates aslp/oh, but CSV contains malicious_compact/malicious_jurisdiction
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

        # Mock EventBatchWriter to capture put_event calls
        with patch('handlers.bulk_upload.EventBatchWriter') as mock_event_writer_class:
            mock_event_writer = mock_event_writer_class.return_value.__enter__.return_value
            # Mock the failed_entry_count attribute to return 0
            mock_event_writer.failed_entry_count = 0

            # Process the file - should not raise an exception
            parse_bulk_upload_file(event, self.mock_context)

            # Verify that put_event was called for the validation error
            mock_event_writer.put_event.assert_called_once()

            # Get the call arguments to verify the event details
            call_args = mock_event_writer.put_event.call_args[1]['Entry']

            # Verify the complete event structure
            expected_entry = {
                'Source': f'org.compactconnect.bulk-ingest.{object_key}',
                'DetailType': 'license.validation-error',
                'Detail': json.dumps(
                    {
                        'eventTime': '1970-01-01T00:00:00+00:00',
                        'compact': 'aslp',
                        'jurisdiction': 'oh',
                        'recordNumber': 1,
                        'validData': {
                            'licenseType': 'audiologist',
                            'licenseStatusName': 'Active',
                            'licenseStatus': 'active',
                            'compactEligibility': 'eligible',
                            'npi': '1234567890',
                            'licenseNumber': 'LICENSE123',
                            'givenName': 'John',
                            'middleName': 'Middle',
                            'familyName': 'Doe',
                            'suffix': 'Jr.',
                            'dateOfIssuance': '2020-01-01',
                            'dateOfRenewal': '2021-01-01',
                            'dateOfExpiration': '2023-01-01',
                        },
                        'errors': ['License contains unsupported fields'],
                    }
                ),
                'EventBusName': 'license-data-events',
            }

            self.assertEqual(expected_entry, call_args)

    def test_bulk_upload_prevents_repeated_ssns_within_the_same_file_upload(self):
        """Test that duplicate SSNs within a CSV upload are detected and rejected."""
        from handlers.bulk_upload import parse_bulk_upload_file

        # Create CSV content that includes duplicate SSNs
        # Rows that duplicate the same SSN will be considered an error and not processed
        csv_content = (
            'ssn,npi,licenseNumber,givenName,middleName,familyName,suffix,dateOfBirth,dateOfIssuance'
            ',dateOfRenewal,dateOfExpiration,licenseStatus,compactEligibility,homeAddressStreet1'
            ',homeAddressStreet2,homeAddressCity,homeAddressState,homeAddressPostalCode'
            ',emailAddress,phoneNumber,licenseType,licenseStatusName\n'
            '123-45-6789,1234567890,LICENSE123,John,Middle,Doe,Jr.,1990-01-01,2020-01-01,2021-01-01,2023-01-01,active,'
            'eligible,123 Main St,Apt 1,Columbus,OH,43215,test@example.com,+15551234567,audiologist,Active\n'
            '123-45-6789,1234567890,LICENSE456,Jane,Middle,Smith,,1995-01-01,2023-01-01,2025-01-01,2026-01-01,active,'
            'eligible,123 Main St,Apt 1,Columbus,OH,43215,test@example.com,+15551234567,audiologist,Active'
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

        # Mock EventBatchWriter to capture put_event calls
        with patch('handlers.bulk_upload.EventBatchWriter') as mock_event_writer_class:
            mock_event_writer = mock_event_writer_class.return_value.__enter__.return_value
            # Mock the failed_entry_count attribute to return 0
            mock_event_writer.failed_entry_count = 0

            # Process the file - should not raise an exception
            parse_bulk_upload_file(event, self.mock_context)

            # Verify that put_event was called for the validation error
            mock_event_writer.put_event.assert_called_once()

            # Get the call arguments to verify the event details
            call_args = mock_event_writer.put_event.call_args[1]['Entry']

            # Verify the complete event structure
            expected_entry = {
                'Source': f'org.compactconnect.bulk-ingest.{object_key}',
                'DetailType': 'license.validation-error',
                'Detail': json.dumps(
                    {
                        'eventTime': '1970-01-01T00:00:00+00:00',
                        'compact': 'aslp',
                        'jurisdiction': 'oh',
                        'recordNumber': 2,
                        'validData': {
                            'licenseType': 'audiologist',
                            'licenseStatusName': 'Active',
                            'licenseStatus': 'active',
                            'compactEligibility': 'eligible',
                            'npi': '1234567890',
                            'licenseNumber': 'LICENSE456',
                            'givenName': 'Jane',
                            'middleName': 'Middle',
                            'familyName': 'Smith',
                            'dateOfIssuance': '2023-01-01',
                            'dateOfRenewal': '2025-01-01',
                            'dateOfExpiration': '2026-01-01',
                        },
                        'errors': [
                            'Duplicate License SSN detected for license type audiologist. SSN matches with record 1. '
                            'Every record must have a unique SSN per license type within the same file.'
                        ],
                    }
                ),
                'EventBusName': 'license-data-events',
            }

            self.assertEqual(expected_entry, call_args)

    def test_bulk_upload_allows_repeated_ssns_for_different_license_types(self):
        """Test that duplicate SSNs within a CSV upload are allowed if the license types are different."""
        from handlers.bulk_upload import parse_bulk_upload_file

        # Create CSV content that includes duplicate SSNs but different license types
        csv_content = (
            'ssn,npi,licenseNumber,givenName,middleName,familyName,suffix,dateOfBirth,dateOfIssuance'
            ',dateOfRenewal,dateOfExpiration,licenseStatus,compactEligibility,homeAddressStreet1'
            ',homeAddressStreet2,homeAddressCity,homeAddressState,homeAddressPostalCode'
            ',emailAddress,phoneNumber,licenseType,licenseStatusName\n'
            '123-45-6789,1234567890,LICENSE123,John,Middle,Doe,Jr.,1990-01-01,2020-01-01,2021-01-01,2023-01-01,active,'
            'eligible,123 Main St,Apt 1,Columbus,OH,43215,test@example.com,+15551234567,audiologist,Active\n'
            '123-45-6789,1234567890,LICENSE456,John,Middle,Doe,Jr.,1990-01-01,2023-01-01,2025-01-01,2026-01-01,active,'
            'eligible,123 Main St,Apt 1,Columbus,OH,43215,test@example.com,+15551234567,speech-language pathologist,Active'
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

        # Verify that both messages were sent to the preprocessing queue
        messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(2, len(messages))

        message_data_1 = json.loads(messages[0].body)
        message_data_2 = json.loads(messages[1].body)

        # Verify the license types are correct
        # Messages might not be in order, so we check both
        license_types = {message_data_1['licenseType'], message_data_2['licenseType']}
        self.assertEqual({'audiologist', 'speech-language pathologist'}, license_types)

        # Verify SSNs are the same
        self.assertEqual(message_data_1['ssn'], '123-45-6789')
        self.assertEqual(message_data_2['ssn'], '123-45-6789')

    def test_bulk_upload_handles_bom_character(self):
        """Test that CSV files with BOM characters are handled correctly."""
        from handlers.bulk_upload import parse_bulk_upload_file

        # Create CSV content without BOM in the string (BOM will be added during encoding)
        csv_content = (
            'dateOfIssuance,npi,licenseNumber,dateOfBirth,licenseType,familyName,homeAddressCity,middleName,'
            'licenseStatus,licenseStatusName,compactEligibility,ssn,homeAddressStreet1,homeAddressStreet2,'
            'dateOfExpiration,homeAddressState,homeAddressPostalCode,givenName,dateOfRenewal\n'
            '2024-06-30,0608337260,BOM0608337260,2024-06-30,speech-language pathologist,TestFamily,Columbus,'
            'TestMiddle,active,ACTIVE,eligible,529-31-5413,123 BOM Test St.,Apt 1,2024-06-30,oh,43215,'
            'TestGiven,2024-06-30'
        )

        # Upload the CSV content with BOM added at byte level (simulates real BOM files)
        object_key = f'aslp/oh/{uuid4().hex}'
        self._bucket.put_object(Key=object_key, Body=csv_content.encode('utf-8-sig'))

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

        # Verify that the license was processed correctly despite the BOM character
        self.assertEqual('BOM0608337260', message_data['licenseNumber'])
        self.assertEqual('TestGiven', message_data['givenName'])
        self.assertEqual('TestMiddle', message_data['middleName'])
        self.assertEqual('TestFamily', message_data['familyName'])
        self.assertEqual('Columbus', message_data['homeAddressCity'])
        self.assertEqual('123 BOM Test St.', message_data['homeAddressStreet1'])
        self.assertEqual('Apt 1', message_data['homeAddressStreet2'])
        self.assertEqual('oh', message_data['homeAddressState'])
        self.assertEqual('43215', message_data['homeAddressPostalCode'])
        self.assertEqual('speech-language pathologist', message_data['licenseType'])
        self.assertEqual('active', message_data['licenseStatus'])
        self.assertEqual('ACTIVE', message_data['licenseStatusName'])
        self.assertEqual('eligible', message_data['compactEligibility'])
        self.assertEqual('529-31-5413', message_data['ssn'])
        self.assertEqual('0608337260', message_data['npi'])

        # Verify injected fields
        self.assertEqual('aslp', message_data['compact'])
        self.assertEqual('oh', message_data['jurisdiction'])
        self.assertEqual('1970-01-01T00:00:00+00:00', message_data['eventTime'])

        # The object should be gone, once parsing is complete
        with self.assertRaises(ClientError):
            self._bucket.Object(object_key).get()
