from unittest.mock import Mock, patch

from common_test.test_constants import (
    DEFAULT_DATE_OF_BIRTH,
    DEFAULT_LICENSE_EXPIRATION_DATE,
    DEFAULT_LICENSE_ISSUANCE_DATE,
    DEFAULT_LICENSE_RENEWAL_DATE,
    DEFAULT_LICENSE_UPDATE_DATE_OF_UPDATE,
    DEFAULT_PROVIDER_UPDATE_DATETIME,
)
from moto import mock_aws

from . import TstFunction

MOCK_COSM_PROVIDER_ID = '00000000-0000-0000-0000-000000000001'

test_license_type_mapping = {
    'cosm': 'cosmetologist',
}
test_provider_id_mapping = {
    'cosm': MOCK_COSM_PROVIDER_ID,
}


@mock_aws
class TestPopulateProviderDocuments(TstFunction):
    """Test suite for populate provider documents handler."""

    def setUp(self):
        super().setUp()

    def _put_test_provider_and_license_record_in_dynamodb_table(self, compact):
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'compact': compact,
                'providerId': test_provider_id_mapping[compact],
                'givenName': f'test{compact}GivenName',
                'familyName': f'test{compact}FamilyName',
            },
            date_of_update_override=DEFAULT_PROVIDER_UPDATE_DATETIME,
        )
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'compact': compact,
                'providerId': test_provider_id_mapping[compact],
                'givenName': f'test{compact}GivenName',
                'familyName': f'test{compact}FamilyName',
                'licenseType': test_license_type_mapping[compact],
            },
            date_of_update_override=DEFAULT_LICENSE_UPDATE_DATE_OF_UPDATE,
        )

    def _put_failed_ingest_record_in_search_event_state_table(
        self, compact: str, provider_id: str, sequence_number: str
    ):
        """Put a failed ingest record in the search event state table for testing."""
        import time
        from datetime import timedelta

        pk = f'COMPACT#{compact}#FAILED_INGEST'
        sk = f'PROVIDER#{provider_id}#SEQUENCE#{sequence_number}'
        ttl = int(time.time()) + int(timedelta(days=7).total_seconds())

        self.config.search_event_state_table.put_item(
            Item={
                'pk': pk,
                'sk': sk,
                'compact': compact,
                'providerId': provider_id,
                'sequenceNumber': sequence_number,
                'ttl': ttl,
            }
        )

    def _when_testing_mock_opensearch_client(self, mock_opensearch_client, bulk_index_response: dict = None):
        if not bulk_index_response:
            bulk_index_response = {'items': [], 'errors': False}

        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.bulk_index.return_value = bulk_index_response
        return mock_client_instance

    def _generate_expected_document(self, compact):
        provider_id = test_provider_id_mapping[compact]
        license_type = test_license_type_mapping[compact]
        return {
            'providerId': provider_id,
            'type': 'provider',
            'dateOfUpdate': DEFAULT_PROVIDER_UPDATE_DATETIME,
            'compact': compact,
            'licenseJurisdiction': 'oh',
            'licenseStatus': 'inactive',
            'compactEligibility': 'ineligible',
            'givenName': f'test{compact}GivenName',
            'middleName': 'Gunnar',
            'familyName': f'test{compact}FamilyName',
            'dateOfExpiration': DEFAULT_LICENSE_EXPIRATION_DATE,
            'jurisdictionUploadedLicenseStatus': 'active',
            'jurisdictionUploadedCompactEligibility': 'eligible',
            'birthMonthDay': '06-06',
            'documentId': f'{provider_id}#oh#{license_type}',
            'licenses': [
                {
                    'providerId': provider_id,
                    'type': 'license',
                    'dateOfUpdate': DEFAULT_LICENSE_UPDATE_DATE_OF_UPDATE,
                    'compact': compact,
                    'jurisdiction': 'oh',
                    'licenseType': license_type,
                    'licenseStatusName': 'DEFINITELY_A_HUMAN',
                    'licenseStatus': 'inactive',
                    'jurisdictionUploadedLicenseStatus': 'active',
                    'compactEligibility': 'ineligible',
                    'jurisdictionUploadedCompactEligibility': 'eligible',
                    'licenseNumber': 'A0608337260',
                    'givenName': f'test{compact}GivenName',
                    'middleName': 'Gunnar',
                    'familyName': f'test{compact}FamilyName',
                    'dateOfIssuance': DEFAULT_LICENSE_ISSUANCE_DATE,
                    'dateOfRenewal': DEFAULT_LICENSE_RENEWAL_DATE,
                    'dateOfExpiration': DEFAULT_LICENSE_EXPIRATION_DATE,
                    'dateOfBirth': DEFAULT_DATE_OF_BIRTH,
                    'homeAddressStreet1': '123 A St.',
                    'homeAddressStreet2': 'Apt 321',
                    'homeAddressCity': 'Columbus',
                    'homeAddressState': 'oh',
                    'homeAddressPostalCode': '43004',
                    'emailAddress': 'björk@example.com',
                    'phoneNumber': '+13213214321',
                    'adverseActions': [],
                    'investigations': [],
                }
            ],
            'privileges': [],
        }

    @patch('handlers.populate_provider_documents.OpenSearchClient')
    def test_populate_indexes_document_with_document_id(self, mock_opensearch_client):
        """Test that populate handler indexes documents with id_field='documentId'."""
        from handlers.populate_provider_documents import populate_provider_documents

        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)
        self._put_test_provider_and_license_record_in_dynamodb_table('cosm')

        mock_context = Mock()
        mock_context.get_remaining_time_in_millis.return_value = 600000

        result = populate_provider_documents({}, mock_context)

        self.assertTrue(result['completed'])
        self.assertGreaterEqual(mock_client_instance.bulk_index.call_count, 1)

        bulk_index_call = mock_client_instance.bulk_index.call_args
        self.assertEqual('compact_cosm_providers', bulk_index_call.kwargs['index_name'])
        self.assertEqual('documentId', bulk_index_call.kwargs['id_field'])

        indexed_documents = bulk_index_call.kwargs['documents']
        self.assertEqual(1, len(indexed_documents))
        self.assertEqual(self._generate_expected_document('cosm'), indexed_documents[0])
