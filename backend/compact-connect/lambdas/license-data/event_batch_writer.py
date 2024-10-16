from botocore.client import BaseClient


class EventBatchWriter:
    """Utility class to batch event bridge event puts for better efficiency with the AWS EventBridge API"""

    def __init__(self, client: BaseClient, batch_size: int = 10):
        """:param BaseClient client: A boto3 EventBridge client to use for API calls
        :param int batch_size: Batch size to use for API calls, default: 10
        """
        self._client = client
        self._batch_size = batch_size
        self._batch = None
        self._count = 0
        self.failed_entry_count = 0
        self.failed_entries = None

    def _do_put(self):
        resp = self._client.put_events(Entries=self._batch)
        failure_count = resp.get('FailedEntryCount', 0)
        if failure_count > 0:
            self.failed_entry_count += failure_count
            self.failed_entries.extend(entry for entry in resp.get('Entries') if entry.get('ErrorCode'))
        self._batch = []
        self._count = 0

    def __enter__(self):
        self._batch = []
        self._count = 0
        self.failed_entries = []
        self.failed_entry_count = 0
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        # We'll check the actual batch length, instead of count here,
        # just to be a bit defensive in the case that we mess up the counter.
        if len(self._batch) > 0:
            self._do_put()
        if exc_val is not None:
            raise exc_val

    def put_event(self, Entry: dict):  # noqa: N803 invalid-name
        if self._batch is None:
            # Protecting ourselves from accidental misuse
            raise RuntimeError('This object must be used as a context manager')
        self._batch.append(Entry)
        self._count += 1
        if self._count >= self._batch_size:
            self._do_put()
