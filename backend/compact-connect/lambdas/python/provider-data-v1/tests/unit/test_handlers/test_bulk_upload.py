import json
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import patch

from botocore.exceptions import ClientError
from botocore.response import StreamingBody

from tests import TstLambdas


class TestProcessS3Event(TstLambdas):
    @patch('handlers.bulk_upload.process_bulk_upload_file', autospec=True)
    @patch('handlers.bulk_upload.config', autospec=True)
    def test_process_s3_event(self, mock_config, mock_process):
        from handlers.bulk_upload import parse_bulk_upload_file

        mock_config.s3_client.get_object.response = {'Body': StreamingBody(b'foo', '3')}

        mock_process.return_value = None

        with open('tests/resources/put-event.json') as f:
            event = json.load(f)

        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        parse_bulk_upload_file(event, self.mock_context)

        # Happy-path execution should always end with the object being deleted
        mock_config.s3_client.delete_object.assert_called_with(Bucket=bucket, Key=key)

        # Verify that we didn't go into exception handling and put a failure event
        mock_config.events_client.put_events.assert_not_called()

    @patch('handlers.bulk_upload.process_bulk_upload_file', autospec=True)
    @patch('handlers.bulk_upload.config', autospec=True)
    def test_internal_exception(self, mock_config, mock_process):
        from handlers.bulk_upload import parse_bulk_upload_file

        mock_config.s3_client.get_object.response = {'Body': StreamingBody(b'foo', '3')}

        # What if we've misconfigured something, so we can't access an AWS resource?
        mock_process.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDeniedError'}},
            operation_name='DoAWSThing',
        )

        with open('tests/resources/put-event.json') as f:
            event = json.load(f)

        with self.assertRaises(ClientError):
            parse_bulk_upload_file(event, self.mock_context)

        # We should not delete the object, as we failed to process it
        mock_config.s3_client.delete_object.assert_not_called()

        # Because this failure is our problem we won't send a failure event, which is intended
        # to indicate a problem with the actual data
        mock_config.events_client.put_events.assert_not_called()

    @patch('handlers.bulk_upload.process_bulk_upload_file', autospec=True)
    @patch('handlers.bulk_upload.config', autospec=True)
    def test_bad_data(self, mock_config, mock_process):
        from handlers.bulk_upload import parse_bulk_upload_file

        mock_config.s3_client.get_object.response = {'Body': StreamingBody(b'foo', '3')}
        mock_config.events_client.put_events.return_value = {'FailedEntryCount': 0, 'Entries': [{'EventId': '123'}]}

        # Force a UnicodeDecodeError to reuse
        error = None
        not_unicode = b'\x83'
        try:
            not_unicode.decode('utf-8')
        except UnicodeDecodeError as e:
            error = e

        # What if the uploaded file is not properly utf-8 encoded?
        mock_process.side_effect = error

        with open('tests/resources/put-event.json') as f:
            event = json.load(f)

        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        parse_bulk_upload_file(event, self.mock_context)

        # We should delete the object, as it contains invalid data
        mock_config.s3_client.delete_object.assert_called_with(Bucket=bucket, Key=key)

        # Because this was a failure due to invalid data, we will fire a failure event
        mock_config.events_client.put_events.assert_called_once()


class TestProcessBulkUploadFile(TstLambdas):
    @patch('handlers.bulk_upload.config', autospec=True)
    def test_good_data(self, mock_config):
        from handlers.bulk_upload import process_bulk_upload_file

        mock_config.events_client.put_events.return_value = {'FailedEntryCount': 0, 'Entries': [{'EventId': '123'}]}

        with open('tests/resources/licenses.csv', 'rb') as f:
            line_count = len(f.readlines())
            f.seek(0)
            content_length = len(f.read())
            f.seek(0)

            stream = StreamingBody(f, content_length)

            process_bulk_upload_file(
                event_time=datetime.now(tz=UTC),
                body=stream,
                object_key='aslp/oh/1234',
                compact='aslp',
                jurisdiction='oh',
            )

        # Collect events put for inspection
        detail_types = {
            entry['DetailType']
            for call in mock_config.events_client.put_events.call_args_list
            for entry in call.kwargs['Entries']
        }
        # There should only be successful ingest events
        self.assertEqual({'license.ingest'}, detail_types)
        entries = [
            entry for call in mock_config.events_client.put_events.call_args_list for entry in call.kwargs['Entries']
        ]
        # Make sure we published the right number of events
        self.assertEqual(line_count - 1, len(entries))

    @patch('handlers.bulk_upload.config', autospec=True)
    def test_bad_data(self, mock_config):
        from handlers.bulk_upload import process_bulk_upload_file

        mock_config.events_client.put_events.return_value = {'FailedEntryCount': 0, 'Entries': [{'EventId': '123'}]}

        # We'll do a little processing to mangle our CSV data a bit
        with open('tests/resources/licenses.csv') as f:
            line_count = len(f.readlines())
            f.seek(0)
            csv_data = [line.split(',') for line in f]
        # SSN of line 3
        csv_data[2][8] = '1234'
        # License type of line 5
        csv_data[4][3] = ''

        mangled_rows = [','.join(row) for row in csv_data]
        mangled_data = '\n'.join(mangled_rows).encode('utf-8')
        content_length = len(mangled_data)

        stream = StreamingBody(BytesIO(mangled_data), content_length)

        process_bulk_upload_file(
            event_time=datetime.now(tz=UTC),
            body=stream,
            object_key='aslp/oh/1234',
            compact='aslp',
            jurisdiction='oh',
        )

        # Collect events put for inspection
        # There should be three successful ingest events and two failures
        entries = [
            entry for call in mock_config.events_client.put_events.call_args_list for entry in call.kwargs['Entries']
        ]
        self.assertEqual(line_count - 1, len(entries))
        self.assertEqual(2, len([entry for entry in entries if entry['DetailType'] == 'license.validation-error']))
        self.assertEqual(line_count - 3, len([entry for entry in entries if entry['DetailType'] == 'license.ingest']))

        # Make sure we're capturing _some_ valid data from the license for feedback
        bad_ssn_event_details = json.loads(entries[1]['Detail'])
        self.assertIn('familyName', bad_ssn_event_details['validData'].keys())

        bad_license_type_details = json.loads(entries[3]['Detail'])
        self.assertIn('dateOfIssuance', bad_license_type_details['validData'])
        # Make sure we don't include sensitive data in these events
        self.assertNotIn('ssn', bad_license_type_details['validData'])
