from unittest import TestCase
from unittest.mock import MagicMock, patch

from opensearchpy.exceptions import ConnectionTimeout, TransportError


class TestOpenSearchClient(TestCase):
    """Test suite for OpenSearchClient to verify internal client calls."""

    def _create_client_with_mock(self):
        """Create an OpenSearchClient with a mocked internal client."""
        with (
            patch('opensearch_client.boto3'),
            patch('opensearch_client.config'),
            patch('opensearch_client.OpenSearch') as mock_opensearch_class,
        ):
            mock_internal_client = MagicMock()
            mock_opensearch_class.return_value = mock_internal_client

            from opensearch_client import OpenSearchClient

            client = OpenSearchClient()
            return client, mock_internal_client

    def test_create_index_calls_internal_client_with_expected_arguments(self):
        """Test that create_index calls the internal client's indices.create method correctly."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        index_mapping = {
            'settings': {'number_of_shards': 1},
            'mappings': {'properties': {'field1': {'type': 'text'}}},
        }

        client.create_index(index_name=index_name, index_mapping=index_mapping)

        mock_internal_client.indices.create.assert_called_once_with(
            index=index_name,
            body=index_mapping,
        )

    def test_index_exists_calls_internal_client_with_expected_arguments(self):
        """Test that index_exists calls the internal client's indices.exists method correctly."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        mock_internal_client.indices.exists.return_value = True

        result = client.index_exists(index_name=index_name)

        mock_internal_client.indices.exists.assert_called_once_with(index=index_name)
        self.assertTrue(result)

    def test_search_calls_internal_client_with_expected_arguments(self):
        """Test that search calls the internal client's search method correctly."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {
            'query': {
                'match': {'givenName': 'John'},
            },
        }
        expected_response = {
            'hits': {
                'total': {'value': 1},
                'hits': [{'_source': {'givenName': 'John', 'familyName': 'Doe'}}],
            },
        }
        mock_internal_client.search.return_value = expected_response

        result = client.search(index_name=index_name, body=query_body)

        mock_internal_client.search.assert_called_once_with(
            index=index_name,
            body=query_body,
        )
        self.assertEqual(expected_response, result)

    def test_index_document_calls_internal_client_with_expected_arguments(self):
        """Test that index_document calls the internal client's index method correctly."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        document_id = 'doc-123'
        document = {'providerId': 'doc-123', 'givenName': 'John', 'familyName': 'Doe'}
        expected_response = {'_index': index_name, '_id': document_id, 'result': 'created'}
        mock_internal_client.index.return_value = expected_response

        result = client.index_document(index_name=index_name, document_id=document_id, document=document)

        mock_internal_client.index.assert_called_once_with(
            index=index_name,
            id=document_id,
            body=document,
        )
        self.assertEqual(expected_response, result)

    def test_bulk_index_calls_internal_client_with_expected_arguments(self):
        """Test that bulk_index calls the internal client's bulk method correctly."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        documents = [
            {'providerId': 'provider-1', 'givenName': 'John', 'familyName': 'Doe'},
            {'providerId': 'provider-2', 'givenName': 'Jane', 'familyName': 'Smith'},
        ]
        expected_response = {
            'errors': False,
            'items': [{'index': {'_id': 'provider-1'}}, {'index': {'_id': 'provider-2'}}],
        }
        mock_internal_client.bulk.return_value = expected_response

        result = client.bulk_index(index_name=index_name, documents=documents)

        # Verify that the bulk method is called with the index in the URL parameter
        # and NOT in the action metadata (for security compliance)
        expected_actions = [
            {'index': {'_id': 'provider-1'}},
            {'providerId': 'provider-1', 'givenName': 'John', 'familyName': 'Doe'},
            {'index': {'_id': 'provider-2'}},
            {'providerId': 'provider-2', 'givenName': 'Jane', 'familyName': 'Smith'},
        ]
        mock_internal_client.bulk.assert_called_once_with(
            body=expected_actions,
            index=index_name,
            timeout=30
        )
        self.assertEqual(expected_response, result)

    def test_bulk_index_uses_custom_id_field(self):
        """Test that bulk_index uses a custom id_field when specified."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        documents = [
            {'customId': 'custom-1', 'name': 'Document 1'},
            {'customId': 'custom-2', 'name': 'Document 2'},
        ]
        mock_internal_client.bulk.return_value = {'errors': False, 'items': []}

        client.bulk_index(index_name=index_name, documents=documents, id_field='customId')

        expected_actions = [
            {'index': {'_id': 'custom-1'}},
            {'customId': 'custom-1', 'name': 'Document 1'},
            {'index': {'_id': 'custom-2'}},
            {'customId': 'custom-2', 'name': 'Document 2'},
        ]
        mock_internal_client.bulk.assert_called_once_with(
            body=expected_actions,
            index=index_name,
            timeout=30
        )

    def test_bulk_index_returns_early_for_empty_documents(self):
        """Test that bulk_index returns early without calling the internal client for empty documents."""
        client, mock_internal_client = self._create_client_with_mock()

        result = client.bulk_index(index_name='test_index', documents=[])

        mock_internal_client.bulk.assert_not_called()
        self.assertEqual({'items': [], 'errors': False}, result)

    @patch('opensearch_client.time.sleep')
    def test_bulk_index_retries_on_connection_timeout_and_succeeds(self, mock_sleep):
        """Test that bulk_index retries on ConnectionTimeout and eventually succeeds."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        documents = [{'providerId': 'provider-1', 'givenName': 'John'}]
        expected_response = {'errors': False, 'items': [{'index': {'_id': 'provider-1'}}]}

        # First two calls fail with ConnectionTimeout, third succeeds
        mock_internal_client.bulk.side_effect = [
            ConnectionTimeout('Connection timed out', 503, 'some error'),
            ConnectionTimeout('Connection timed out', 503, 'some error'),
            expected_response,
        ]

        result = client.bulk_index(index_name=index_name, documents=documents)

        # Verify bulk was called 3 times
        self.assertEqual(3, mock_internal_client.bulk.call_count)
        # Verify sleep was called with exponential backoff (1s, 2s)
        self.assertEqual(2, mock_sleep.call_count)
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        # Verify we got the successful response
        self.assertEqual(expected_response, result)

    @patch('opensearch_client.time.sleep')
    def test_bulk_index_retries_on_transport_error_and_succeeds(self, mock_sleep):
        """Test that bulk_index retries on TransportError and eventually succeeds."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        documents = [{'providerId': 'provider-1', 'givenName': 'John'}]
        expected_response = {'errors': False, 'items': [{'index': {'_id': 'provider-1'}}]}

        # First call fails with TransportError, second succeeds
        mock_internal_client.bulk.side_effect = [
            TransportError(503, 'ReadTimeout'),
            expected_response,
        ]

        result = client.bulk_index(index_name=index_name, documents=documents)

        # Verify bulk was called 2 times
        self.assertEqual(2, mock_internal_client.bulk.call_count)
        # Verify sleep was called once
        self.assertEqual(1, mock_sleep.call_count)
        self.assertEqual(expected_response, result)

    @patch('opensearch_client.time.sleep')
    def test_bulk_index_raises_cc_internal_exception_after_max_retries(self, mock_sleep):
        """Test that bulk_index raises CCInternalException after all retry attempts fail."""
        from cc_common.exceptions import CCInternalException
        from opensearch_client import MAX_RETRY_ATTEMPTS

        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        documents = [{'providerId': 'provider-1', 'givenName': 'John'}]

        # All calls fail with ConnectionTimeout
        mock_internal_client.bulk.side_effect = ConnectionTimeout('Connection timed out', 503, 'some error')

        with self.assertRaises(CCInternalException) as context:
            client.bulk_index(index_name=index_name, documents=documents)

        # Verify bulk was called MAX_RETRY_ATTEMPTS times
        self.assertEqual(MAX_RETRY_ATTEMPTS, mock_internal_client.bulk.call_count)
        # Verify sleep was called MAX_RETRY_ATTEMPTS - 1 times (no sleep after last failure)
        self.assertEqual(MAX_RETRY_ATTEMPTS - 1, mock_sleep.call_count)
        # Verify the exception message contains useful info
        self.assertIn('Failed to bulk index', str(context.exception))
        self.assertIn(index_name, str(context.exception))
        self.assertIn(str(MAX_RETRY_ATTEMPTS), str(context.exception))

    @patch('opensearch_client.time.sleep')
    def test_bulk_index_exponential_backoff_caps_at_max(self, mock_sleep):
        """Test that exponential backoff is capped at MAX_BACKOFF_SECONDS."""
        from opensearch_client import MAX_BACKOFF_SECONDS

        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        documents = [{'providerId': 'provider-1', 'givenName': 'John'}]

        # All calls fail
        mock_internal_client.bulk.side_effect = ConnectionTimeout('Connection timed out', 503, 'some error')

        with self.assertRaises(Exception):
            client.bulk_index(index_name=index_name, documents=documents)

        # Verify backoff values: 1, 2, 4, 8 (all should be <= MAX_BACKOFF_SECONDS)
        # With MAX_RETRY_ATTEMPTS = 5, we have 4 sleeps
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        for sleep_value in sleep_calls:
            self.assertLessEqual(sleep_value, MAX_BACKOFF_SECONDS)
