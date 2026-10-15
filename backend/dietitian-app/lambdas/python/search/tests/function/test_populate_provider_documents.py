from unittest.mock import MagicMock, Mock, call, patch

from common_test.test_constants import (
    DEFAULT_LICENSE_EXPIRATION_DATE,
    DEFAULT_LICENSE_ISSUANCE_DATE,
    DEFAULT_LICENSE_RENEWAL_DATE,
    DEFAULT_LICENSE_UPDATE_DATE_OF_UPDATE,
    DEFAULT_PROVIDER_UPDATE_DATETIME,
    DEFAULT_REGISTERED_EMAIL_ADDRESS,
)
from moto import mock_aws

from . import TstFunction

MOCK_DIET_PROVIDER_ID = '00000000-0000-0000-0000-000000000001'
SECOND_DIET_PROVIDER_ID = '00000000-0000-0000-0000-000000000002'

test_license_type_mapping = {
    'diet': 'dietitian',
}
test_provider_id_mapping = {
    'diet': MOCK_DIET_PROVIDER_ID,
}


@mock_aws
class TestPopulateProviderDocuments(TstFunction):
    """Test suite for populate provider documents handler."""

    def setUp(self):
        super().setUp()

    def _put_test_provider_and_license_record_in_dynamodb_table(self, compact, provider_id=None):
        if provider_id is None:
            provider_id = test_provider_id_mapping[compact]
        self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'compact': compact,
                'providerId': provider_id,
                'givenName': f'test{compact}GivenName',
                'familyName': f'test{compact}FamilyName',
            },
            date_of_update_override=DEFAULT_PROVIDER_UPDATE_DATETIME,
        )
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'compact': compact,
                'providerId': provider_id,
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

        # Create a mock instance that will be returned by the OpenSearchClient constructor
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.bulk_index.return_value = bulk_index_response
        return mock_client_instance

    def _generate_expected_call_for_document(self, compact):
        # Use timezone(timedelta(0), '+0000') to match how the code creates UTC timezone
        return call(
            index_name=f'compact_{compact}_providers',
            documents=[
                {
                    'providerId': test_provider_id_mapping[compact],
                    'type': 'provider',
                    'dateOfUpdate': DEFAULT_PROVIDER_UPDATE_DATETIME,
                    'compact': compact,
                    'licenseJurisdiction': 'oh',
                    'currentHomeJurisdiction': 'oh',
                    'licenseStatus': 'inactive',
                    'compactEligibility': 'ineligible',
                    'npi': '0608337260',
                    'givenName': f'test{compact}GivenName',
                    'middleName': 'Gunnar',
                    'familyName': f'test{compact}FamilyName',
                    'dateOfExpiration': DEFAULT_LICENSE_EXPIRATION_DATE,
                    'compactConnectRegisteredEmailAddress': DEFAULT_REGISTERED_EMAIL_ADDRESS,
                    'jurisdictionUploadedLicenseStatus': 'active',
                    'jurisdictionUploadedCompactEligibility': 'eligible',
                    'militaryStatus': 'notApplicable',
                    'privilegeJurisdictions': ['ne'],
                    'birthMonthDay': '06-06',
                    'licenses': [
                        {
                            'providerId': test_provider_id_mapping[compact],
                            'type': 'license',
                            'dateOfUpdate': DEFAULT_LICENSE_UPDATE_DATE_OF_UPDATE,
                            'compact': compact,
                            'jurisdiction': 'oh',
                            'licenseType': test_license_type_mapping[compact],
                            'licenseStatusName': 'DEFINITELY_A_HUMAN',
                            'licenseStatus': 'inactive',
                            'jurisdictionUploadedLicenseStatus': 'active',
                            'compactEligibility': 'ineligible',
                            'jurisdictionUploadedCompactEligibility': 'eligible',
                            'npi': '0608337260',
                            'licenseNumber': 'A0608337260',
                            'givenName': f'test{compact}GivenName',
                            'middleName': 'Gunnar',
                            'familyName': f'test{compact}FamilyName',
                            'dateOfIssuance': DEFAULT_LICENSE_ISSUANCE_DATE,
                            'dateOfRenewal': DEFAULT_LICENSE_RENEWAL_DATE,
                            'dateOfExpiration': DEFAULT_LICENSE_EXPIRATION_DATE,
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
                    'militaryAffiliations': [],
                }
            ],
        )

    @patch('handlers.populate_provider_documents.OpenSearchClient')
    def test_provider_records_from_all_three_compacts_are_indexed_in_expected_index(self, mock_opensearch_client):
        from handlers.populate_provider_documents import TIME_THRESHOLD_MS, populate_provider_documents

        # Set up the mock opensearch client
        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        self._put_test_provider_and_license_record_in_dynamodb_table('diet')

        # mock the context to always return time above the cutoff threshold
        mock_context = MagicMock()
        mock_context.get_remaining_time_in_millis.return_value = TIME_THRESHOLD_MS + 60000

        # now run the handler
        result = populate_provider_documents({}, mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        self.assertEqual(1, mock_client_instance.bulk_index.call_count)
        bulk_index_calls = mock_client_instance.bulk_index.call_args_list
        self.assertEqual(self._generate_expected_call_for_document('diet'), bulk_index_calls[0])

        self.assertEqual(
            {
                'compacts_processed': [
                    {'compact': 'diet', 'providers_failed': 0, 'providers_indexed': 1, 'providers_processed': 1},
                ],
                'completed': True,
                'errors': [],
                'total_providers_failed': 0,
                'total_providers_indexed': 1,
                'total_providers_processed': 1,
            },
            result,
        )

    @patch('handlers.populate_provider_documents.OpenSearchClient')
    def test_pagination_across_invocations_when_time_limit_reached(self, mock_opensearch_client):
        """Test that the handler paginates within the diet compact when approaching the time limit.

        This test verifies:
        1. When the time limit is reached, the handler returns pagination info
        2. The pagination info can be passed to the next invocation to resume processing
        3. All diet records are eventually indexed across multiple invocations
        """
        from handlers.populate_provider_documents import TIME_THRESHOLD_MS, populate_provider_documents

        time_before_cutoff = TIME_THRESHOLD_MS + 60000
        time_after_cutoff = TIME_THRESHOLD_MS - 1000

        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        self._put_test_provider_and_license_record_in_dynamodb_table('diet', provider_id=MOCK_DIET_PROVIDER_ID)
        self._put_test_provider_and_license_record_in_dynamodb_table('diet', provider_id=SECOND_DIET_PROVIDER_ID)

        page_key = {'pk': 'diet#PROVIDER#page', 'sk': 'diet#PROVIDER'}
        with patch(
            'handlers.populate_provider_documents.config.data_client.get_providers_sorted_by_updated',
            side_effect=[
                {
                    'items': [{'providerId': MOCK_DIET_PROVIDER_ID}],
                    'pagination': {'lastKey': page_key},
                },
                {
                    'items': [{'providerId': SECOND_DIET_PROVIDER_ID}],
                    'pagination': {},
                },
            ],
        ):
            mock_context = MagicMock()
            mock_context.get_remaining_time_in_millis.side_effect = [time_before_cutoff, time_after_cutoff]

            first_result = populate_provider_documents({}, mock_context)

            self.assertFalse(first_result['completed'])
            self.assertEqual('diet', first_result['resumeFrom']['startingCompact'])
            self.assertEqual(page_key, first_result['resumeFrom']['startingLastKey'])
            self.assertEqual(1, first_result['total_providers_indexed'])
            self.assertEqual(1, mock_client_instance.bulk_index.call_count)
            self.assertEqual(self._generate_expected_call_for_document('diet'), mock_client_instance.bulk_index.call_args)

            mock_opensearch_client.reset_mock()
            mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)
            mock_context.get_remaining_time_in_millis.side_effect = [time_before_cutoff]

            second_result = populate_provider_documents(
                {
                    'startingCompact': first_result['resumeFrom']['startingCompact'],
                    'startingLastKey': first_result['resumeFrom']['startingLastKey'],
                },
                mock_context,
            )

        self.assertTrue(second_result['completed'])
        self.assertNotIn('resumeFrom', second_result)
        self.assertEqual(1, second_result['total_providers_indexed'])
        self.assertEqual(1, mock_client_instance.bulk_index.call_count)
        self.assertEqual(
            SECOND_DIET_PROVIDER_ID,
            mock_client_instance.bulk_index.call_args.kwargs['documents'][0]['providerId'],
        )

    @patch('handlers.populate_provider_documents.OpenSearchClient')
    def test_returns_pagination_info_when_bulk_indexing_fails_after_retries(self, mock_opensearch_client):
        """Test that the handler returns pagination info when bulk indexing fails after max retries.

        This test verifies:
        1. When CCInternalException is raised by bulk_index, the handler catches it
        2. The response includes resumeFrom with the batch_start_key for retry
        3. The developer can use this info to retry from the exact point of failure
        """
        from cc_common.exceptions import CCInternalException
        from handlers.populate_provider_documents import TIME_THRESHOLD_MS, populate_provider_documents

        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.bulk_index.side_effect = CCInternalException('Connection timeout after 5 retries')

        self._put_test_provider_and_license_record_in_dynamodb_table('diet')

        mock_context = MagicMock()
        mock_context.get_remaining_time_in_millis.return_value = TIME_THRESHOLD_MS + 60000

        result = populate_provider_documents({}, mock_context)

        self.assertFalse(result['completed'])
        self.assertEqual('diet', result['resumeFrom']['startingCompact'])
        self.assertIsNone(result['resumeFrom']['startingLastKey'])
        self.assertEqual(0, result['total_providers_indexed'])
        self.assertEqual(1, len(result['errors']))
        self.assertEqual('diet', result['errors'][0]['compact'])
        self.assertIn('Connection timeout', result['errors'][0]['error'])

        mock_opensearch_client.reset_mock()
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.bulk_index.return_value = {'items': [], 'errors': False}

        second_result = populate_provider_documents(
            {'startingCompact': result['resumeFrom']['startingCompact']},
            mock_context,
        )

        self.assertTrue(second_result['completed'])
        self.assertNotIn('resumeFrom', second_result)
        self.assertEqual(1, second_result['total_providers_indexed'])
        self.assertEqual(1, mock_client_instance.bulk_index.call_count)
