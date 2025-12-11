import json
from unittest.mock import MagicMock, Mock, patch

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

TEST_LICENSE_TYPE_MAPPING = {
    'aslp': 'audiologist',
    'octp': 'occupational therapist',
}
TEST_PROVIDER_ID_MAPPING = {
    'aslp': MOCK_ASLP_PROVIDER_ID,
    'octp': MOCK_OCTP_PROVIDER_ID,
}


@mock_aws
class TestProviderUpdateIngest(TstFunction):
    """Test suite for provider update ingest handler."""

    def setUp(self):
        super().setUp()

    def _put_test_provider_and_license_record_in_dynamodb_table(self, compact: str, provider_id: str = None):
        """Helper to create test provider and license records in DynamoDB."""
        if provider_id is None:
            provider_id = TEST_PROVIDER_ID_MAPPING[compact]

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
                'licenseType': TEST_LICENSE_TYPE_MAPPING[compact],
            },
            date_of_update_override=DEFAULT_LICENSE_UPDATE_DATE_OF_UPDATE,
        )

    def _create_dynamodb_stream_record(
        self,
        compact: str,
        provider_id: str,
        sequence_number: str,
        event_name: str = 'MODIFY',
        include_old_image: bool = True,
    ) -> dict:
        """
        Create a DynamoDB stream record in the format received by Lambda.

        DynamoDB stream records contain the image data in a specific format where
        each attribute is wrapped with its type indicator (e.g., {'S': 'value'} for strings).

        :param compact: The compact abbreviation
        :param provider_id: The provider ID
        :param sequence_number: The stream sequence number
        :param event_name: The event type (INSERT, MODIFY, REMOVE)
        :param include_old_image: Whether to include OldImage (False for INSERT events)
        """
        image_data = {
            'pk': {'S': f'{compact}#PROVIDER#{provider_id}'},
            'sk': {'S': f'{compact}#PROVIDER'},
            'compact': {'S': compact},
            'providerId': {'S': provider_id},
            'type': {'S': 'provider'},
            'givenName': {'S': f'test{compact}GivenName'},
            'familyName': {'S': f'test{compact}FamilyName'},
        }

        dynamodb_data = {
            'ApproximateCreationDateTime': 1234567890,
            'Keys': {
                'pk': {'S': f'{compact}#PROVIDER#{provider_id}'},
                'sk': {'S': f'{compact}#PROVIDER'},
            },
            'NewImage': image_data,
            'SequenceNumber': sequence_number,
            'SizeBytes': 256,
            'StreamViewType': 'NEW_AND_OLD_IMAGES',
        }

        # Include OldImage only if requested (MODIFY events have both, INSERT events only have NewImage)
        if include_old_image:
            dynamodb_data['OldImage'] = image_data

        return {
            'eventID': f'event-{sequence_number}',
            'eventName': event_name,
            'eventVersion': '1.1',
            'eventSource': 'aws:dynamodb',
            'awsRegion': 'us-east-1',
            'dynamodb': dynamodb_data,
            'eventSourceARN': 'arn:aws:dynamodb:us-east-1:123456789012:table/provider-table/stream/1234',
        }

    def _when_testing_mock_opensearch_client(self, mock_opensearch_client, bulk_index_response: dict = None):
        """Helper to configure the mock OpenSearch client."""
        if not bulk_index_response:
            bulk_index_response = {'items': [], 'errors': False}

        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.bulk_index.return_value = bulk_index_response
        return mock_client_instance

    def _generate_expected_document(self, compact: str, provider_id: str = None) -> dict:
        """Generate the expected document that should be indexed into OpenSearch."""
        if provider_id is None:
            provider_id = TEST_PROVIDER_ID_MAPPING[compact]

        return {
            'providerId': provider_id,
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
                    'providerId': provider_id,
                    'type': 'license',
                    'dateOfUpdate': DEFAULT_LICENSE_UPDATE_DATE_OF_UPDATE,
                    'compact': compact,
                    'jurisdiction': 'oh',
                    'licenseType': TEST_LICENSE_TYPE_MAPPING[compact],
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

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_opensearch_client_called_with_expected_parameters(self, mock_opensearch_client):
        """Test that OpenSearch client is called with expected parameters when indexing a record."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        # Set up mock OpenSearch client
        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Create provider and license records in DynamoDB
        self._put_test_provider_and_license_record_in_dynamodb_table('aslp')

        # Create an SQS event with DynamoDB stream record in the body
        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                        )
                    ),
                }
            ]
        }

        # Run the handler
        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        # Assert that bulk_index was called once with expected parameters
        self.assertEqual(1, mock_client_instance.bulk_index.call_count)

        # Verify the call arguments
        call_args = mock_client_instance.bulk_index.call_args
        self.assertEqual('compact_aslp_providers', call_args.kwargs['index_name'])
        self.assertEqual([self._generate_expected_document('aslp')], call_args.kwargs['documents'])

        # Verify no batch item failures
        self.assertEqual({'batchItemFailures': []}, result)

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_provider_ids_are_deduped_only_one_document_indexed(self, mock_opensearch_client):
        """Test that duplicate provider IDs in the batch are deduplicated."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        # Set up mock OpenSearch client
        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Create provider and license records in DynamoDB
        self._put_test_provider_and_license_record_in_dynamodb_table('aslp')

        # Create multiple SQS records for the SAME provider (simulating multiple updates)
        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number-1',
                            event_name='INSERT',
                        )
                    ),
                },
                {
                    'messageId': '12346',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number-2',
                            event_name='MODIFY',
                        )
                    ),
                },
                {
                    'messageId': '12347',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number-3',
                            event_name='MODIFY',
                        )
                    ),
                },
            ]
        }

        # Run the handler
        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Assert that bulk_index was called only once despite 3 records
        self.assertEqual(1, mock_client_instance.bulk_index.call_count)

        # Verify only ONE document was indexed (deduplication worked)
        call_args = mock_client_instance.bulk_index.call_args
        self.assertEqual(1, len(call_args.kwargs['documents']))
        self.assertEqual(MOCK_ASLP_PROVIDER_ID, call_args.kwargs['documents'][0]['providerId'])

        # Verify no batch item failures
        self.assertEqual({'batchItemFailures': []}, result)

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_validation_failure_returns_batch_item_failure(self, mock_opensearch_client):
        """Test that a record that fails validation is returned in batchItemFailures."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        # Set up mock OpenSearch client
        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        provider = self.test_data_generator.generate_default_provider(
            value_overrides={
                'compact': 'aslp',
                'providerId': MOCK_ASLP_PROVIDER_ID,
                'givenName': 'testGivenName',
                'familyName': 'testFamilyName',
            }
        )
        serialized_provider = provider.serialize_to_database_record()
        # put invalid compact to fail validation
        serialized_provider['compact'] = 'foo'
        self.config.provider_table.put_item(Item=serialized_provider)

        # Create SQS event with DynamoDB stream record in the body
        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                        )
                    ),
                }
            ]
        }

        # Run the handler
        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Verify that the batch item failure is returned with the message ID
        self.assertEqual(1, len(result['batchItemFailures']))
        self.assertEqual('12345', result['batchItemFailures'][0]['itemIdentifier'])

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_opensearch_indexing_failure_returns_batch_item_failure(self, mock_opensearch_client):
        """Test that a record which fails to be indexed by OpenSearch is in batchItemFailures."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        # Set up mock OpenSearch client to return errors for specific documents
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance

        # Simulate OpenSearch returning an error for one document
        mock_client_instance.bulk_index.return_value = {
            'errors': True,
            'items': [
                {
                    'index': {
                        '_id': MOCK_ASLP_PROVIDER_ID,
                        '_index': 'compact_aslp_providers',
                        'status': 201,
                        'result': 'created',
                    }
                },
                {
                    'index': {
                        '_id': MOCK_OCTP_PROVIDER_ID,
                        '_index': 'compact_octp_providers',
                        'status': 400,
                        'error': {
                            'type': 'mapper_parsing_exception',
                            'reason': 'failed to parse field',
                        },
                    }
                },
            ],
        }

        # Create provider and license records in DynamoDB for both compacts
        self._put_test_provider_and_license_record_in_dynamodb_table('aslp')
        self._put_test_provider_and_license_record_in_dynamodb_table('octp')

        # Create SQS events with DynamoDB stream records in the body for both providers
        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number-1',
                        )
                    ),
                },
                {
                    'messageId': '12346',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='octp',
                            provider_id=MOCK_OCTP_PROVIDER_ID,
                            sequence_number='some-sequence-number-2',
                        )
                    ),
                },
            ]
        }

        # Run the handler
        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Verify that only the failed document's message ID is in batchItemFailures
        self.assertEqual(1, len(result['batchItemFailures']))
        self.assertEqual('12346', result['batchItemFailures'][0]['itemIdentifier'])

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_bulk_index_exception_returns_all_batch_item_failures(self, mock_opensearch_client):
        """Test that when bulk_index raises an exception, all providers are marked as failed."""
        from cc_common.exceptions import CCInternalException
        from handlers.provider_update_ingest import provider_update_ingest_handler

        # Set up mock OpenSearch client to raise an exception
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.bulk_index.side_effect = CCInternalException('Connection timeout after 5 retries')

        # Create provider and license records in DynamoDB for both compacts
        self._put_test_provider_and_license_record_in_dynamodb_table('aslp')
        self._put_test_provider_and_license_record_in_dynamodb_table('octp')

        # Create SQS events with DynamoDB stream records in the body for both providers
        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number-1',
                        )
                    ),
                },
                {
                    'messageId': '12346',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='octp',
                            provider_id=MOCK_OCTP_PROVIDER_ID,
                            sequence_number='some-sequence-number-2',
                        )
                    ),
                },
            ]
        }

        # Run the handler
        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Verify that both records were returned in batch failures
        self.assertEqual(2, len(result['batchItemFailures']))
        self.assertEqual('12345', result['batchItemFailures'][0]['itemIdentifier'])
        self.assertEqual('12346', result['batchItemFailures'][1]['itemIdentifier'])

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_multiple_compacts_indexed_separately(self, mock_opensearch_client):
        """Test that providers from different compacts are indexed in their respective indices."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        # Set up mock OpenSearch client
        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Create provider and license records for two different compacts
        self._put_test_provider_and_license_record_in_dynamodb_table('aslp')
        self._put_test_provider_and_license_record_in_dynamodb_table('octp')

        # Create SQS events with DynamoDB stream records in the body for both compacts
        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number-1',
                        )
                    ),
                },
                {
                    'messageId': '12346',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='octp',
                            provider_id=MOCK_OCTP_PROVIDER_ID,
                            sequence_number='some-sequence-number-2',
                        )
                    ),
                },
            ]
        }

        # Run the handler
        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Assert that bulk_index was called for each compact that had providers
        # Note: The handler iterates over all compacts, but only calls bulk_index if there are documents
        call_args_list = mock_client_instance.bulk_index.call_args_list

        # Find the calls for aslp and octp
        aslp_calls = [c for c in call_args_list if c.kwargs['index_name'] == 'compact_aslp_providers']
        octp_calls = [c for c in call_args_list if c.kwargs['index_name'] == 'compact_octp_providers']

        self.assertEqual(1, len(aslp_calls))
        self.assertEqual(1, len(octp_calls))

        # Verify each call has the correct document
        self.assertEqual([self._generate_expected_document('aslp')], aslp_calls[0].kwargs['documents'])
        self.assertEqual([self._generate_expected_document('octp')], octp_calls[0].kwargs['documents'])

        # Verify no batch item failures
        self.assertEqual({'batchItemFailures': []}, result)

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_empty_records_returns_empty_batch_failures(self, mock_opensearch_client):
        """Test that an empty Records list returns empty batchItemFailures."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        event = {'Records': []}

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Verify empty response
        self.assertEqual({'batchItemFailures': []}, result)

        # Verify OpenSearch client was never called
        mock_opensearch_client.assert_not_called()

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_insert_event_without_old_image_indexes_successfully(self, mock_opensearch_client):
        """Test that INSERT events (newly created records) without OldImage are processed correctly.

        When a new record is created in DynamoDB, the stream event contains only NewImage
        and no OldImage. The handler should extract the compact and providerId from NewImage
        and successfully index the document.
        """
        from handlers.provider_update_ingest import provider_update_ingest_handler

        # Set up mock OpenSearch client
        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Create provider and license records in DynamoDB
        self._put_test_provider_and_license_record_in_dynamodb_table('aslp')

        # Create an SQS event with DynamoDB stream record in the body for INSERT (no OldImage)
        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                            event_name='INSERT',
                            include_old_image=False,  # INSERT events don't have OldImage
                        )
                    ),
                }
            ]
        }

        # Run the handler
        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        # Assert that bulk_index was called with the correct parameters
        self.assertEqual(1, mock_client_instance.bulk_index.call_count)

        # Verify the call arguments
        call_args = mock_client_instance.bulk_index.call_args
        self.assertEqual('compact_aslp_providers', call_args.kwargs['index_name'])
        self.assertEqual([self._generate_expected_document('aslp')], call_args.kwargs['documents'])

        # Verify no batch item failures for INSERT event
        self.assertEqual({'batchItemFailures': []}, result)

    def _create_dynamodb_stream_record_with_old_image_only(
        self, compact: str, provider_id: str, sequence_number: str
    ) -> dict:
        """Create a DynamoDB stream record for REMOVE events (only OldImage, no NewImage)."""
        image_data = {
            'pk': {'S': f'{compact}#PROVIDER#{provider_id}'},
            'sk': {'S': f'{compact}#PROVIDER'},
            'compact': {'S': compact},
            'providerId': {'S': provider_id},
            'type': {'S': 'provider'},
            'givenName': {'S': f'test{compact}GivenName'},
            'familyName': {'S': f'test{compact}FamilyName'},
        }

        return {
            'eventID': f'event-{sequence_number}',
            'eventName': 'REMOVE',
            'eventVersion': '1.1',
            'eventSource': 'aws:dynamodb',
            'awsRegion': 'us-east-1',
            'dynamodb': {
                'ApproximateCreationDateTime': 1234567890,
                'Keys': {
                    'pk': {'S': f'{compact}#PROVIDER#{provider_id}'},
                    'sk': {'S': f'{compact}#PROVIDER'},
                },
                'OldImage': image_data,  # REMOVE events only have OldImage
                'SequenceNumber': sequence_number,
                'SizeBytes': 256,
                'StreamViewType': 'NEW_AND_OLD_IMAGES',
            },
            'eventSourceARN': 'arn:aws:dynamodb:us-east-1:123456789012:table/provider-table/stream/1234',
        }

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_remove_event_with_only_old_image_indexes_successfully(self, mock_opensearch_client):
        """Test that REMOVE events (deleted records) with only OldImage are processed correctly.

        When a record is deleted from DynamoDB, the stream event contains only OldImage
        and no NewImage. The handler should extract the compact and providerId from OldImage
        and still index/update the document (to reflect the latest state of the provider).
        """
        from handlers.provider_update_ingest import provider_update_ingest_handler

        # Set up mock OpenSearch client
        mock_client_instance = self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Create provider and license records in DynamoDB
        self._put_test_provider_and_license_record_in_dynamodb_table('aslp')

        # Create an SQS event with DynamoDB stream record in the body for REMOVE (only OldImage, no NewImage)
        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record_with_old_image_only(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                        )
                    ),
                }
            ]
        }

        # Run the handler
        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        # Assert that bulk_index was called with the correct parameters
        self.assertEqual(1, mock_client_instance.bulk_index.call_count)

        # Verify the call arguments
        call_args = mock_client_instance.bulk_index.call_args
        self.assertEqual('compact_aslp_providers', call_args.kwargs['index_name'])
        self.assertEqual([self._generate_expected_document('aslp')], call_args.kwargs['documents'])

        # Verify no batch item failures for REMOVE event
        self.assertEqual({'batchItemFailures': []}, result)

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_provider_deleted_from_index_when_no_records_found(self, mock_opensearch_client):
        """Test that when no provider records are found (CCNotFoundException), bulk_delete is called.

        This scenario occurs when a provider is completely removed from the system,
        such as during a license upload rollback. The handler should call bulk_delete
        to remove the provider document from the OpenSearch index.
        """
        from handlers.provider_update_ingest import provider_update_ingest_handler

        # Set up mock OpenSearch client
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.bulk_index.return_value = {'items': [], 'errors': False}
        mock_client_instance.bulk_delete.return_value = {'items': [], 'errors': False}

        # Do NOT create any provider records in DynamoDB - this simulates the provider being deleted

        # Create an SQS event with DynamoDB stream record in the body for a provider that no longer exists
        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                            event_name='REMOVE',
                            include_old_image=False,
                        )
                    ),
                }
            ]
        }

        # Run the handler
        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        # Assert that bulk_index was NOT called (no documents to index)
        mock_client_instance.bulk_index.assert_not_called()

        # Assert that bulk_delete WAS called with the correct parameters
        self.assertEqual(1, mock_client_instance.bulk_delete.call_count)
        call_args = mock_client_instance.bulk_delete.call_args
        self.assertEqual('compact_aslp_providers', call_args.kwargs['index_name'])
        self.assertEqual([MOCK_ASLP_PROVIDER_ID], call_args.kwargs['document_ids'])

        # Verify no batch item failures (deletion is expected behavior, not a failure)
        self.assertEqual({'batchItemFailures': []}, result)

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_bulk_delete_failure_returns_batch_item_failure(self, mock_opensearch_client):
        """Test that when bulk_delete fails, the provider is returned in batchItemFailures."""
        from cc_common.exceptions import CCInternalException
        from handlers.provider_update_ingest import provider_update_ingest_handler

        # Set up mock OpenSearch client - bulk_delete raises exception
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.bulk_delete.side_effect = CCInternalException('Connection timeout after 5 retries')

        # Do NOT create any provider records in DynamoDB - this simulates the provider being deleted

        # Create an SQS event with DynamoDB stream record in the body for a provider that no longer exists
        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                            event_name='REMOVE',
                            include_old_image=False,
                        )
                    ),
                }
            ]
        }

        # Run the handler
        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Verify that the batch item failure is returned with the message ID
        self.assertEqual(1, len(result['batchItemFailures']))
        self.assertEqual('12345', result['batchItemFailures'][0]['itemIdentifier'])

    @patch('handlers.provider_update_ingest.OpenSearchClient')
    def test_bulk_delete_404_not_found_does_not_return_batch_item_failure(self, mock_opensearch_client):
        """Test that when bulk_delete returns 404 (document not found), it is NOT treated as a failure.

        This scenario occurs when a provider document has already been deleted from OpenSearch
        (e.g., a previous delete succeeded, or the document never existed in the index).
        The 404 response should be ignored since the desired end state (document not in index)
        has been achieved.
        """
        from handlers.provider_update_ingest import provider_update_ingest_handler

        # Set up mock OpenSearch client - bulk_delete returns 404 not_found response
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance

        # Simulate OpenSearch bulk delete response when document doesn't exist
        mock_client_instance.bulk_delete.return_value = {
            'errors': True,  # OpenSearch reports this as an "error" even though it's just not found
            'items': [
                {
                    'delete': {
                        '_index': 'compact_aslp_providers',
                        '_id': MOCK_ASLP_PROVIDER_ID,
                        'status': 404,
                        'result': 'not_found',
                        'error': {
                            'type': 'document_missing_exception',
                            'reason': f'[_doc][{MOCK_ASLP_PROVIDER_ID}]: document missing',
                        },
                    }
                }
            ],
        }

        # Do NOT create any provider records in DynamoDB - this simulates the provider being deleted

        # Create a DynamoDB stream event for a provider that no longer exists
        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='aslp',
                            provider_id=MOCK_ASLP_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                            event_name='REMOVE',
                            include_old_image=False,
                        )
                    ),
                }
            ]
        }

        # Run the handler
        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # Assert that bulk_delete was called
        self.assertEqual(1, mock_client_instance.bulk_delete.call_count)

        # Verify NO batch item failures - 404 is not treated as an error
        self.assertEqual({'batchItemFailures': []}, result)
