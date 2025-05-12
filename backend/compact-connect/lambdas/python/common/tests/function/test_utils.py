import json

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
