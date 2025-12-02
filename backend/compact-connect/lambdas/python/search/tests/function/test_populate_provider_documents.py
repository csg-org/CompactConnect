from datetime import date, datetime, timedelta, timezone
from unittest.mock import Mock, call, patch
from uuid import UUID

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
    """Test suite for OpenSearchIndexManager custom resource."""

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
        utc_tz = timezone(timedelta(0), '+0000')
        return call(
            index_name=f'compact_{compact}_providers',
            documents=[
                {
                    'providerId': UUID(test_provider_id_mapping[compact]),
                    'type': 'provider',
                    'dateOfUpdate': datetime.fromisoformat(DEFAULT_PROVIDER_UPDATE_DATETIME).replace(tzinfo=utc_tz),
                    'compact': compact,
                    'licenseJurisdiction': 'oh',
                    'currentHomeJurisdiction': 'oh',
                    'licenseStatus': 'inactive',
                    'compactEligibility': 'ineligible',
                    'npi': '0608337260',
                    'givenName': f'test{compact}GivenName',
                    'middleName': 'Gunnar',
                    'familyName': f'test{compact}FamilyName',
                    'dateOfExpiration': date.fromisoformat(DEFAULT_LICENSE_EXPIRATION_DATE),
                    'compactConnectRegisteredEmailAddress': DEFAULT_REGISTERED_EMAIL_ADDRESS,
                    'jurisdictionUploadedLicenseStatus': 'active',
                    'jurisdictionUploadedCompactEligibility': 'eligible',
                    'privilegeJurisdictions': {'ne'},
                    'birthMonthDay': '06-06',
                    'licenses': [
                        {
                            'providerId': UUID(test_provider_id_mapping[compact]),
                            'type': 'license',
                            'dateOfUpdate': datetime.fromisoformat(DEFAULT_LICENSE_UPDATE_DATE_OF_UPDATE).replace(
                                tzinfo=utc_tz
                            ),
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
                            'dateOfIssuance': date.fromisoformat(DEFAULT_LICENSE_ISSUANCE_DATE),
                            'dateOfRenewal': date.fromisoformat(DEFAULT_LICENSE_RENEWAL_DATE),
                            'dateOfExpiration': date.fromisoformat(DEFAULT_LICENSE_EXPIRATION_DATE),
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
        from handlers.populate_provider_documents import populate_provider_documents

        # Set up the mock opensearch client
        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        compacts = ['aslp', 'octp', 'coun']
        # add a provider and license record for each of the three compacts
        for compact in compacts:
            self._put_test_provider_and_license_record_in_dynamodb_table(compact)

        # now run the handler
        result = populate_provider_documents({}, self.mock_context)

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
        self.assertEqual(3, result['total_providers_processed'])
        self.assertEqual(3, result['total_providers_indexed'])
        self.assertEqual(0, result['total_providers_failed'])
