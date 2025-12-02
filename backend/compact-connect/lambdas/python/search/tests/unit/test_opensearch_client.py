from unittest import TestCase
from unittest.mock import MagicMock, patch


class TestOpenSearchClient(TestCase):
    """Test suite for OpenSearchClient to verify internal client calls."""

    def _create_client_with_mock(self):
        """Create an OpenSearchClient with a mocked internal client."""
        with patch('opensearch_client.boto3'), patch('opensearch_client.config'), patch(
            'opensearch_client.OpenSearch'
        ) as mock_opensearch_class:
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
        expected_response = {'errors': False, 'items': [{'index': {'_id': 'provider-1'}}, {'index': {'_id': 'provider-2'}}]}
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
        )

    def test_bulk_index_returns_early_for_empty_documents(self):
        """Test that bulk_index returns early without calling the internal client for empty documents."""
        client, mock_internal_client = self._create_client_with_mock()

        result = client.bulk_index(index_name='test_index', documents=[])

        mock_internal_client.bulk.assert_not_called()
        self.assertEqual({'items': [], 'errors': False}, result)




