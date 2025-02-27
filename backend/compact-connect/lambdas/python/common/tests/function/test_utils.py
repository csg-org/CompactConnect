import json
from unittest.mock import patch

from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class TestUtils(TstFunction):
    def test_send_licenses_to_preprocessing_queue_handles_batches(self):
        from cc_common.utils import send_licenses_to_preprocessing_queue

        with open('tests/resources/api/license-post.json') as f:
            license_record = json.load(f)
            license_record['compact'] = 'aslp'
            license_record['jurisdiction'] = 'oh'

        # generate 100 records and ensure the system processes all of them.
        licenses_data = [license_record] * 100

        failed_license_numbers = send_licenses_to_preprocessing_queue(
            licenses_data=licenses_data, event_time='2024-12-04T08:08:08+00:00'
        )

        self.assertEqual([], failed_license_numbers)

        # now get all the messages and make sure all ids are in the list
        # we can only get 10 messages at a time, so we iterate over the range and get all the messages
        messages = []
        for _i in range(10):
            messages.extend(self._license_preprocessing_queue.receive_messages(MaxNumberOfMessages=10))

        self.assertEqual(100, len(messages))

    @patch('cc_common.config._Config.license_preprocessing_queue')
    def test_send_licenses_to_preprocessing_queue_handles_failures(self, mock_preprocessing_queue):
        from cc_common.utils import send_licenses_to_preprocessing_queue

        def mock_send_messages(Entries):  # noqa N803 AWS defines the kwargs
            failed_entries = [
                {'Id': entry['Id'], 'SenderFault': False, 'Code': '1234', 'Message': 'Something went wrong'}
                for entry in Entries
            ]
            return {'Successful': [], 'Failed': failed_entries}

        # we have to mock the SQS queue to force a failure scenario
        mock_preprocessing_queue.send_messages.side_effect = mock_send_messages

        with open('tests/resources/api/license-post.json') as f:
            license_record = json.load(f)
            license_record['compact'] = 'aslp'
            license_record['jurisdiction'] = 'oh'

        # generate 5 records and ensure the system processes all the failures
        licenses_data = []
        for i in range(6):
            with open('tests/resources/api/license-post.json') as f:
                license_record = json.load(f)
                license_record['compact'] = 'aslp'
                license_record['jurisdiction'] = 'oh'
                license_record['licenseNumber'] = f'licenseNumber-{i}'
                licenses_data.append(license_record)

        failed_license_numbers = send_licenses_to_preprocessing_queue(
            licenses_data=licenses_data, event_time='2024-12-04T08:08:08+00:00'
        )

        self.assertEqual([f'licenseNumber-{i}' for i in range(6)], failed_license_numbers)
