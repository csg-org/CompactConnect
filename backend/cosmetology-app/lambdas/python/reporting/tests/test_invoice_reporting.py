import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPORTING_ROOT = Path(__file__).resolve().parents[1]
COMMON_ROOT = REPORTING_ROOT.parents[0] / 'common'
sys.path.insert(0, str(REPORTING_ROOT))
sys.path.insert(0, str(COMMON_ROOT))

from cc_common.exceptions import CCInternalException  # noqa: E402
from handlers import invoice_reporting  # noqa: E402


class TestBatchGetLicenses(unittest.TestCase):
    def setUp(self):
        os.environ['PROVIDER_TABLE_NAME'] = 'provider-table'

    def test_retries_unprocessed_keys_and_keeps_records_already_fetched(self):
        keys = [{'pk': 'a', 'sk': '1'}]
        responses = [
            {
                'Responses': {'provider-table': [{'pk': 'a', 'sk': '1'}]},
                'UnprocessedKeys': {'provider-table': {'Keys': keys}},
            },
            {'Responses': {'provider-table': [{'pk': 'b', 'sk': '2'}]}, 'UnprocessedKeys': {}},
        ]

        with (
            patch.object(invoice_reporting.time, 'sleep') as sleep,
            patch.object(invoice_reporting.boto3, 'resource') as resource,
        ):
            resource.return_value.batch_get_item.side_effect = responses
            records = invoice_reporting._batch_get_licenses(keys)  # noqa: SLF001

        self.assertEqual([{'pk': 'a', 'sk': '1'}, {'pk': 'b', 'sk': '2'}], records)
        sleep.assert_called_once_with(invoice_reporting.UNPROCESSED_BASE_SLEEP_SECONDS)
        retried = resource.return_value.batch_get_item.call_args_list[1].kwargs['RequestItems']
        retried_keys = retried['provider-table']['Keys']
        self.assertEqual(keys, retried_keys)

    def test_fails_before_a_partial_invoice_when_keys_stay_unprocessed(self):
        keys = [{'pk': 'a', 'sk': '1'}]
        stuck = {
            'Responses': {'provider-table': []},
            'UnprocessedKeys': {'provider-table': {'Keys': keys}},
        }

        with (
            patch.object(invoice_reporting.time, 'sleep') as sleep,
            patch.object(invoice_reporting.boto3, 'resource') as resource,
        ):
            resource.return_value.batch_get_item.return_value = stuck
            with self.assertRaises(CCInternalException):
                invoice_reporting._batch_get_licenses(keys)  # noqa: SLF001

        # One request plus one retry for each allowed attempt.
        self.assertEqual(invoice_reporting.MAX_UNPROCESSED_RETRIES + 1, resource.return_value.batch_get_item.call_count)
        self.assertEqual(invoice_reporting.MAX_UNPROCESSED_RETRIES, sleep.call_count)
