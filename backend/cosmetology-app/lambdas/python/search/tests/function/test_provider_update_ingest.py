import json
from unittest.mock import MagicMock, patch

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

TEST_LICENSE_TYPE_MAPPING = {
    'cosm': 'cosmetologist',
}
TEST_PROVIDER_ID_MAPPING = {
    'cosm': MOCK_COSM_PROVIDER_ID,
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

        mock_opensearch_client.bulk_index.return_value = bulk_index_response
        mock_opensearch_client.delete_provider_documents.return_value = {'deleted': 0, 'failures': []}
        return mock_opensearch_client

    def _generate_expected_document(self, compact: str, provider_id: str = None) -> dict:
        """Generate the expected document that should be indexed into OpenSearch."""
        if provider_id is None:
            provider_id = TEST_PROVIDER_ID_MAPPING[compact]

        license_type = TEST_LICENSE_TYPE_MAPPING[compact]
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
                'OldImage': image_data,
                'SequenceNumber': sequence_number,
                'SizeBytes': 256,
                'StreamViewType': 'NEW_AND_OLD_IMAGES',
            },
            'eventSourceARN': 'arn:aws:dynamodb:us-east-1:123456789012:table/provider-table/stream/1234',
        }

    # ---- INSERT/MODIFY path tests ----

    @patch('handlers.provider_update_ingest.opensearch_client')
    def test_opensearch_client_called_with_expected_parameters(self, mock_opensearch_client):
        """Test that OpenSearch client is called with expected parameters when indexing a record."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)
        self._put_test_provider_and_license_record_in_dynamodb_table('cosm')

        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                        )
                    ),
                }
            ]
        }

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        self.assertEqual(1, mock_opensearch_client.bulk_index.call_count)

        call_args = mock_opensearch_client.bulk_index.call_args
        self.assertEqual('compact_cosm_providers', call_args.kwargs['index_name'])
        self.assertEqual([self._generate_expected_document('cosm')], call_args.kwargs['documents'])
        self.assertEqual('documentId', call_args.kwargs['id_field'])

        self.assertEqual({'batchItemFailures': []}, result)

    @patch('handlers.provider_update_ingest.opensearch_client')
    def test_provider_ids_are_deduped_only_one_document_indexed(self, mock_opensearch_client):
        """Test that duplicate provider IDs in the batch are deduplicated."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)
        self._put_test_provider_and_license_record_in_dynamodb_table('cosm')

        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number-1',
                            event_name='INSERT',
                        )
                    ),
                },
                {
                    'messageId': '12346',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number-2',
                            event_name='MODIFY',
                        )
                    ),
                },
                {
                    'messageId': '12347',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number-3',
                            event_name='MODIFY',
                        )
                    ),
                },
            ]
        }

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        self.assertEqual(1, mock_opensearch_client.bulk_index.call_count)

        call_args = mock_opensearch_client.bulk_index.call_args
        self.assertEqual(1, len(call_args.kwargs['documents']))
        self.assertEqual(MOCK_COSM_PROVIDER_ID, call_args.kwargs['documents'][0]['providerId'])
        self.assertEqual('documentId', call_args.kwargs['id_field'])

        self.assertEqual({'batchItemFailures': []}, result)

    @patch('handlers.provider_update_ingest.opensearch_client')
    def test_validation_failure_returns_batch_item_failure(self, mock_opensearch_client):
        """Test that a record that fails validation is returned in batchItemFailures."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        provider = self.test_data_generator.generate_default_provider(
            value_overrides={
                'compact': 'cosm',
                'providerId': MOCK_COSM_PROVIDER_ID,
                'givenName': 'testGivenName',
                'familyName': 'testFamilyName',
            }
        )
        serialized_provider = provider.serialize_to_database_record()
        serialized_provider['compact'] = 'foo'
        self.config.provider_table.put_item(Item=serialized_provider)

        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                        )
                    ),
                }
            ]
        }

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        self.assertEqual(1, len(result['batchItemFailures']))
        self.assertEqual('12345', result['batchItemFailures'][0]['itemIdentifier'])

    @patch('handlers.provider_update_ingest.opensearch_client')
    def test_opensearch_indexing_failure_returns_batch_item_failure(self, mock_opensearch_client):
        """Test that a record which fails to be indexed by OpenSearch is in batchItemFailures."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        document_id = f'{MOCK_COSM_PROVIDER_ID}#oh#cosmetologist'
        mock_opensearch_client.bulk_index.return_value = {
            'errors': True,
            'items': [
                {
                    'index': {
                        '_id': document_id,
                        '_index': 'compact_cosm_providers',
                        'status': 400,
                        'error': {
                            'type': 'mapper_parsing_exception',
                            'reason': 'failed to parse field',
                        },
                    }
                },
            ],
        }

        self._put_test_provider_and_license_record_in_dynamodb_table('cosm')

        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number-1',
                        )
                    ),
                }
            ]
        }

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        self.assertEqual(1, len(result['batchItemFailures']))
        self.assertEqual('12345', result['batchItemFailures'][0]['itemIdentifier'])

    @patch('handlers.provider_update_ingest.opensearch_client')
    def test_bulk_index_exception_returns_all_batch_item_failures(self, mock_opensearch_client):
        """Test that when bulk_index raises an exception, all providers are marked as failed."""
        from cc_common.exceptions import CCInternalException
        from handlers.provider_update_ingest import provider_update_ingest_handler

        mock_opensearch_client.bulk_index.side_effect = CCInternalException('Connection timeout after 5 retries')

        self._put_test_provider_and_license_record_in_dynamodb_table('cosm')

        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number-1',
                        )
                    ),
                },
                {
                    'messageId': '12346',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number-2',
                        )
                    ),
                },
            ]
        }

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        self.assertEqual(2, len(result['batchItemFailures']))
        self.assertEqual('12345', result['batchItemFailures'][0]['itemIdentifier'])
        self.assertEqual('12346', result['batchItemFailures'][1]['itemIdentifier'])

    @patch('handlers.provider_update_ingest.opensearch_client')
    def test_empty_records_returns_empty_batch_failures(self, mock_opensearch_client):
        """Test that an empty Records list returns empty batchItemFailures."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        event = {'Records': []}

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        self.assertEqual({'batchItemFailures': []}, result)
        mock_opensearch_client.bulk_index.assert_not_called()

    @patch('handlers.provider_update_ingest.opensearch_client')
    def test_insert_event_without_old_image_indexes_successfully(self, mock_opensearch_client):
        """Test that INSERT events (newly created records) without OldImage are processed correctly."""
        from handlers.provider_update_ingest import provider_update_ingest_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)
        self._put_test_provider_and_license_record_in_dynamodb_table('cosm')

        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                            event_name='INSERT',
                            include_old_image=False,
                        )
                    ),
                }
            ]
        }

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        self.assertEqual(1, mock_opensearch_client.bulk_index.call_count)

        call_args = mock_opensearch_client.bulk_index.call_args
        self.assertEqual('compact_cosm_providers', call_args.kwargs['index_name'])
        self.assertEqual([self._generate_expected_document('cosm')], call_args.kwargs['documents'])
        self.assertEqual('documentId', call_args.kwargs['id_field'])

        # No delete_provider_documents should be called for INSERT events
        mock_opensearch_client.delete_provider_documents.assert_not_called()

        self.assertEqual({'batchItemFailures': []}, result)

    # ---- REMOVE event path tests ----

    @patch('handlers.provider_update_ingest.opensearch_client')
    def test_remove_event_with_remaining_records_deletes_then_reindexes(self, mock_opensearch_client):
        """Test that REMOVE events trigger delete_provider_documents then re-index remaining records.

        When a single record (e.g., a license) is deleted but the provider still has other records
        in DynamoDB, the handler should:
        1. Call delete_provider_documents to remove all documents for the provider
        2. Re-check DynamoDB and find the provider still exists
        3. Re-index the remaining license documents
        """
        from handlers.provider_update_ingest import provider_update_ingest_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Provider still exists in DynamoDB with remaining records
        self._put_test_provider_and_license_record_in_dynamodb_table('cosm')

        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record_with_old_image_only(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                        )
                    ),
                }
            ]
        }

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # delete_provider_documents should be called to remove all existing docs for this provider
        mock_opensearch_client.delete_provider_documents.assert_called_once_with(
            index_name='compact_cosm_providers',
            provider_id=MOCK_COSM_PROVIDER_ID,
        )

        # bulk_index should be called with the remaining documents
        self.assertEqual(1, mock_opensearch_client.bulk_index.call_count)
        call_args = mock_opensearch_client.bulk_index.call_args
        self.assertEqual('compact_cosm_providers', call_args.kwargs['index_name'])
        self.assertEqual([self._generate_expected_document('cosm')], call_args.kwargs['documents'])
        self.assertEqual('documentId', call_args.kwargs['id_field'])

        self.assertEqual({'batchItemFailures': []}, result)

    @patch('handlers.provider_update_ingest.opensearch_client')
    def test_remove_event_provider_fully_deleted_no_reindex(self, mock_opensearch_client):
        """Test that REMOVE events for a fully deleted provider just delete from OpenSearch.

        When a REMOVE event occurs and the provider no longer exists in DynamoDB at all,
        the handler should:
        1. Call delete_provider_documents to remove all documents for the provider
        2. Re-check DynamoDB and find the provider does NOT exist
        3. NOT attempt to re-index
        """
        from handlers.provider_update_ingest import provider_update_ingest_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Do NOT create any provider records in DynamoDB - provider is fully deleted

        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record_with_old_image_only(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                        )
                    ),
                }
            ]
        }

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # delete_provider_documents should be called
        mock_opensearch_client.delete_provider_documents.assert_called_once_with(
            index_name='compact_cosm_providers',
            provider_id=MOCK_COSM_PROVIDER_ID,
        )

        # bulk_index should NOT be called (provider no longer exists)
        mock_opensearch_client.bulk_index.assert_not_called()

        self.assertEqual({'batchItemFailures': []}, result)

    @patch('handlers.provider_update_ingest.opensearch_client')
    def test_delete_provider_documents_failure_returns_batch_item_failure(self, mock_opensearch_client):
        """Test that when delete_provider_documents fails, the provider is returned in batchItemFailures."""
        from cc_common.exceptions import CCInternalException
        from handlers.provider_update_ingest import provider_update_ingest_handler

        mock_opensearch_client.delete_provider_documents.side_effect = CCInternalException(
            'Connection timeout after 5 retries'
        )

        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record_with_old_image_only(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                        )
                    ),
                }
            ]
        }

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        self.assertEqual(1, len(result['batchItemFailures']))
        self.assertEqual('12345', result['batchItemFailures'][0]['itemIdentifier'])

    @patch('handlers.provider_update_ingest.opensearch_client')
    def test_cc_not_found_on_non_remove_event_logs_warning_no_reindex(self, mock_opensearch_client):
        """Test that CCNotFoundException on a non-REMOVE event logs a warning without re-indexing.

        This is a safety net for race conditions where a MODIFY/INSERT event arrives but the
        provider has already been deleted from DynamoDB. The handler should log a warning
        and NOT attempt to re-index.
        """
        from handlers.provider_update_ingest import provider_update_ingest_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Do NOT create any provider records in DynamoDB - simulates race condition
        # where provider was deleted between event creation and processing

        event = {
            'Records': [
                {
                    'messageId': '12345',
                    'body': json.dumps(
                        self._create_dynamodb_stream_record(
                            compact='cosm',
                            provider_id=MOCK_COSM_PROVIDER_ID,
                            sequence_number='some-sequence-number',
                            event_name='MODIFY',
                        )
                    ),
                }
            ]
        }

        mock_context = MagicMock()
        result = provider_update_ingest_handler(event, mock_context)

        # delete_provider_documents should be called to remove documents from OpenSearch
        mock_opensearch_client.delete_provider_documents.assert_called_once_with(
            index_name='compact_cosm_providers',
            provider_id=MOCK_COSM_PROVIDER_ID,
        )

        # No bulk_index should be called (no documents to index)
        mock_opensearch_client.bulk_index.assert_not_called()

        # No batch failures - this is expected behavior for a race condition
        self.assertEqual({'batchItemFailures': []}, result)
