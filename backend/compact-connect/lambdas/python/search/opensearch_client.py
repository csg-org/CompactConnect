from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from cc_common.config import config
import boto3

class OpenSearchClient:
    def __init__(self):
        lambda_credentials = boto3.Session().get_credentials()
        auth = AWSV4SignerAuth(
            credentials=lambda_credentials,
            region=config.environment_region,
            service='es'
        )
        self._client = OpenSearch(
        hosts = [{'host': config.opensearch_host_endpoint, 'port': 443}],
        http_auth = auth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection,
        pool_maxsize = 20
    )

    def create_index(self, index_name: str, index_mapping: dict) -> None:
        self._client.indices.create(index=index_name, body=index_mapping)

    def index_exists(self, index_name: str) -> bool:
        return self._client.indices.exists(index=index_name)
