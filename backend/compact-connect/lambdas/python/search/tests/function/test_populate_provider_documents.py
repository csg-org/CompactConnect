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

MOCK_ASLP_PROVIDER_ID = '00000000-0000-0000-0000-000000000001'
MOCK_OCTP_PROVIDER_ID = '00000000-0000-0000-0000-000000000002'
MOCK_COUN_PROVIDER_ID = '00000000-0000-0000-0000-000000000003'

test_license_type_mapping = {
    'aslp': 'audiologist',
    'octp': 'occupational therapist',
    'coun': 'licensed professional counselor',
}
test_provider_id_mapping = {
    'aslp': MOCK_ASLP_PROVIDER_ID,
    'octp': MOCK_OCTP_PROVIDER_ID,
    'coun': MOCK_COUN_PROVIDER_ID,
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

        compacts = ['aslp', 'octp', 'coun']
        # add a provider and license record for each of the three compacts
        for compact in compacts:
            self._put_test_provider_and_license_record_in_dynamodb_table(compact)

        # mock the context to always return time above the cutoff threshold
        mock_context = MagicMock()
        mock_context.get_remaining_time_in_millis.return_value = TIME_THRESHOLD_MS + 60000

        # now run the handler
        result = populate_provider_documents({}, mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        # Assert that bulk indexing was called once for each compact (3 times total)
        self.assertEqual(3, mock_client_instance.bulk_index.call_count)

        # Get all calls to bulk_index and verify each compact was indexed
        bulk_index_calls = mock_client_instance.bulk_index.call_args_list
        self.assertEqual(self._generate_expected_call_for_document('aslp'), bulk_index_calls[0])
        self.assertEqual(self._generate_expected_call_for_document('octp'), bulk_index_calls[1])
        self.assertEqual(self._generate_expected_call_for_document('coun'), bulk_index_calls[2])

        # Verify the result statistics
        self.assertEqual(
            {
                'compacts_processed': [
                    {'compact': 'aslp', 'providers_failed': 0, 'providers_indexed': 1, 'providers_processed': 1},
                    {'compact': 'octp', 'providers_failed': 0, 'providers_indexed': 1, 'providers_processed': 1},
                    {'compact': 'coun', 'providers_failed': 0, 'providers_indexed': 1, 'providers_processed': 1},
                ],
                'completed': True,
                'errors': [],
                'total_providers_failed': 0,
                'total_providers_indexed': 3,
                'total_providers_processed': 3,
            },
            result,
        )

    @patch('handlers.populate_provider_documents.OpenSearchClient')
    def test_pagination_across_invocations_when_time_limit_reached(self, mock_opensearch_client):
        """Test that the handler properly paginates across multiple invocations when approaching time limit.

        This test verifies:
        1. When the time limit is reached, the handler returns pagination info
        2. The pagination info can be passed to the next invocation to resume processing
        3. All records are eventually indexed across multiple invocations
        """
        from handlers.populate_provider_documents import TIME_THRESHOLD_MS, populate_provider_documents

        # Time values for mocking (in milliseconds)
        time_before_cutoff = TIME_THRESHOLD_MS + 60000  # before cutoff time, continue processing
        time_after_cutoff = TIME_THRESHOLD_MS - 1000  # after cutoff time, trigger timeout

        # Set up the mock opensearch client
        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        compacts = ['aslp', 'octp', 'coun']
        # Add a provider and license record for each of the three compacts
        for compact in compacts:
            self._put_test_provider_and_license_record_in_dynamodb_table(compact)

        # First invocation: Mock time to trigger timeout after processing first compact (aslp)
        # The time check happens at the START of each while loop iteration:
        # - Call 1: Processing aslp, plenty of time -> continue
        # - Call 2: About to process octp, low time -> timeout and return
        mock_context = MagicMock()
        mock_context.get_remaining_time_in_millis.side_effect = [time_before_cutoff, time_after_cutoff]

        # Run the first invocation
        first_result = populate_provider_documents({}, mock_context)

        # Verify first invocation returned incomplete with pagination info
        self.assertFalse(first_result['completed'])
        self.assertIn('resumeFrom', first_result)
        self.assertEqual('octp', first_result['resumeFrom']['startingCompact'])
        # startingLastKey should be None since we haven't started processing octp yet
        self.assertIsNone(first_result['resumeFrom']['startingLastKey'])

        # Verify only aslp was indexed in first invocation
        self.assertEqual(1, first_result['total_providers_indexed'])
        self.assertEqual(1, mock_client_instance.bulk_index.call_count)

        # Second invocation: Use the resumeFrom values as input
        # Reset the mock for the second invocation
        mock_opensearch_client.reset_mock()
        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Mock time to allow completion - needs enough calls for both octp and coun
        # - Call 1: Processing octp, plenty of time -> continue
        # - Call 2: Processing coun, plenty of time -> continue
        mock_context.get_remaining_time_in_millis.side_effect = [time_before_cutoff, time_before_cutoff]

        # Build the resume event from the first result
        resume_event = {
            'startingCompact': first_result['resumeFrom']['startingCompact'],
            'startingLastKey': first_result['resumeFrom']['startingLastKey'],
        }

        # Run the second invocation with pagination info
        second_result = populate_provider_documents(resume_event, mock_context)

        # Verify second invocation completed successfully
        self.assertTrue(second_result['completed'])
        self.assertNotIn('resumeFrom', second_result)

        # Verify octp and coun were indexed in second invocation
        self.assertEqual(2, second_result['total_providers_indexed'])
        self.assertEqual(2, mock_client_instance.bulk_index.call_count)

        # Verify the correct indices were called
        bulk_index_calls = mock_client_instance.bulk_index.call_args_list
        self.assertEqual(self._generate_expected_call_for_document('octp'), bulk_index_calls[0])
        self.assertEqual(self._generate_expected_call_for_document('coun'), bulk_index_calls[1])

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

        # Set up the mock opensearch client to raise CCInternalException on second compact
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance

        # First compact (aslp) succeeds, second compact (octp) fails with CCInternalException
        mock_client_instance.bulk_index.side_effect = [
            {'items': [], 'errors': False},  # aslp succeeds
            CCInternalException('Connection timeout after 5 retries'),  # octp fails
        ]

        compacts = ['aslp', 'octp', 'coun']
        # Add a provider and license record for each compact
        for compact in compacts:
            self._put_test_provider_and_license_record_in_dynamodb_table(compact)

        # Mock the context to always return time above the cutoff threshold
        mock_context = MagicMock()
        mock_context.get_remaining_time_in_millis.return_value = TIME_THRESHOLD_MS + 60000

        # Run the handler
        result = populate_provider_documents({}, mock_context)

        # Verify the result indicates incomplete processing
        self.assertFalse(result['completed'])
        self.assertIn('resumeFrom', result)

        # Verify resumeFrom points to octp with the batch_start_key (None since it's the first batch)
        self.assertEqual('octp', result['resumeFrom']['startingCompact'])
        # startingLastKey should be None since it was the first batch of octp
        self.assertIsNone(result['resumeFrom']['startingLastKey'])

        # Verify aslp was indexed but octp was not
        self.assertEqual(1, result['total_providers_indexed'])

        # Verify errors list contains the failure info
        self.assertEqual(1, len(result['errors']))
        self.assertEqual('octp', result['errors'][0]['compact'])
        self.assertIn('Connection timeout', result['errors'][0]['error'])

        # Now verify that using resumeFrom allows completing the indexing
        mock_opensearch_client.reset_mock()
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.bulk_index.return_value = {'items': [], 'errors': False}

        # Build the resume event from the first result
        resume_event = {
            'startingCompact': result['resumeFrom']['startingCompact'],
            'startingLastKey': result['resumeFrom']['startingLastKey'],
        }

        # Run the second invocation
        second_result = populate_provider_documents(resume_event, mock_context)

        # Verify second invocation completed successfully
        self.assertTrue(second_result['completed'])
        self.assertNotIn('resumeFrom', second_result)

        # Verify octp and coun were indexed
        self.assertEqual(2, second_result['total_providers_indexed'])
        self.assertEqual(2, mock_client_instance.bulk_index.call_count)

    @patch('handlers.populate_provider_documents.OpenSearchClient')
    def test_retry_ingest_failures_for_compact_indexes_only_failed_providers(self, mock_opensearch_client):
        """Test that retry_ingest_failures_for_compact only indexes providers from the search event state table.

        This test verifies:
        1. A failed ingest record is put in the search event state table
        2. A provider record exists in the provider table
        3. When 'retry_ingest_failures_for_compact' is passed, only that provider is indexed
        4. The opensearch_client is called with the correct provider document
        """
        from handlers.populate_provider_documents import populate_provider_documents

        # Set up the mock opensearch client
        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        compact = 'aslp'
        provider_id = MOCK_ASLP_PROVIDER_ID
        sequence_number = '12345'

        # Put a failed ingest record in the search event state table
        self._put_failed_ingest_record_in_search_event_state_table(compact, provider_id, sequence_number)

        # Put provider and license records in the provider table
        self._put_test_provider_and_license_record_in_dynamodb_table(compact)

        # Create event with retry_ingest_failures_for_compact
        event = {'retry_ingest_failures_for_compact': compact}

        # Mock context (not used in retry path, but required for handler signature)
        mock_context = MagicMock()

        # Run the handler
        result = populate_provider_documents(event, mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        # Assert that bulk_index was called exactly once (only for the failed provider)
        self.assertEqual(1, mock_client_instance.bulk_index.call_count)

        # Verify the call was made with the correct provider document
        bulk_index_calls = mock_client_instance.bulk_index.call_args_list
        expected_call = self._generate_expected_call_for_document(compact)
        self.assertEqual(expected_call, bulk_index_calls[0])

        # Verify the result statistics
        self.assertEqual(
            {
                'compacts_processed': [
                    {
                        'compact': compact,
                        'providers_failed': 0,
                        'providers_indexed': 1,
                        'providers_deleted': 0,
                        'providers_processed': 1,
                    }
                ],
                'completed': True,
                'total_providers_failed': 0,
                'total_providers_deleted': 0,
                'total_providers_indexed': 1,
                'total_providers_processed': 1,
            },
            result,
        )

    @patch('handlers.populate_provider_documents.OpenSearchClient')
    def test_retry_ingest_failures_deletes_providers_when_not_found(self, mock_opensearch_client):
        """Test that retry_ingest_failures_for_compact deletes providers from index when CCNotFoundException is raised.

        This test verifies:
        1. A failed ingest record is put in the search event state table
        2. NO provider records exist in the provider table (simulating deletion/rollback)
        3. When 'retry_ingest_failures_for_compact' is passed, bulk_delete is called
        4. The provider is deleted from the OpenSearch index
        5. Statistics reflect the deletion
        """
        from handlers.populate_provider_documents import populate_provider_documents

        # Set up the mock opensearch client
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.bulk_index.return_value = set()
        mock_client_instance.bulk_delete.return_value = set()

        compact = 'aslp'
        provider_id = MOCK_ASLP_PROVIDER_ID
        sequence_number = '12345'

        # Put a failed ingest record in the search event state table
        self._put_failed_ingest_record_in_search_event_state_table(compact, provider_id, sequence_number)

        # Do NOT create provider records in the provider table - this simulates the provider being deleted

        # Create event with retry_ingest_failures_for_compact
        event = {'retry_ingest_failures_for_compact': compact}

        # Mock context (not used in retry path, but required for handler signature)
        mock_context = MagicMock()

        # Run the handler
        result = populate_provider_documents(event, mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        # Assert that bulk_index was NOT called (no documents to index)
        mock_client_instance.bulk_index.assert_not_called()

        # Assert that bulk_delete WAS called with the correct parameters
        self.assertEqual(1, mock_client_instance.bulk_delete.call_count)
        call_args = mock_client_instance.bulk_delete.call_args
        self.assertEqual('compact_aslp_providers', call_args.kwargs['index_name'])
        self.assertEqual([MOCK_ASLP_PROVIDER_ID], call_args.kwargs['document_ids'])

        # Verify the result statistics
        self.assertEqual(
            {
                'compacts_processed': [
                    {
                        'compact': compact,
                        'providers_deleted': 1,
                        'providers_failed': 0,
                        'providers_indexed': 0,
                        'providers_processed': 1,
                    }
                ],
                'completed': True,
                'total_providers_deleted': 1,
                'total_providers_failed': 0,
                'total_providers_indexed': 0,
                'total_providers_processed': 1,
            },
            result,
        )
