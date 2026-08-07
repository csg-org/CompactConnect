import csv
import json
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from botocore.exceptions import ClientError
from common_test.test_constants import DEFAULT_DATE_OF_UPDATE_TIMESTAMP
from moto import mock_aws

from tests.function import TstFunction

VALIDATION_ERROR_EVENT_TIME = '2024-11-08T23:59:59+00:00'

mock_flag_client = MagicMock()
mock_flag_client.return_value = True


@mock_aws
class TestBulkUpload(TstFunction):
    def test_get_bulk_upload_url(self):
        from handlers.bulk_upload import bulk_upload_url_handler

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff oh/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}
        resp = bulk_upload_url_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        body = json.loads(resp['body'])
        self.assertEqual({'url', 'fields'}, body['upload'].keys())

    def test_get_bulk_upload_url_forbidden(self):
        from handlers.bulk_upload import bulk_upload_url_handler

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
        # User has permission in ne, not oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email stuff ne/socw.write'
        event['pathParameters'] = {'compact': 'socw', 'jurisdiction': 'oh'}

        resp = bulk_upload_url_handler(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(DEFAULT_DATE_OF_UPDATE_TIMESTAMP))
class TestProcessObjects(TstFunction):
    def test_uploaded_csv(self):
        from handlers.bulk_upload import parse_bulk_upload_file

        # Upload a bulk license csv file
        object_key = f'socw/co/{uuid4().hex}'
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
        object_key = f'socw/oh/{uuid4().hex}'
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
                row['compact'] = 'socw'
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
            'ssn,licenseNumber,givenName,middleName,familyName,suffix,dateOfBirth,dateOfIssuance'
            ',dateOfRenewal,dateOfExpiration,licenseStatus,compactEligibility,homeAddressStreet1'
            ',homeAddressStreet2,homeAddressCity,homeAddressState,homeAddressPostalCode'
            ',emailAddress,phoneNumber,licenseType,licenseScope,licenseStatusName\n'
            '123-45-6789,'
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
            '  licensed clinical social worker  ,'
            '  single-state  ,'
            '  Active  '
        )

        # Upload the CSV content directly to the mock S3 bucket
        object_key = f'socw/oh/{uuid4().hex}'
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
        self.assertEqual('licensed clinical social worker', message_data['licenseType'])  # Should be trimmed
        self.assertEqual('single-state', message_data['licenseScope'])  # Should be trimmed
        self.assertEqual('Active', message_data['licenseStatusName'])  # Should be trimmed

        # Verify that other fields remain unchanged
        self.assertEqual('socw', message_data['compact'])
        self.assertEqual('oh', message_data['jurisdiction'])
        self.assertEqual('123-45-6789', message_data['ssn'])
        self.assertEqual('active', message_data['licenseStatus'])
        self.assertEqual('eligible', message_data['compactEligibility'])

    @patch(
        'cc_common.config._Config.current_standard_datetime',
        datetime.fromisoformat(VALIDATION_ERROR_EVENT_TIME),
    )
    def test_bulk_upload_prevents_compact_jurisdiction_overwrites(self):
        """Test that CSV compact/jurisdiction fields cannot overwrite URL path values."""
        from handlers.bulk_upload import parse_bulk_upload_file

        # Create CSV content that includes compact and jurisdiction fields
        # These should NOT be allowed to overwrite the values from the URL path
        csv_content = (
            'ssn,licenseNumber,givenName,middleName,familyName,suffix,dateOfBirth,dateOfIssuance'
            ',dateOfRenewal,dateOfExpiration,licenseStatus,compactEligibility,homeAddressStreet1'
            ',homeAddressStreet2,homeAddressCity,homeAddressState,homeAddressPostalCode'
            ',emailAddress,phoneNumber,licenseType,licenseScope,licenseStatusName,compact,jurisdiction\n'
            '123-45-6789,LICENSE123,John,Middle,Doe,Jr.,1990-01-01,2020-01-01,2021-01-01,2023-01-01,active,'
            'eligible,123 Main St,Apt 1,Columbus,OH,43215,test@example.com,+15551234567,licensed master social worker,'
            'single-state,Active,malicious_compact,malicious_jurisdiction'
        )

        # Upload the CSV content directly to the mock S3 bucket
        # URL path indicates socw/oh, but CSV contains malicious_compact/malicious_jurisdiction
        object_key = f'socw/oh/{uuid4().hex}'
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
                        'eventTime': VALIDATION_ERROR_EVENT_TIME,
                        'compact': 'socw',
                        'jurisdiction': 'oh',
                        'recordNumber': 1,
                        'validData': {
                            'licenseType': 'licensed master social worker',
                            'licenseScope': 'single-state',
                            'licenseStatusName': 'Active',
                            'licenseStatus': 'active',
                            'compactEligibility': 'eligible',
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

    @patch(
        'cc_common.config._Config.current_standard_datetime',
        datetime.fromisoformat(VALIDATION_ERROR_EVENT_TIME),
    )
    def test_bulk_upload_prevents_repeated_ssns_within_the_same_file_upload(self):
        """Test that duplicate SSNs within a CSV upload are detected and rejected."""
        from handlers.bulk_upload import parse_bulk_upload_file

        # Create CSV content that includes duplicate SSNs
        # Rows that duplicate the same SSN will be considered an error and not processed
        csv_content = (
            'ssn,licenseNumber,givenName,middleName,familyName,suffix,dateOfBirth,dateOfIssuance'
            ',dateOfRenewal,dateOfExpiration,licenseStatus,compactEligibility,homeAddressStreet1'
            ',homeAddressStreet2,homeAddressCity,homeAddressState,homeAddressPostalCode'
            ',emailAddress,phoneNumber,licenseType,licenseScope,licenseStatusName\n'
            '123-45-6789,LICENSE123,John,Middle,Doe,Jr.,1990-01-01,2020-01-01,2021-01-01,2023-01-01,active,'
            'eligible,123 Main St,Apt 1,Columbus,OH,43215,test@example.com,+15551234567,'
            'licensed clinical social worker,single-state,Active\n'
            '123-45-6789,LICENSE456,Jane,Middle,Smith,,1995-01-01,2023-01-01,2025-01-01,2026-01-01,active,'
            'eligible,123 Main St,Apt 1,Columbus,OH,43215,test@example.com,+15551234567,'
            'licensed clinical social worker,single-state,Active'
        )

        # Upload the CSV content directly to the mock S3 bucket
        object_key = f'socw/oh/{uuid4().hex}'
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
                        'eventTime': VALIDATION_ERROR_EVENT_TIME,
                        'compact': 'socw',
                        'jurisdiction': 'oh',
                        'recordNumber': 2,
                        'validData': {
                            'licenseType': 'licensed clinical social worker',
                            'licenseScope': 'single-state',
                            'licenseStatusName': 'Active',
                            'licenseStatus': 'active',
                            'compactEligibility': 'eligible',
                            'licenseNumber': 'LICENSE456',
                            'givenName': 'Jane',
                            'middleName': 'Middle',
                            'familyName': 'Smith',
                            'dateOfIssuance': '2023-01-01',
                            'dateOfRenewal': '2025-01-01',
                            'dateOfExpiration': '2026-01-01',
                        },
                        'errors': {
                            '_schema': [
                                'Duplicate License SSN detected for license type licensed clinical social worker '
                                'and scope single-state. SSN matches with record 1. Every record must have a unique '
                                'SSN per license type and scope within the same file.'
                            ]
                        },
                    }
                ),
                'EventBusName': 'license-data-events',
            }

            self.assertEqual(expected_entry, call_args)

    def test_bulk_upload_rejects_license_type_not_recognized_in_jurisdiction(self):
        """Test that bulk upload rejects license types not recognized by the uploading jurisdiction."""
        from handlers.bulk_upload import parse_bulk_upload_file

        csv_content = (
            'ssn,licenseNumber,givenName,middleName,familyName,suffix,dateOfBirth,dateOfIssuance'
            ',dateOfRenewal,dateOfExpiration,licenseStatus,compactEligibility,homeAddressStreet1'
            ',homeAddressStreet2,homeAddressCity,homeAddressState,homeAddressPostalCode'
            ',emailAddress,phoneNumber,licenseType,licenseScope,licenseStatusName\n'
            '123-45-6789,LICENSE123,John,Middle,Doe,Jr.,1990-01-01,2020-01-01,2021-01-01,2023-01-01,active,'
            'eligible,123 Main St,Apt 1,Columbus,OH,43215,test@example.com,+15551234567,'
            'licensed bachelors social worker,single-state,Active'
        )

        object_key = f'socw/co/{uuid4().hex}'
        self._bucket.put_object(Key=object_key, Body=csv_content)

        with open('../common/tests/resources/put-event.json') as f:
            event = json.load(f)

        event['Records'][0]['s3']['bucket'] = {
            'name': self._bucket.name,
            'arn': f'arn:aws:s3:::{self._bucket.name}',
            'ownerIdentity': {'principalId': 'ASDFG123'},
        }
        event['Records'][0]['s3']['object']['key'] = object_key

        with patch('handlers.bulk_upload.EventBatchWriter') as mock_event_writer_class:
            mock_event_writer = mock_event_writer_class.return_value.__enter__.return_value
            mock_event_writer.failed_entry_count = 0

            parse_bulk_upload_file(event, self.mock_context)

            mock_event_writer.put_event.assert_called_once()
            call_args = mock_event_writer.put_event.call_args[1]['Entry']

            expected_entry = {
                'Source': f'org.compactconnect.bulk-ingest.{object_key}',
                'DetailType': 'license.validation-error',
                'Detail': json.dumps(
                    {
                        'eventTime': DEFAULT_DATE_OF_UPDATE_TIMESTAMP,
                        'compact': 'socw',
                        'jurisdiction': 'co',
                        'recordNumber': 1,
                        'validData': {
                            'licenseType': 'licensed bachelors social worker',
                            'licenseScope': 'single-state',
                            'licenseStatusName': 'Active',
                            'licenseStatus': 'active',
                            'compactEligibility': 'eligible',
                            'licenseNumber': 'LICENSE123',
                            'givenName': 'John',
                            'middleName': 'Middle',
                            'familyName': 'Doe',
                            'suffix': 'Jr.',
                            'dateOfIssuance': '2020-01-01',
                            'dateOfRenewal': '2021-01-01',
                            'dateOfExpiration': '2023-01-01',
                        },
                        'errors': {
                            'licenseType': [
                                'License type licensed bachelors social worker is not recognized in jurisdiction co.'
                            ]
                        },
                    }
                ),
                'EventBusName': 'license-data-events',
            }

            self.assertEqual(expected_entry, call_args)

        messages = self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)
        self.assertEqual(0, len(messages))

    def test_bulk_upload_allows_repeated_ssns_for_different_license_types(self):
        """Test that duplicate SSNs within a CSV upload are allowed if the license types are different."""
        from handlers.bulk_upload import parse_bulk_upload_file

        # Create CSV content that includes duplicate SSNs but different license types
        csv_content = (
            'ssn,licenseNumber,givenName,middleName,familyName,suffix,dateOfBirth,dateOfIssuance'
            ',dateOfRenewal,dateOfExpiration,licenseStatus,compactEligibility,homeAddressStreet1'
            ',homeAddressStreet2,homeAddressCity,homeAddressState,homeAddressPostalCode'
            ',emailAddress,phoneNumber,licenseType,licenseScope,licenseStatusName\n'
            '123-45-6789,LICENSE123,John,Middle,Doe,Jr.,1990-01-01,2020-01-01,2021-01-01,2023-01-01,active,'
            'eligible,123 Main St,Apt 1,Columbus,OH,43215,test@example.com,+15551234567,'
            'licensed clinical social worker,single-state,Active\n'
            '123-45-6789,LICENSE456,John,Middle,Doe,Jr.,1990-01-01,2023-01-01,2025-01-01,2026-01-01,active,'
            'eligible,123 Main St,Apt 1,Columbus,OH,43215,test@example.com,+15551234567,licensed master social worker,'
            'single-state,Active'
        )

        # Upload the CSV content directly to the mock S3 bucket
        object_key = f'socw/oh/{uuid4().hex}'
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
        self.assertEqual({'licensed master social worker', 'licensed clinical social worker'}, license_types)

        # Verify SSNs are the same
        self.assertEqual(message_data_1['ssn'], '123-45-6789')
        self.assertEqual(message_data_2['ssn'], '123-45-6789')

    def test_bulk_upload_handles_bom_character(self):
        """Test that CSV files with BOM characters are handled correctly."""
        from handlers.bulk_upload import parse_bulk_upload_file

        # Create CSV content without BOM in the string (BOM will be added during encoding)
        csv_content = (
            'dateOfIssuance,licenseNumber,dateOfBirth,licenseType,licenseScope,familyName,homeAddressCity,middleName,'
            'licenseStatus,licenseStatusName,compactEligibility,ssn,homeAddressStreet1,homeAddressStreet2,'
            'dateOfExpiration,homeAddressState,homeAddressPostalCode,givenName,dateOfRenewal\n'
            '2024-06-30,BOM0608337260,2024-06-30,licensed master social worker,single-state,TestFamily,Columbus,'
            'TestMiddle,active,ACTIVE,eligible,529-31-5413,123 BOM Test St.,Apt 1,2024-06-30,oh,43215,'
            'TestGiven,2024-06-30'
        )

        # Upload the CSV content with BOM added at byte level (simulates real BOM files)
        object_key = f'socw/oh/{uuid4().hex}'
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
        self.assertEqual('licensed master social worker', message_data['licenseType'])
        self.assertEqual('active', message_data['licenseStatus'])
        self.assertEqual('ACTIVE', message_data['licenseStatusName'])
        self.assertEqual('eligible', message_data['compactEligibility'])
        self.assertEqual('529-31-5413', message_data['ssn'])

        # Verify injected fields
        self.assertEqual('socw', message_data['compact'])
        self.assertEqual('oh', message_data['jurisdiction'])
        self.assertEqual('1970-01-01T00:00:00+00:00', message_data['eventTime'])

        # The object should be gone, once parsing is complete
        with self.assertRaises(ClientError):
            self._bucket.Object(object_key).get()


# TODO - once LICENSE_UPLOAD_WITHOUT_SSN_FLAG is removed, drop the flag patch in the disabled-flag  # noqa: FIX002
#  test and keep the rest
@mock_aws
@patch('cc_common.feature_flag_client.is_feature_enabled', mock_flag_client)
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(VALIDATION_ERROR_EVENT_TIME))
class TestBulkUploadWithoutSsn(TstFunction):
    """
    Tests for CSV rows that leave the ssn column blank, identifying the practitioner by the license
    number a previous SSN-bearing upload stored for them.
    """

    CSV_HEADER = (
        'ssn,licenseNumber,givenName,familyName,dateOfBirth,dateOfIssuance,dateOfExpiration,'
        'licenseStatus,compactEligibility,homeAddressStreet1,homeAddressCity,homeAddressState,'
        'homeAddressPostalCode,licenseType,licenseScope'
    )

    def _csv_row(
        self,
        *,
        ssn: str = '',
        license_number: str = 'A0608337260',
        license_type: str = 'licensed clinical social worker',
        family_name: str = 'Guðmundsdóttir',
    ) -> str:
        return (
            f'{ssn},{license_number},Björk,{family_name},1985-06-06,2010-06-06,2050-04-04,'
            f'active,eligible,123 A St.,Columbus,oh,43004,{license_type},single-state'
        )

    def _seed_existing_license(self, **overrides):
        return self.test_data_generator.put_default_license_record_in_provider_table(value_overrides=overrides)

    def _process_csv(self, rows: list[str], flag_enabled: bool = True):
        """Upload a CSV to the mock bucket and run the parse handler over it."""
        from handlers import bulk_upload

        csv_content = '\n'.join([self.CSV_HEADER, *rows])
        object_key = f'socw/oh/{uuid4().hex}'
        self._bucket.put_object(Key=object_key, Body=csv_content)

        with open('../common/tests/resources/put-event.json') as f:
            event = json.load(f)
        event['Records'][0]['s3']['bucket'] = {
            'name': self._bucket.name,
            'arn': f'arn:aws:s3:::{self._bucket.name}',
            'ownerIdentity': {'principalId': 'ASDFG123'},
        }
        event['Records'][0]['s3']['object']['key'] = object_key

        with patch('handlers.bulk_upload.EventBatchWriter') as mock_event_writer_class:
            mock_event_writer = mock_event_writer_class.return_value.__enter__.return_value
            mock_event_writer.failed_entry_count = 0
            with patch(
                'handlers.bulk_upload.license_upload_without_ssn_flag_enabled',
                flag_enabled,
            ):
                bulk_upload.parse_bulk_upload_file(event, self.mock_context)

        entries = [call.kwargs['Entry'] for call in mock_event_writer.put_event.call_args_list]
        return object_key, entries

    @staticmethod
    def _details_of_type(entries: list[dict], detail_type: str) -> list[dict]:
        return [json.loads(entry['Detail']) for entry in entries if entry['DetailType'] == detail_type]

    def test_publishes_ingest_event_for_a_known_license_number(self):
        existing_license = self._seed_existing_license()

        _, entries = self._process_csv([self._csv_row(license_number=existing_license.licenseNumber)])

        ingest_details = self._details_of_type(entries, 'license.ingest')
        self.assertEqual(1, len(ingest_details))
        self.assertEqual(str(existing_license.providerId), ingest_details[0]['providerId'])
        self.assertEqual(existing_license.ssnLastFour, ingest_details[0]['ssnLastFour'])
        self.assertNotIn('ssn', ingest_details[0])

        # nothing goes to the SSN preprocessing queue, because there is no SSN to strip
        self.assertEqual(0, len(self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)))

    def test_emits_validation_error_for_an_unknown_license_number_and_keeps_processing(self):
        from license_upload_without_ssn import LICENSE_NUMBER_NOT_FOUND_ERROR_MESSAGE

        existing_license = self._seed_existing_license()

        _, entries = self._process_csv(
            [
                self._csv_row(license_number='NOT-A-REAL-NUMBER'),
                self._csv_row(license_number=existing_license.licenseNumber),
            ]
        )

        validation_errors = self._details_of_type(entries, 'license.validation-error')
        self.assertEqual(1, len(validation_errors))
        self.assertEqual(1, validation_errors[0]['recordNumber'])
        self.assertEqual(
            {'_schema': [LICENSE_NUMBER_NOT_FOUND_ERROR_MESSAGE]},
            validation_errors[0]['errors'],
        )
        self.assertEqual('NOT-A-REAL-NUMBER', validation_errors[0]['validData']['licenseNumber'])

        # the valid row on line 2 is still processed
        self.assertEqual(1, len(self._details_of_type(entries, 'license.ingest')))

    def test_emits_validation_error_for_an_ambiguous_license_number_and_keeps_processing(self):
        """
        An ambiguous license number fails only its own row. Aborting the whole file would punish every
        other practitioner in what can be a very large upload.
        """
        existing_license = self._seed_existing_license()
        self._seed_existing_license(
            providerId='2d3f1b0e-4c5a-4d6b-8e7f-9a0b1c2d3e4f',
            licenseType='licensed master social worker',
        )
        other_license = self._seed_existing_license(
            licenseNumber='B0608337260', licenseType='licensed master social worker'
        )

        _, entries = self._process_csv(
            [
                self._csv_row(license_number=existing_license.licenseNumber),
                self._csv_row(license_number=other_license.licenseNumber, license_type='licensed master social worker'),
            ]
        )

        validation_errors = self._details_of_type(entries, 'license.validation-error')
        self.assertEqual(1, len(validation_errors))
        self.assertEqual(1, validation_errors[0]['recordNumber'])

        # the unambiguous row on line 2 is still processed
        self.assertEqual(1, len(self._details_of_type(entries, 'license.ingest')))

    def test_emits_validation_error_for_a_duplicate_license_number_in_the_same_file(self):
        existing_license = self._seed_existing_license()

        _, entries = self._process_csv(
            [
                self._csv_row(license_number=existing_license.licenseNumber),
                self._csv_row(license_number=existing_license.licenseNumber),
            ]
        )

        validation_errors = self._details_of_type(entries, 'license.validation-error')
        self.assertEqual(1, len(validation_errors))
        self.assertEqual(2, validation_errors[0]['recordNumber'])
        # the error names the earlier line it collides with, so the state can find both rows
        self.assertIn('matches with record 1', validation_errors[0]['errors']['_schema'][0])

        # only the first occurrence is ingested
        self.assertEqual(1, len(self._details_of_type(entries, 'license.ingest')))

    def test_reports_a_duplicate_even_when_the_first_occurrence_could_not_be_resolved(self):
        """
        A row claims its license number whether or not it resolves, so the state is told the second row is
        a duplicate rather than being shown the same unknown-license-number error twice.
        """
        _, entries = self._process_csv(
            [
                self._csv_row(license_number='NOT-A-REAL-NUMBER'),
                self._csv_row(license_number='NOT-A-REAL-NUMBER'),
            ]
        )

        validation_errors = self._details_of_type(entries, 'license.validation-error')
        self.assertEqual(2, len(validation_errors))
        self.assertIn('No existing license record was found', validation_errors[0]['errors']['_schema'][0])
        self.assertIn('matches with record 1', validation_errors[1]['errors']['_schema'][0])
        self.assertEqual([], self._details_of_type(entries, 'license.ingest'))

    def test_accepts_the_same_license_number_for_two_license_types(self):
        existing_license = self._seed_existing_license()
        self._seed_existing_license(licenseType='licensed master social worker')

        _, entries = self._process_csv(
            [
                self._csv_row(license_number=existing_license.licenseNumber),
                self._csv_row(
                    license_number=existing_license.licenseNumber, license_type='licensed master social worker'
                ),
            ]
        )

        self.assertEqual([], self._details_of_type(entries, 'license.validation-error'))
        self.assertEqual(2, len(self._details_of_type(entries, 'license.ingest')))

    def test_processes_a_mixed_file_down_both_paths(self):
        existing_license = self._seed_existing_license()

        _, entries = self._process_csv(
            [
                self._csv_row(
                    ssn='123-45-6789', license_number='C0608337260', license_type='licensed master social worker'
                ),
                self._csv_row(license_number=existing_license.licenseNumber),
            ]
        )

        # the SSN-bearing row still goes through the preprocessor
        self.assertEqual(1, len(self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10)))
        self.assertEqual(1, len(self._details_of_type(entries, 'license.ingest')))
        self.assertEqual([], self._details_of_type(entries, 'license.validation-error'))

    def test_loads_the_license_number_index_once_for_the_whole_file(self):
        """
        The bulk path resolves rows against a single in-memory load of the jurisdiction's license number
        index. Querying per row would mean a network round trip per row, which is what puts a large file
        at risk of exhausting the lambda's execution time.
        """
        record_count = 25
        rows = []
        for index in range(record_count):
            license_number = f'INDEXLOAD{index:05d}'
            self._seed_existing_license(licenseNumber=license_number, providerId=str(uuid4()))
            rows.append(self._csv_row(license_number=license_number))

        import license_upload_without_ssn

        with patch.object(license_upload_without_ssn.config, 'data_client') as mock_data_client:
            mock_data_client.load_license_number_lookup.return_value.get.return_value = MagicMock(
                provider_id='89a6377e-c3a5-40e5-bca5-317ec854c570', ssn_last_four='1234'
            )
            _, entries = self._process_csv(rows)

        self.assertEqual(1, mock_data_client.load_license_number_lookup.call_count)
        mock_data_client.find_provider_by_license_number.assert_not_called()
        self.assertEqual(record_count, len(self._details_of_type(entries, 'license.ingest')))

    def test_does_not_load_the_license_number_index_when_no_rows_need_it(self):
        """A file made entirely of SSN-bearing rows must not pay for the index load."""
        import license_upload_without_ssn

        with patch.object(license_upload_without_ssn.config, 'data_client') as mock_data_client:
            self._process_csv([self._csv_row(ssn='123-45-6789')])

        mock_data_client.load_license_number_lookup.assert_not_called()

    def test_publishes_every_record_when_the_file_exceeds_one_batch(self):
        """The SSN-less path batches independently of the SSN path, so a large file must not drop rows."""
        record_count = 105
        rows = []
        for index in range(record_count):
            license_number = f'BULK{index:05d}'
            # each row must belong to a distinct practitioner, or the seeded records would share a
            # primary key and overwrite one another
            self._seed_existing_license(
                licenseNumber=license_number,
                providerId=str(uuid4()),
            )
            rows.append(self._csv_row(license_number=license_number))

        _, entries = self._process_csv(rows)

        self.assertEqual([], self._details_of_type(entries, 'license.validation-error'))
        self.assertEqual(record_count, len(self._details_of_type(entries, 'license.ingest')))

    # TODO - remove this test once the LICENSE_UPLOAD_WITHOUT_SSN_FLAG scaffolding is removed  # noqa: FIX002
    def test_emits_validation_error_when_the_feature_flag_is_disabled(self):
        from license_upload_without_ssn import FLAG_DISABLED_ERROR_MESSAGE

        existing_license = self._seed_existing_license()

        _, entries = self._process_csv(
            [self._csv_row(license_number=existing_license.licenseNumber)],
            flag_enabled=False,
        )

        validation_errors = self._details_of_type(entries, 'license.validation-error')
        self.assertEqual(1, len(validation_errors))
        self.assertEqual({'_schema': [FLAG_DISABLED_ERROR_MESSAGE]}, validation_errors[0]['errors'])
        self.assertEqual([], self._details_of_type(entries, 'license.ingest'))
