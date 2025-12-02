from unittest.mock import Mock, call, patch

from moto import mock_aws

from . import TstFunction


@mock_aws
class TestOpenSearchIndexManager(TstFunction):
    """Test suite for OpenSearchIndexManager custom resource."""

    def setUp(self):
        super().setUp()

    def _create_event(self, request_type: str, properties: dict = None) -> dict:
        """Create a CloudFormation custom resource event."""
        return {
            'RequestType': request_type,
            'ResourceProperties': properties or {},
        }

    def _when_testing_mock_opensearch_client(
        self, mock_opensearch_client, index_exists_return_value: bool | dict = False
    ):
        """
        Configure the mock OpenSearchClient for testing.

        :param mock_opensearch_client: The patched OpenSearchClient class
        :param index_exists_return_value: Either a boolean (applied to all indices)
            or a dict mapping index names to booleans
        :return: The mock client instance
        """
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance

        # If a dict is provided, use side_effect to return different values per index
        if isinstance(index_exists_return_value, dict):
            mock_client_instance.index_exists.side_effect = lambda index_name: index_exists_return_value.get(
                index_name, False
            )
        else:
            mock_client_instance.index_exists.return_value = index_exists_return_value

        return mock_client_instance

    @patch('handlers.manage_opensearch_indices.OpenSearchClient')
    def test_on_create_creates_indices_for_all_compacts_when_none_exist(self, mock_opensearch_client):
        """Test that on_create creates indices for all compacts when they don't exist."""
        from handlers.manage_opensearch_indices import on_event

        # Set up the mock opensearch client - no indices exist
        mock_client_instance = self._when_testing_mock_opensearch_client(
            mock_opensearch_client, index_exists_return_value=False
        )

        # Create the event for a 'Create' request
        event = self._create_event('Create')

        # Call the handler
        on_event(event, self.mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        # Assert that index_exists was called for each compact
        expected_index_exists_calls = [
            call('compact_aslp_providers'),
            call('compact_octp_providers'),
            call('compact_coun_providers'),
        ]
        mock_client_instance.index_exists.assert_has_calls(expected_index_exists_calls, any_order=False)
        self.assertEqual(3, mock_client_instance.index_exists.call_count)

        # Assert that create_index was called for each compact
        self.assertEqual(3, mock_client_instance.create_index.call_count)

        # Verify the index names in create_index calls
        create_index_calls = mock_client_instance.create_index.call_args_list
        index_names_created = [call_args[0][0] for call_args in create_index_calls]
        self.assertEqual(
            ['compact_aslp_providers', 'compact_octp_providers', 'compact_coun_providers'],
            index_names_created,
        )

        # Verify the mapping was passed to create_index
        for call_args in create_index_calls:
            index_mapping = call_args[0][1]
            # Verify the mapping has the expected structure
            self.assertEqual(
                {
                    'mappings': {
                        'properties': {
                            'birthMonthDay': {'type': 'keyword'},
                            'compact': {'type': 'keyword'},
                            'compactConnectRegisteredEmailAddress': {'type': 'keyword'},
                            'compactEligibility': {'type': 'keyword'},
                            'currentHomeJurisdiction': {'type': 'keyword'},
                            'dateOfExpiration': {'type': 'date'},
                            'dateOfUpdate': {'type': 'date'},
                            'familyName': {
                                'analyzer': 'custom_ascii_analyzer',
                                'fields': {'keyword': {'ignore_above': 256, 'type': 'keyword'}},
                                'type': 'text',
                            },
                            'givenName': {
                                'analyzer': 'custom_ascii_analyzer',
                                'fields': {'keyword': {'ignore_above': 256, 'type': 'keyword'}},
                                'type': 'text',
                            },
                            'jurisdictionUploadedCompactEligibility': {'type': 'keyword'},
                            'jurisdictionUploadedLicenseStatus': {'type': 'keyword'},
                            'licenseJurisdiction': {'type': 'keyword'},
                            'licenseStatus': {'type': 'keyword'},
                            'licenses': {
                                'properties': {
                                    'adverseActions': {
                                        'properties': {
                                            'actionAgainst': {'type': 'keyword'},
                                            'adverseActionId': {'type': 'keyword'},
                                            'clinicalPrivilegeActionCategories': {'type': 'keyword'},
                                            'clinicalPrivilegeActionCategory': {'type': 'keyword'},
                                            'compact': {'type': 'keyword'},
                                            'creationDate': {'type': 'date'},
                                            'dateOfUpdate': {'type': 'date'},
                                            'effectiveLiftDate': {'type': 'date'},
                                            'effectiveStartDate': {'type': 'date'},
                                            'encumbranceType': {'type': 'keyword'},
                                            'jurisdiction': {'type': 'keyword'},
                                            'licenseType': {'type': 'keyword'},
                                            'licenseTypeAbbreviation': {'type': 'keyword'},
                                            'liftingUser': {'type': 'keyword'},
                                            'providerId': {'type': 'keyword'},
                                            'submittingUser': {'type': 'keyword'},
                                            'type': {'type': 'keyword'},
                                        },
                                        'type': 'nested',
                                    },
                                    'compact': {'type': 'keyword'},
                                    'compactEligibility': {'type': 'keyword'},
                                    'dateOfExpiration': {'type': 'date'},
                                    'dateOfIssuance': {'type': 'date'},
                                    'dateOfRenewal': {'type': 'date'},
                                    'dateOfUpdate': {'type': 'date'},
                                    'emailAddress': {'type': 'keyword'},
                                    'familyName': {
                                        'analyzer': 'custom_ascii_analyzer',
                                        'fields': {'keyword': {'ignore_above': 256, 'type': 'keyword'}},
                                        'type': 'text',
                                    },
                                    'givenName': {
                                        'analyzer': 'custom_ascii_analyzer',
                                        'fields': {'keyword': {'ignore_above': 256, 'type': 'keyword'}},
                                        'type': 'text',
                                    },
                                    'homeAddressCity': {
                                        'analyzer': 'custom_ascii_analyzer',
                                        'fields': {'keyword': {'ignore_above': 256, 'type': 'keyword'}},
                                        'type': 'text',
                                    },
                                    'homeAddressPostalCode': {'type': 'keyword'},
                                    'homeAddressState': {'type': 'keyword'},
                                    'homeAddressStreet1': {'type': 'text'},
                                    'homeAddressStreet2': {'type': 'text'},
                                    'investigationStatus': {'type': 'keyword'},
                                    'investigations': {
                                        'properties': {
                                            'compact': {'type': 'keyword'},
                                            'dateOfUpdate': {'type': 'date'},
                                            'investigationId': {'type': 'keyword'},
                                            'jurisdiction': {'type': 'keyword'},
                                            'licenseType': {'type': 'keyword'},
                                            'status': {'type': 'keyword'},
                                            'type': {'type': 'keyword'},
                                        },
                                        'type': 'nested',
                                    },
                                    'jurisdiction': {'type': 'keyword'},
                                    'jurisdictionUploadedCompactEligibility': {'type': 'keyword'},
                                    'jurisdictionUploadedLicenseStatus': {'type': 'keyword'},
                                    'licenseNumber': {'type': 'keyword'},
                                    'licenseStatus': {'type': 'keyword'},
                                    'licenseStatusName': {'type': 'keyword'},
                                    'licenseType': {'type': 'keyword'},
                                    'middleName': {
                                        'analyzer': 'custom_ascii_analyzer',
                                        'fields': {'keyword': {'ignore_above': 256, 'type': 'keyword'}},
                                        'type': 'text',
                                    },
                                    'npi': {'type': 'keyword'},
                                    'phoneNumber': {'type': 'keyword'},
                                    'providerId': {'type': 'keyword'},
                                    'suffix': {'type': 'keyword'},
                                    'type': {'type': 'keyword'},
                                },
                                'type': 'nested',
                            },
                            'middleName': {
                                'analyzer': 'custom_ascii_analyzer',
                                'fields': {'keyword': {'ignore_above': 256, 'type': 'keyword'}},
                                'type': 'text',
                            },
                            'militaryAffiliations': {
                                'properties': {
                                    'affiliationType': {'type': 'keyword'},
                                    'compact': {'type': 'keyword'},
                                    'dateOfUpdate': {'type': 'date'},
                                    'dateOfUpload': {'type': 'date'},
                                    'fileNames': {'type': 'keyword'},
                                    'providerId': {'type': 'keyword'},
                                    'status': {'type': 'keyword'},
                                    'type': {'type': 'keyword'},
                                },
                                'type': 'nested',
                            },
                            'npi': {'type': 'keyword'},
                            'privilegeJurisdictions': {'type': 'keyword'},
                            'privileges': {
                                'properties': {
                                    'activeSince': {'type': 'date'},
                                    'administratorSetStatus': {'type': 'keyword'},
                                    'adverseActions': {
                                        'properties': {
                                            'actionAgainst': {'type': 'keyword'},
                                            'adverseActionId': {'type': 'keyword'},
                                            'clinicalPrivilegeActionCategories': {'type': 'keyword'},
                                            'clinicalPrivilegeActionCategory': {'type': 'keyword'},
                                            'compact': {'type': 'keyword'},
                                            'creationDate': {'type': 'date'},
                                            'dateOfUpdate': {'type': 'date'},
                                            'effectiveLiftDate': {'type': 'date'},
                                            'effectiveStartDate': {'type': 'date'},
                                            'encumbranceType': {'type': 'keyword'},
                                            'jurisdiction': {'type': 'keyword'},
                                            'licenseType': {'type': 'keyword'},
                                            'licenseTypeAbbreviation': {'type': 'keyword'},
                                            'liftingUser': {'type': 'keyword'},
                                            'providerId': {'type': 'keyword'},
                                            'submittingUser': {'type': 'keyword'},
                                            'type': {'type': 'keyword'},
                                        },
                                        'type': 'nested',
                                    },
                                    'attestations': {
                                        'properties': {
                                            'attestationId': {'type': 'keyword'},
                                            'version': {'type': 'keyword'},
                                        },
                                        'type': 'nested',
                                    },
                                    'compact': {'type': 'keyword'},
                                    'compactTransactionId': {'type': 'keyword'},
                                    'dateOfExpiration': {'type': 'date'},
                                    'dateOfIssuance': {'type': 'date'},
                                    'dateOfRenewal': {'type': 'date'},
                                    'dateOfUpdate': {'type': 'date'},
                                    'investigationStatus': {'type': 'keyword'},
                                    'investigations': {
                                        'properties': {
                                            'compact': {'type': 'keyword'},
                                            'dateOfUpdate': {'type': 'date'},
                                            'investigationId': {'type': 'keyword'},
                                            'jurisdiction': {'type': 'keyword'},
                                            'licenseType': {'type': 'keyword'},
                                            'status': {'type': 'keyword'},
                                            'type': {'type': 'keyword'},
                                        },
                                        'type': 'nested',
                                    },
                                    'jurisdiction': {'type': 'keyword'},
                                    'licenseJurisdiction': {'type': 'keyword'},
                                    'licenseType': {'type': 'keyword'},
                                    'privilegeId': {'type': 'keyword'},
                                    'providerId': {'type': 'keyword'},
                                    'status': {'type': 'keyword'},
                                    'type': {'type': 'keyword'},
                                },
                                'type': 'nested',
                            },
                            'providerDateOfUpdate': {'type': 'date'},
                            'providerFamGivMid': {'type': 'keyword'},
                            'providerId': {'type': 'keyword'},
                            'suffix': {'type': 'keyword'},
                            'type': {'type': 'keyword'},
                        }
                    },
                    'settings': {
                        'analysis': {
                            'analyzer': {
                                'custom_ascii_analyzer': {
                                    'filter': ['lowercase', 'custom_ascii_folding'],
                                    'tokenizer': 'standard',
                                    'type': 'custom',
                                }
                            },
                            'filter': {'custom_ascii_folding': {'preserve_original': True, 'type': 'asciifolding'}},
                        },
                        'index': {'number_of_replicas': 0, 'number_of_shards': 1},
                    },
                },
                index_mapping,
            )

    @patch('handlers.manage_opensearch_indices.OpenSearchClient')
    def test_on_create_skips_index_creation_when_all_indices_exist(self, mock_opensearch_client):
        """Test that on_create skips index creation when indices already exist."""
        from handlers.manage_opensearch_indices import on_event

        # Set up the mock opensearch client - all indices exist
        mock_client_instance = self._when_testing_mock_opensearch_client(
            mock_opensearch_client, index_exists_return_value=True
        )

        # Create the event for a 'Create' request
        event = self._create_event('Create')

        # Call the handler
        on_event(event, self.mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        # Assert that index_exists was called for each compact
        self.assertEqual(3, mock_client_instance.index_exists.call_count)

        # Assert that create_index was NOT called since indices already exist
        mock_client_instance.create_index.assert_not_called()

    @patch('handlers.manage_opensearch_indices.OpenSearchClient')
    def test_on_create_only_creates_missing_indices(self, mock_opensearch_client):
        """Test that on_create only creates indices that don't exist."""
        from handlers.manage_opensearch_indices import on_event

        # Set up the mock opensearch client - only aslp index exists
        mock_client_instance = self._when_testing_mock_opensearch_client(
            mock_opensearch_client,
            index_exists_return_value={
                'compact_aslp_providers': True,
                'compact_octp_providers': False,
                'compact_coun_providers': False,
            },
        )

        # Create the event for a 'Create' request
        event = self._create_event('Create')

        # Call the handler
        on_event(event, self.mock_context)

        # Assert that index_exists was called for each compact
        self.assertEqual(3, mock_client_instance.index_exists.call_count)

        # Assert that create_index was called only for missing indices (octp and coun)
        self.assertEqual(2, mock_client_instance.create_index.call_count)

        # Verify the correct indices were created
        create_index_calls = mock_client_instance.create_index.call_args_list
        index_names_created = [call_args[0][0] for call_args in create_index_calls]
        self.assertEqual(['compact_octp_providers', 'compact_coun_providers'], index_names_created)

    @patch('handlers.manage_opensearch_indices.OpenSearchClient')
    def test_on_update_is_noop(self, mock_opensearch_client):
        """Test that on_update does not create or modify indices."""
        from handlers.manage_opensearch_indices import on_event

        # Create the event for an 'Update' request
        event = self._create_event('Update')

        # Call the handler
        result = on_event(event, self.mock_context)

        # Assert that the OpenSearchClient was NOT instantiated
        mock_opensearch_client.assert_not_called()

        # Result should be None (no-op)
        self.assertIsNone(result)

    @patch('handlers.manage_opensearch_indices.OpenSearchClient')
    def test_on_delete_is_noop(self, mock_opensearch_client):
        """Test that on_delete does not delete indices."""
        from handlers.manage_opensearch_indices import on_event

        # Create the event for a 'Delete' request
        event = self._create_event('Delete')

        # Call the handler
        result = on_event(event, self.mock_context)

        # Assert that the OpenSearchClient was NOT instantiated
        mock_opensearch_client.assert_not_called()

        # Result should be None (no-op)
        self.assertIsNone(result)
