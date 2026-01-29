import json
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import patch

from botocore.exceptions import ClientError
from botocore.response import StreamingBody

from tests import TstLambdas


class TestProcessS3Event(TstLambdas):
    @patch('handlers.bulk_upload.process_bulk_upload_file', autospec=True)
    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.bulk_upload.config', autospec=False)
    def test_process_s3_event(self, mock_config, mock_process):
        from handlers.bulk_upload import parse_bulk_upload_file

        mock_config.s3_client.get_object.response = {'Body': StreamingBody(b'foo', '3')}

        mock_process.return_value = None

        with open('../common/tests/resources/put-event.json') as f:
            event = json.load(f)

        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        parse_bulk_upload_file(event, self.mock_context)

        # Happy-path execution should always end with the object being deleted
        mock_config.s3_client.delete_object.assert_called_with(Bucket=bucket, Key=key)

        # Verify that we didn't go into exception handling and put a failure event
        mock_config.events_client.put_events.assert_not_called()

    @patch('handlers.bulk_upload.process_bulk_upload_file', autospec=True)
    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.bulk_upload.config', autospec=False)
    def test_internal_exception(self, mock_config, mock_process):
        from handlers.bulk_upload import parse_bulk_upload_file

        mock_config.s3_client.get_object.response = {'Body': StreamingBody(b'foo', '3')}

        # What if we've misconfigured something, so we can't access an AWS resource?
        mock_process.side_effect = ClientError(
            error_response={'Error': {'Code': 'AccessDeniedError'}},
            operation_name='DoAWSThing',
        )

        with open('../common/tests/resources/put-event.json') as f:
            event = json.load(f)

        with self.assertRaises(ClientError):
            parse_bulk_upload_file(event, self.mock_context)

        # We should not delete the object, as we failed to process it
        mock_config.s3_client.delete_object.assert_not_called()

        # Because this failure is our problem we won't send a failure event, which is intended
        # to indicate a problem with the actual data
        mock_config.events_client.put_events.assert_not_called()

    @patch('handlers.bulk_upload.process_bulk_upload_file', autospec=True)
    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.bulk_upload.config', autospec=False)
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

        with open('../common/tests/resources/put-event.json') as f:
            event = json.load(f)

        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        parse_bulk_upload_file(event, self.mock_context)

        # We should delete the object, as it contains invalid data
        mock_config.s3_client.delete_object.assert_called_with(Bucket=bucket, Key=key)

        # Because this was a failure due to invalid data, we will fire a failure event
        mock_config.events_client.put_events.assert_called_once()


class TestProcessBulkUploadFile(TstLambdas):
    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.bulk_upload.send_licenses_to_preprocessing_queue')
    def test_good_data(self, mock_send_licenses_to_preprocessing_queue):
        from handlers.bulk_upload import process_bulk_upload_file

        # this method returns a list of any message ids that failed to send, in this test case, there are no failures
        mock_send_licenses_to_preprocessing_queue.return_value = []

        with open('../common/tests/resources/licenses.csv', 'rb') as f:
            line_count = len(f.readlines())
            f.seek(0)
            content_length = len(f.read())
            f.seek(0)

            stream = StreamingBody(f, content_length)

            process_bulk_upload_file(
                event_time=datetime.now(tz=UTC),
                body=stream,
                object_key='cosm/oh/1234',
                compact='cosm',
                jurisdiction='oh',
            )

        # Collect events sent to SQS for inspection

        # There should only be successful ingest events
        entries = [
            entry
            for call in mock_send_licenses_to_preprocessing_queue.call_args_list
            for entry in call.kwargs['licenses_data']
        ]
        # Make sure we put the right number of events on the queue
        self.assertEqual(line_count - 1, len(entries))

    # We can't autospec because it causes the patch to evaluate properties that look up environment variables that we
    # don't intend to set for these tests.
    @patch('handlers.bulk_upload.config', autospec=False)
    @patch('handlers.bulk_upload.send_licenses_to_preprocessing_queue')
    def test_bad_data(self, mock_send_licenses_to_preprocessing_queue, mock_config):
        from handlers.bulk_upload import process_bulk_upload_file

        # mock static response for the events client when we put messages on the event bus
        mock_config.events_client.put_events.return_value = {'FailedEntryCount': 0, 'Entries': [{'EventId': '123'}]}
        # this method returns a list of any message ids that failed to send, in this test case, there are no failures
        mock_send_licenses_to_preprocessing_queue.return_value = []

        # We'll do a little processing to mangle our CSV data a bit
        with open('../common/tests/resources/licenses.csv') as f:
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
            object_key='cosm/oh/1234',
            compact='cosm',
            jurisdiction='oh',
        )

        # Collect events put for validation failures
        # There should be two failures
        event_writer_entries = [
            entry for call in mock_config.events_client.put_events.call_args_list for entry in call.kwargs['Entries']
        ]
        self.assertEqual(
            2, len([entry for entry in event_writer_entries if entry['DetailType'] == 'license.validation-error'])
        )

        # Make sure we're capturing _some_ valid data from the license for feedback
        bad_ssn_event_details = json.loads(event_writer_entries[0]['Detail'])
        self.assertIn('familyName', bad_ssn_event_details['validData'].keys())

        bad_license_type_details = json.loads(event_writer_entries[1]['Detail'])
        self.assertIn('dateOfIssuance', bad_license_type_details['validData'])
        # Make sure we don't include sensitive data in these events
        self.assertNotIn('ssn', bad_license_type_details['validData'])

        # Now we collect how many entries were sent to SQS
        # there should be three successful messages
        preprocessor_entries = [
            entry
            for call in mock_send_licenses_to_preprocessing_queue.call_args_list
            for entry in call.kwargs['licenses_data']
        ]
        # the payload contract for these messages is covered in other tests, so we just check that the expected
        # number of messages was sent
        self.assertEqual(3, len(preprocessor_entries))
