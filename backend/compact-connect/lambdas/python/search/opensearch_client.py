import boto3
from cc_common.config import config
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection


class OpenSearchClient:
    def __init__(self):
        lambda_credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(credentials=lambda_credentials, region=config.environment_region, service='es')
        self._client = OpenSearch(
            hosts=[{'host': config.opensearch_host_endpoint, 'port': 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            pool_maxsize=20,
        )

    def create_index(self, index_name: str, index_mapping: dict) -> None:
        self._client.indices.create(index=index_name, body=index_mapping)

    def index_exists(self, index_name: str) -> bool:
        return self._client.indices.exists(index=index_name)

    def search(self, index_name: str, body: dict) -> dict:
        """
        Execute a search query against the specified index.

        :param index_name: The name of the index to search
        :param body: The OpenSearch query body
        :return: The search response from OpenSearch
        """
        return self._client.search(index=index_name, body=body)

    def index_document(self, index_name: str, document_id: str, document: dict) -> dict:
        """
        Index a single document into the specified index.

        :param index_name: The name of the index to write to.
        :param document_id: The unique identifier for the document.
        :param document: The document to index
        :return: The response from OpenSearch
        """
        return self._client.index(index=index_name, id=document_id, body=document)

    def bulk_index(self, index_name: str, documents: list[dict], id_field: str = 'providerId') -> dict:
        """
        Bulk index multiple documents into the specified index.

        :param index_name: The name of the index to write to
        :param documents: List of documents to index
        :param id_field: The field name to use as the document ID (default: 'providerId')
        :return: The bulk response from OpenSearch
        """
        if not documents:
            return {'items': [], 'errors': False}

        actions = []
        for doc in documents:
            # Note: We specify the index via the `index` parameter in the bulk() call below,
            # not in the action metadata. This is required because the OpenSearch domain has
            # `rest.action.multi.allow_explicit_index: false` which prevents specifying
            # indices in the request body for security purposes.
            actions.append({'index': {'_id': doc[id_field]}})
            actions.append(doc)
        return self._client.bulk(body=actions, index=index_name)
