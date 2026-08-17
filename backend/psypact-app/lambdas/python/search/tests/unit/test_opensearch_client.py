# ruff: noqa ARG002 unused-argument
from unittest import TestCase
from unittest.mock import MagicMock, patch

from opensearchpy.exceptions import ConnectionTimeout, RequestError, TransportError


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

    def test_alias_exists_calls_internal_client_with_expected_arguments(self):
        """Test that alias_exists calls the internal client's indices.exists_alias method correctly."""
        client, mock_internal_client = self._create_client_with_mock()

        alias_name = 'test_alias'
        mock_internal_client.indices.exists_alias.return_value = True

        result = client.alias_exists(alias_name=alias_name)

        mock_internal_client.indices.exists_alias.assert_called_once_with(name=alias_name)
        self.assertTrue(result)

    def test_alias_exists_returns_false_when_alias_does_not_exist(self):
        """Test that alias_exists returns False when the alias does not exist."""
        client, mock_internal_client = self._create_client_with_mock()

        alias_name = 'nonexistent_alias'
        mock_internal_client.indices.exists_alias.return_value = False

        result = client.alias_exists(alias_name=alias_name)

        mock_internal_client.indices.exists_alias.assert_called_once_with(name=alias_name)
        self.assertFalse(result)

    def test_create_alias_calls_internal_client_with_expected_arguments(self):
        """Test that create_alias calls the internal client's indices.put_alias method correctly."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index_v1'
        alias_name = 'test_alias'

        client.create_alias(index_name=index_name, alias_name=alias_name)

        mock_internal_client.indices.put_alias.assert_called_once_with(index=index_name, name=alias_name)

    def test_get_index_settings_calls_internal_client_with_expected_arguments(self):
        """Test that get_index_settings calls the internal client's indices.get_settings method correctly."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        expected_response = {
            'test_index_v1': {
                'settings': {
                    'index': {
                        'number_of_replicas': '1',
                        'number_of_shards': '1',
                    }
                }
            }
        }
        mock_internal_client.indices.get_settings.return_value = expected_response

        result = client.get_index_settings(index_name=index_name)

        mock_internal_client.indices.get_settings.assert_called_once_with(index=index_name)
        self.assertEqual(expected_response, result)

    def test_update_index_settings_calls_internal_client_with_expected_arguments(self):
        """Test that update_index_settings calls the internal client's indices.put_settings method correctly."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        settings = {'index': {'number_of_replicas': 1}}

        client.update_index_settings(index_name=index_name, settings=settings)

        mock_internal_client.indices.put_settings.assert_called_once_with(index=index_name, body=settings)

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

        mock_internal_client.search.assert_called_once_with(index=index_name, body=query_body)
        self.assertEqual(expected_response, result)

    def test_search_raises_cc_invalid_request_exception_on_400_request_error(self):
        """Test that search raises CCInvalidRequestException when OpenSearch returns a 400 RequestError."""
        from cc_common.exceptions import CCInvalidRequestException

        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {'query': {'match_all': {}}, 'sort': [{'familyName': 'asc'}]}

        # Simulate OpenSearch returning a 400 error with realistic error structure
        error_reason = (
            'Text fields are not optimised for operations that require per-document field data '
            'like aggregations and sorting, so these operations are disabled by default.'
        )
        error_info = {
            'error': {
                'root_cause': [
                    {
                        'type': 'illegal_argument_exception',
                        'reason': error_reason,
                    }
                ],
                'type': 'search_phase_execution_exception',
                'reason': 'all shards failed',
            },
            'status': 400,
        }
        mock_internal_client.search.side_effect = RequestError(400, 'search_phase_execution_exception', error_info)

        with self.assertRaises(CCInvalidRequestException) as context:
            client.search(index_name=index_name, body=query_body)

        # Verify the exception message extracts the reason from root_cause
        self.assertEqual(
            f'Invalid search query: {error_reason}',
            str(context.exception),
        )

    def test_search_raises_cc_invalid_request_exception_with_fallback_on_missing_root_cause(self):
        """Test that search falls back to error type when root_cause is missing."""
        from cc_common.exceptions import CCInvalidRequestException

        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {'query': {'match_all': {}}}

        # Simulate OpenSearch returning a 400 error without root_cause structure
        mock_internal_client.search.side_effect = RequestError(400, 'parsing_exception', None)

        with self.assertRaises(CCInvalidRequestException) as context:
            client.search(index_name=index_name, body=query_body)

        # Verify the exception falls back to the error type
        self.assertEqual(
            'Invalid search query: parsing_exception',
            str(context.exception),
        )

    def test_search_reraises_non_400_request_error(self):
        """Test that search re-raises RequestError for non-400 status codes."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {'query': {'match_all': {}}}

        # Simulate OpenSearch returning a 500 error
        mock_internal_client.search.side_effect = RequestError(500, 'internal_error', 'Something went wrong')

        with self.assertRaises(RequestError) as context:
            client.search(index_name=index_name, body=query_body)

        self.assertEqual(500, context.exception.status_code)

    def test_search_raises_cc_invalid_request_exception_on_timeout(self):
        """Test that search raises CCInvalidRequestException when the request times out."""
        from cc_common.exceptions import CCInvalidRequestException

        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {'query': {'match_all': {}}}

        # Simulate OpenSearch timing out
        mock_internal_client.search.side_effect = ConnectionTimeout('Connection timed out', 503, 'Read timed out')

        with self.assertRaises(CCInvalidRequestException) as context:
            client.search(index_name=index_name, body=query_body)

        # Verify the exception message tells the user to try again
        self.assertEqual(
            'Search request timed out. Please try again or narrow your search criteria.',
            str(context.exception),
        )

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

        expected_actions = [
            {'index': {'_id': 'provider-1'}},
            {'providerId': 'provider-1', 'givenName': 'John', 'familyName': 'Doe'},
            {'index': {'_id': 'provider-2'}},
            {'providerId': 'provider-2', 'givenName': 'Jane', 'familyName': 'Smith'},
        ]
        mock_internal_client.bulk.assert_called_once_with(body=expected_actions, index=index_name)
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
        mock_internal_client.bulk.assert_called_once_with(body=expected_actions, index=index_name)

    def test_bulk_index_returns_early_for_empty_documents(self):
        """Test that bulk_index returns early without calling the internal client for empty documents."""
        client, mock_internal_client = self._create_client_with_mock()

        result = client.bulk_index(index_name='test_index', documents=[])

        mock_internal_client.bulk.assert_not_called()
        self.assertEqual({'items': [], 'errors': False}, result)

    @patch('opensearch_client.time.sleep')
    def test_bulk_index_retries_on_connection_timeout_and_succeeds(self, mock_sleep):
        """Test that bulk_index retries on ConnectionTimeout and eventually succeeds."""
        from opensearch_client import INITIAL_BACKOFF_SECONDS

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
        # Verify sleep was called with exponential backoff
        self.assertEqual(2, mock_sleep.call_count)
        mock_sleep.assert_any_call(INITIAL_BACKOFF_SECONDS)
        mock_sleep.assert_any_call(INITIAL_BACKOFF_SECONDS * 2)
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
        from cc_common.exceptions import CCInternalException
        from opensearch_client import MAX_BACKOFF_SECONDS

        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        documents = [{'providerId': 'provider-1', 'givenName': 'John'}]

        # All calls fail
        mock_internal_client.bulk.side_effect = ConnectionTimeout('Connection timed out', 503, 'some error')

        with self.assertRaises(CCInternalException):
            client.bulk_index(index_name=index_name, documents=documents)

        # Verify backoff values: 2, 4, 8, 16 (all should be <= MAX_BACKOFF_SECONDS)
        # With MAX_RETRY_ATTEMPTS = 5, we have 4 sleeps
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        for sleep_value in sleep_calls:
            self.assertLessEqual(sleep_value, MAX_BACKOFF_SECONDS)


class TestOpenSearchClientIndexManagementRetry(TestCase):
    """Test suite for OpenSearchClient index management operations with retry logic."""

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

    @patch('opensearch_client.time.sleep')
    def test_create_index_retries_on_connection_timeout_and_succeeds(self, mock_sleep):
        """Test that create_index retries on ConnectionTimeout and eventually succeeds."""
        from opensearch_client import INITIAL_BACKOFF_SECONDS

        client, mock_internal_client = self._create_client_with_mock()

        # First call fails, second succeeds
        mock_internal_client.indices.create.side_effect = [
            ConnectionTimeout('Connection timed out', 503, 'some error'),
            {'acknowledged': True},
        ]

        # Should not raise
        client.create_index(index_name='test_index', index_mapping={'settings': {}})

        # Verify create was called 2 times
        self.assertEqual(2, mock_internal_client.indices.create.call_count)
        # Verify sleep was called once
        self.assertEqual(1, mock_sleep.call_count)
        mock_sleep.assert_called_with(INITIAL_BACKOFF_SECONDS)

    @patch('opensearch_client.time.sleep')
    def test_create_index_raises_after_max_retries(self, mock_sleep):
        """Test that create_index raises CCInternalException after max retries."""
        from cc_common.exceptions import CCInternalException
        from opensearch_client import MAX_RETRY_ATTEMPTS

        client, mock_internal_client = self._create_client_with_mock()

        # All calls fail
        mock_internal_client.indices.create.side_effect = ConnectionTimeout('Connection timed out', 503, 'some error')

        with self.assertRaises(CCInternalException) as context:
            client.create_index(index_name='test_index', index_mapping={'settings': {}})

        # Verify create was called MAX_RETRY_ATTEMPTS times
        self.assertEqual(MAX_RETRY_ATTEMPTS, mock_internal_client.indices.create.call_count)
        self.assertIn('create_index', str(context.exception))

    @patch('opensearch_client.time.sleep')
    def test_index_exists_retries_on_transport_error_and_succeeds(self, mock_sleep):
        """Test that index_exists retries on TransportError and eventually succeeds."""
        client, mock_internal_client = self._create_client_with_mock()

        # First call fails, second succeeds
        mock_internal_client.indices.exists.side_effect = [
            TransportError(503, 'ReadTimeout'),
            True,
        ]

        result = client.index_exists(index_name='test_index')

        self.assertTrue(result)
        self.assertEqual(2, mock_internal_client.indices.exists.call_count)

    @patch('opensearch_client.time.sleep')
    def test_alias_exists_retries_on_connection_timeout_and_succeeds(self, mock_sleep):
        """Test that alias_exists retries on ConnectionTimeout and eventually succeeds."""
        client, mock_internal_client = self._create_client_with_mock()

        # First call fails, second succeeds
        mock_internal_client.indices.exists_alias.side_effect = [
            ConnectionTimeout('Connection timed out', 503, 'some error'),
            True,
        ]

        result = client.alias_exists(alias_name='test_alias')

        self.assertTrue(result)
        self.assertEqual(2, mock_internal_client.indices.exists_alias.call_count)

    @patch('opensearch_client.time.sleep')
    def test_create_alias_retries_on_connection_timeout_and_succeeds(self, mock_sleep):
        """Test that create_alias retries on ConnectionTimeout and eventually succeeds."""
        client, mock_internal_client = self._create_client_with_mock()

        # First call fails, second succeeds
        mock_internal_client.indices.put_alias.side_effect = [
            ConnectionTimeout('Connection timed out', 503, 'some error'),
            {'acknowledged': True},
        ]

        # Should not raise
        client.create_alias(index_name='test_index', alias_name='test_alias')

        self.assertEqual(2, mock_internal_client.indices.put_alias.call_count)

    @patch('opensearch_client.time.sleep')
    def test_cluster_health_retries_on_connection_timeout_and_succeeds(self, mock_sleep):
        """Test that cluster_health retries on ConnectionTimeout and eventually succeeds."""
        client, mock_internal_client = self._create_client_with_mock()

        expected_response = {'status': 'green', 'number_of_nodes': 3}

        # First call fails, second succeeds
        mock_internal_client.cluster.health.side_effect = [
            ConnectionTimeout('Connection timed out', 503, 'some error'),
            expected_response,
        ]

        result = client.cluster_health()

        self.assertEqual(expected_response, result)
        self.assertEqual(2, mock_internal_client.cluster.health.call_count)

    @patch('opensearch_client.time.sleep')
    def test_cluster_health_raises_after_max_retries(self, mock_sleep):
        """Test that cluster_health raises CCInternalException after max retries."""
        from cc_common.exceptions import CCInternalException
        from opensearch_client import MAX_RETRY_ATTEMPTS

        client, mock_internal_client = self._create_client_with_mock()

        # All calls fail
        mock_internal_client.cluster.health.side_effect = ConnectionTimeout('Connection timed out', 503, 'some error')

        with self.assertRaises(CCInternalException) as context:
            client.cluster_health()

        # Verify health was called MAX_RETRY_ATTEMPTS times
        self.assertEqual(MAX_RETRY_ATTEMPTS, mock_internal_client.cluster.health.call_count)
        self.assertIn('cluster_health', str(context.exception))


class TestOpenSearchClientSearchWithRetry(TestCase):
    """Test suite for OpenSearchClient.search_with_retry method."""

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

    def test_search_with_retry_calls_internal_client_with_expected_arguments(self):
        """Test that search_with_retry calls the internal client's search method correctly."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {'query': {'match': {'givenName': 'John'}}}
        expected_response = {
            'hits': {
                'total': {'value': 1},
                'hits': [{'_source': {'givenName': 'John', 'familyName': 'Doe'}}],
            },
        }
        mock_internal_client.search.return_value = expected_response

        result = client.search_with_retry(index_name=index_name, body=query_body)

        mock_internal_client.search.assert_called_once_with(index=index_name, body=query_body)
        self.assertEqual(expected_response, result)

    @patch('opensearch_client.time.sleep')
    def test_search_with_retry_retries_on_connection_timeout_and_succeeds(self, mock_sleep):
        """Test that search_with_retry retries on ConnectionTimeout and eventually succeeds."""
        from opensearch_client import INITIAL_BACKOFF_SECONDS

        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {'query': {'match_all': {}}}
        expected_response = {'hits': {'total': {'value': 0}, 'hits': []}}

        # First two calls fail with ConnectionTimeout, third succeeds
        mock_internal_client.search.side_effect = [
            ConnectionTimeout('Connection timed out', 503, 'some error'),
            ConnectionTimeout('Connection timed out', 503, 'some error'),
            expected_response,
        ]

        result = client.search_with_retry(index_name=index_name, body=query_body)

        # Verify search was called 3 times
        self.assertEqual(3, mock_internal_client.search.call_count)
        # Verify sleep was called with exponential backoff
        self.assertEqual(2, mock_sleep.call_count)
        mock_sleep.assert_any_call(INITIAL_BACKOFF_SECONDS)
        mock_sleep.assert_any_call(INITIAL_BACKOFF_SECONDS * 2)
        # Verify we got the successful response
        self.assertEqual(expected_response, result)

    @patch('opensearch_client.time.sleep')
    def test_search_with_retry_retries_on_transport_error_and_succeeds(self, mock_sleep):
        """Test that search_with_retry retries on TransportError and eventually succeeds."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {'query': {'match_all': {}}}
        expected_response = {'hits': {'total': {'value': 0}, 'hits': []}}

        # First call fails with TransportError, second succeeds
        mock_internal_client.search.side_effect = [
            TransportError(503, 'ReadTimeout'),
            expected_response,
        ]

        result = client.search_with_retry(index_name=index_name, body=query_body)

        # Verify search was called 2 times
        self.assertEqual(2, mock_internal_client.search.call_count)
        # Verify sleep was called once
        self.assertEqual(1, mock_sleep.call_count)
        self.assertEqual(expected_response, result)

    @patch('opensearch_client.time.sleep')
    def test_search_with_retry_raises_cc_internal_exception_after_max_retries(self, mock_sleep):
        """Test that search_with_retry raises CCInternalException after all retry attempts fail."""
        from cc_common.exceptions import CCInternalException
        from opensearch_client import MAX_RETRY_ATTEMPTS

        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {'query': {'match_all': {}}}

        # All calls fail with ConnectionTimeout
        mock_internal_client.search.side_effect = ConnectionTimeout('Connection timed out', 503, 'some error')

        with self.assertRaises(CCInternalException) as context:
            client.search_with_retry(index_name=index_name, body=query_body)

        # Verify search was called MAX_RETRY_ATTEMPTS times
        self.assertEqual(MAX_RETRY_ATTEMPTS, mock_internal_client.search.call_count)
        # Verify sleep was called MAX_RETRY_ATTEMPTS - 1 times (no sleep after last failure)
        self.assertEqual(MAX_RETRY_ATTEMPTS - 1, mock_sleep.call_count)
        # Verify the exception message contains useful info
        self.assertIn('Search request', str(context.exception))
        self.assertIn(index_name, str(context.exception))
        self.assertIn(str(MAX_RETRY_ATTEMPTS), str(context.exception))

    def test_search_with_retry_raises_cc_invalid_request_exception_on_400_error_without_retrying(self):
        """Test that search_with_retry raises CCInvalidRequestException on 400 error without retrying."""
        from cc_common.exceptions import CCInvalidRequestException

        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {'query': {'invalid_query': {}}}

        error_reason = 'Unknown query type [invalid_query]'
        error_info = {
            'error': {
                'root_cause': [{'type': 'parsing_exception', 'reason': error_reason}],
                'type': 'parsing_exception',
                'reason': error_reason,
            },
            'status': 400,
        }
        mock_internal_client.search.side_effect = RequestError(400, 'parsing_exception', error_info)

        with self.assertRaises(CCInvalidRequestException) as context:
            client.search_with_retry(index_name=index_name, body=query_body)

        # Verify search was only called once (no retry on 400)
        self.assertEqual(1, mock_internal_client.search.call_count)
        # Verify the exception message extracts the reason
        self.assertEqual(f'Invalid search query: {error_reason}', str(context.exception))

    def test_search_with_retry_reraises_non_400_request_error(self):
        """Test that search_with_retry re-raises RequestError for non-400 status codes."""
        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {'query': {'match_all': {}}}

        # Simulate OpenSearch returning a 500 error
        mock_internal_client.search.side_effect = RequestError(500, 'internal_error', 'Something went wrong')

        with self.assertRaises(RequestError) as context:
            client.search_with_retry(index_name=index_name, body=query_body)

        self.assertEqual(500, context.exception.status_code)

    @patch('opensearch_client.time.sleep')
    def test_search_with_retry_exponential_backoff_caps_at_max(self, mock_sleep):
        """Test that exponential backoff is capped at MAX_BACKOFF_SECONDS."""
        from cc_common.exceptions import CCInternalException
        from opensearch_client import MAX_BACKOFF_SECONDS

        client, mock_internal_client = self._create_client_with_mock()

        index_name = 'test_index'
        query_body = {'query': {'match_all': {}}}

        # All calls fail
        mock_internal_client.search.side_effect = ConnectionTimeout('Connection timed out', 503, 'some error')

        with self.assertRaises(CCInternalException):
            client.search_with_retry(index_name=index_name, body=query_body)

        # Verify backoff values: 2, 4, 8, 16 (all should be <= MAX_BACKOFF_SECONDS)
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        for sleep_value in sleep_calls:
            self.assertLessEqual(sleep_value, MAX_BACKOFF_SECONDS)
