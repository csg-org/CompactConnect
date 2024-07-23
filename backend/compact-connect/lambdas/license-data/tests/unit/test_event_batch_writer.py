import json
from typing import List
from unittest.mock import MagicMock
from uuid import uuid4

from botocore.exceptions import ParamValidationError

from tests import TstLambdas


class TestEventBatchWriter(TstLambdas):
    def test_write_big_batch(self):
        from event_batch_writer import EventBatchWriter

        put_count = []

        def mock_put_items(Entries: List[dict]):  # pylint: disable=invalid-name
            put_count.extend(Entries)
            return {}

        mock_client = MagicMock()
        mock_client.put_events.side_effect = mock_put_items

        with open('tests/resources/ingest/message.json', 'r') as f:
            event = json.load(f)

        with EventBatchWriter(client=mock_client) as writer:
            # Send a bunch of messages, make sure each is sent
            for _ in range(123):
                writer.put_event(
                    Entry=event
                )

        # Make sure each message was eventually sent
        self.assertEqual(123, len(put_count))
        # Make sure these were sent in three batches
        self.assertEqual(13, mock_client.put_events.call_count)

    def test_write_small_batch(self):
        from event_batch_writer import EventBatchWriter

        put_count = []

        def mock_put_items(Entries: List[dict]):  # pylint: disable=invalid-name
            put_count.extend(Entries)
            return {}

        mock_client = MagicMock()
        mock_client.put_events.side_effect = mock_put_items

        with open('tests/resources/ingest/message.json', 'r') as f:
            event = json.load(f)

        with EventBatchWriter(client=mock_client) as writer:
            # Send a bunch of messages, make sure each is sent
            for _ in range(3):
                writer.put_event(
                    Entry=event
                )

        # Make sure each message was eventually sent
        self.assertEqual(3, len(put_count))
        # Make sure these were sent in one batch
        self.assertEqual(1, mock_client.put_events.call_count)

    def test_write_batch(self):
        """
        Making sure that, in the event that we exit with exactly 0 messages remaining, we don't try
        to put an empty batch
        """
        from event_batch_writer import EventBatchWriter

        put_count = []

        def mock_put_items(Entries: List[dict]):  # pylint: disable=invalid-name
            if len(Entries) < 1:
                raise ParamValidationError(report='Invalid length for parameter Entries, value: 0, valid min length: 1')
            put_count.extend(Entries)
            return {}

        mock_client = MagicMock()
        mock_client.put_events.side_effect = mock_put_items

        with open('tests/resources/ingest/message.json', 'r') as f:
            event = json.load(f)

        with EventBatchWriter(client=mock_client) as writer:
            # Send a bunch of messages, make sure each is sent
            for _ in range(10):
                writer.put_event(
                    Entry=event
                )

        # Make sure each message was eventually sent
        self.assertEqual(10, len(put_count))
        # Make sure these were sent in one batch
        self.assertEqual(1, mock_client.put_events.call_count)

    def test_exception_recovery(self):
        from event_batch_writer import EventBatchWriter

        put_count = []

        def mock_put_items(Entries: List[dict]):  # pylint: disable=invalid-name
            put_count.extend(Entries)
            return {}

        mock_client = MagicMock()
        mock_client.put_events.side_effect = mock_put_items

        with open('tests/resources/ingest/message.json', 'r') as f:
            event = json.load(f)

        def interrupted_with_exception():
            with EventBatchWriter(client=mock_client) as writer:
                # Send a bunch of messages, make sure each is sent
                for _ in range(3):
                    writer.put_event(
                        Entry=event
                    )
                raise RuntimeError('Oh noes!')

        # Make sure the exception is not suppressed
        with self.assertRaises(RuntimeError):
            interrupted_with_exception()

        # Make sure each message was eventually sent
        self.assertEqual(3, len(put_count))
        # Make sure these were sent in one batch
        self.assertEqual(1, mock_client.put_events.call_count)

    def test_bad_use(self):
        from event_batch_writer import EventBatchWriter

        # If a developer uses this wrong
        writer = EventBatchWriter(MagicMock())
        with self.assertRaises(RuntimeError):
            writer.put_event(Entry={})

    def test_entry_failures(self):
        from event_batch_writer import EventBatchWriter

        put_count = []

        def mock_put_items(Entries: List[dict]):  # pylint: disable=invalid-name
            """
            Fail every last entry
            """
            put_count.extend(Entries)
            response = {
                'FailedEntryCount': 1,
                'Entries': [
                    {'EventId': uuid4().hex}
                    for entry in Entries[:-1]
                ]
            }
            response['Entries'].append({
                'EventId': uuid4().hex,
                'ErrorCode': 'InternalFailure',
                'ErrorMessage': 'Oh no, AWS is having problems!'
            })
            return response

        mock_client = MagicMock()
        mock_client.put_events.side_effect = mock_put_items

        with open('tests/resources/ingest/message.json', 'r') as f:
            event = json.load(f)

        with EventBatchWriter(client=mock_client) as writer:
            # Send a bunch of messages, make sure each is sent
            for _ in range(123):
                writer.put_event(
                    Entry=event
                )

        self.assertEqual(123, len(put_count))
        # 13 batches, one failure each
        self.assertEqual(13, writer.failed_entry_count)
        self.assertEqual(13, len(writer.failed_entries))
