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
        PLENTY_OF_TIME_MS = TIME_THRESHOLD_MS + 60000  # Above threshold, continue processing
        LOW_TIME_MS = TIME_THRESHOLD_MS - 1000  # Below threshold, trigger timeout

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
        mock_context.get_remaining_time_in_millis.side_effect = [PLENTY_OF_TIME_MS, LOW_TIME_MS]

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
        mock_context.get_remaining_time_in_millis.side_effect = [PLENTY_OF_TIME_MS, PLENTY_OF_TIME_MS]

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
