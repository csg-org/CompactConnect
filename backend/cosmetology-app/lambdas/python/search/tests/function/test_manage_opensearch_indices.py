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
        default_properties = {
            'numberOfShards': 1,
            'numberOfReplicas': 0,
        }
        if properties:
            default_properties.update(properties)
        return {
            'RequestType': request_type,
            'ResourceProperties': default_properties,
        }

    def _when_testing_mock_opensearch_client(
        self,
        mock_opensearch_client,
        alias_exists_return_value: bool | dict = False,
        index_exists_return_value: bool | dict = False,
    ):
        """
        Configure the mock OpenSearchClient for testing.

        :param mock_opensearch_client: The patched OpenSearchClient class
        :param alias_exists_return_value: Either a boolean (applied to all aliases)
            or a dict mapping alias names to booleans
        :param index_exists_return_value: Either a boolean (applied to all indices)
            or a dict mapping index names to booleans
        :return: The mock client instance
        """
        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance

        # Configure cluster_health mock (used by _wait_for_domain_ready)
        mock_client_instance.cluster_health.return_value = {
            'status': 'green',
            'number_of_nodes': 1,
            'cluster_name': 'test-cluster',
        }

        # Configure alias_exists mock
        if isinstance(alias_exists_return_value, dict):
            mock_client_instance.alias_exists.side_effect = lambda alias_name: alias_exists_return_value.get(
                alias_name, False
            )
        else:
            mock_client_instance.alias_exists.return_value = alias_exists_return_value

        # Configure index_exists mock
        if isinstance(index_exists_return_value, dict):
            mock_client_instance.index_exists.side_effect = lambda index_name: index_exists_return_value.get(
                index_name, False
            )
        else:
            mock_client_instance.index_exists.return_value = index_exists_return_value

        return mock_client_instance

    @patch('handlers.manage_opensearch_indices.OpenSearchClient')
    def test_on_create_creates_versioned_indices_and_aliases_for_all_compacts_when_none_exist(
        self, mock_opensearch_client
    ):
        """Test that on_create creates versioned indices and aliases for all compacts when they don't exist."""
        from handlers.manage_opensearch_indices import on_event

        # Set up the mock opensearch client - no aliases or indices exist
        mock_client_instance = self._when_testing_mock_opensearch_client(
            mock_opensearch_client, alias_exists_return_value=False, index_exists_return_value=False
        )

        # Create the event for a 'Create' request with explicit shard/replica configuration
        event = self._create_event('Create', {'numberOfShards': 2, 'numberOfReplicas': 1})

        # Call the handler
        on_event(event, self.mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        # Assert that alias_exists was called for each compact
        expected_alias_exists_calls = [call('compact_cosm_providers')]
        mock_client_instance.alias_exists.assert_has_calls(expected_alias_exists_calls, any_order=False)
        self.assertEqual(1, mock_client_instance.alias_exists.call_count)

        # Assert that create_index was called for each compact with versioned names
        self.assertEqual(1, mock_client_instance.create_index.call_count)

        # Verify the versioned index names in create_index calls
        create_index_calls = mock_client_instance.create_index.call_args_list
        index_names_created = [call_args[0][0] for call_args in create_index_calls]
        self.assertEqual(
            ['compact_cosm_providers_v1'],
            index_names_created,
        )

        # Assert that create_alias was called for each compact
        self.assertEqual(1, mock_client_instance.create_alias.call_count)
        expected_alias_calls = [
            call('compact_cosm_providers_v1', 'compact_cosm_providers'),
        ]
        mock_client_instance.create_alias.assert_has_calls(expected_alias_calls, any_order=False)

        # Verify the mapping was passed to create_index with correct shard/replica configuration
        for call_args in create_index_calls:
            index_mapping = call_args[0][1]
            # Verify the index settings use the provided shard/replica values
            self.assertEqual(2, index_mapping['settings']['index']['number_of_shards'])
            self.assertEqual(1, index_mapping['settings']['index']['number_of_replicas'])
            # Verify the mapping has the expected structure
            self.assertEqual(
                {
                    'mappings': {
                        'properties': {
                            'birthMonthDay': {'type': 'keyword'},
                            'compact': {'type': 'keyword'},
                            'compactEligibility': {'type': 'keyword'},
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
                        'index': {'number_of_replicas': 1, 'number_of_shards': 2},
                    },
                },
                index_mapping,
            )

    @patch('handlers.manage_opensearch_indices.OpenSearchClient')
    def test_on_create_skips_index_and_alias_creation_when_all_aliases_exist(self, mock_opensearch_client):
        """Test that on_create skips index and alias creation when aliases already exist."""
        from handlers.manage_opensearch_indices import on_event

        # Set up the mock opensearch client - all aliases exist (meaning indices are already set up)
        mock_client_instance = self._when_testing_mock_opensearch_client(
            mock_opensearch_client, alias_exists_return_value=True
        )

        # Create the event for a 'Create' request
        event = self._create_event('Create')

        # Call the handler
        on_event(event, self.mock_context)

        # Assert that the OpenSearchClient was instantiated
        mock_opensearch_client.assert_called_once()

        # Assert that alias_exists was called for each compact
        self.assertEqual(1, mock_client_instance.alias_exists.call_count)

        # Assert that index_exists was NOT called since aliases already exist
        mock_client_instance.index_exists.assert_not_called()

        # Assert that create_index was NOT called since aliases already exist
        mock_client_instance.create_index.assert_not_called()

        # Assert that create_alias was NOT called since aliases already exist
        mock_client_instance.create_alias.assert_not_called()

    @patch('handlers.manage_opensearch_indices.OpenSearchClient')
    def test_on_create_creates_alias_only_when_index_exists_but_alias_does_not(self, mock_opensearch_client):
        """Test that on_create creates only the alias when the index exists but the alias doesn't."""
        from handlers.manage_opensearch_indices import on_event

        # Set up the mock opensearch client - index exists but alias doesn't (edge case)
        mock_client_instance = self._when_testing_mock_opensearch_client(
            mock_opensearch_client,
            alias_exists_return_value=False,
            index_exists_return_value={
                'compact_cosm_providers_v1': True,
            },
        )

        # Create the event for a 'Create' request
        event = self._create_event('Create')

        # Call the handler
        on_event(event, self.mock_context)

        # Assert that alias_exists was called for each compact
        self.assertEqual(1, mock_client_instance.alias_exists.call_count)

        # Assert that index_exists was called for each compact
        self.assertEqual(1, mock_client_instance.index_exists.call_count)

        # Assert that create_index was NOT called since indices already exist
        mock_client_instance.create_index.assert_not_called()

        # Assert that create_alias was called for each compact (to create the missing aliases)
        self.assertEqual(1, mock_client_instance.create_alias.call_count)
        expected_alias_calls = [
            call('compact_cosm_providers_v1', 'compact_cosm_providers'),
        ]
        mock_client_instance.create_alias.assert_has_calls(expected_alias_calls, any_order=False)

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

    @patch('handlers.manage_opensearch_indices.time.sleep')
    @patch('handlers.manage_opensearch_indices.OpenSearchClient')
    def test_on_create_retries_when_domain_not_immediately_responsive(self, mock_opensearch_client, mock_sleep):
        """Test that on_create retries connecting to the domain when it's not immediately responsive."""
        from cc_common.exceptions import CCInternalException
        from handlers.manage_opensearch_indices import on_event

        # First two calls fail, third succeeds
        mock_client_instance = Mock()
        mock_client_instance.cluster_health.return_value = {
            'status': 'green',
            'number_of_nodes': 1,
        }
        mock_client_instance.alias_exists.return_value = True  # Skip index creation for simplicity

        call_count = 0

        def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise CCInternalException('cluster_health failed after 5 attempts. Last error: ConnectionTimeout')
            return mock_client_instance

        mock_opensearch_client.side_effect = side_effect

        # Create the event for a 'Create' request
        event = self._create_event('Create')

        # Call the handler
        on_event(event, self.mock_context)

        # Assert that OpenSearchClient was instantiated 3 times (2 failures + 1 success)
        self.assertEqual(3, mock_opensearch_client.call_count)

        # Assert that sleep was called twice (once between each retry)
        self.assertEqual(2, mock_sleep.call_count)

    @patch('handlers.manage_opensearch_indices.time.sleep')
    @patch('handlers.manage_opensearch_indices.OpenSearchClient')
    def test_on_create_raises_after_max_retries(self, mock_opensearch_client, mock_sleep):  # noqa ARG002 unused-argument
        """Test that on_create raises CCInternalException after max retries are exhausted."""
        from cc_common.exceptions import CCInternalException
        from handlers.manage_opensearch_indices import (
            DOMAIN_READINESS_MAX_ATTEMPTS,
            on_event,
        )

        # All calls fail
        mock_opensearch_client.side_effect = CCInternalException(
            'cluster_health failed after 5 attempts. Last error: ConnectionTimeout'
        )

        # Create the event for a 'Create' request
        event = self._create_event('Create')

        # Call the handler and expect an exception
        with self.assertRaises(CCInternalException) as context:
            on_event(event, self.mock_context)

        # Verify the error message mentions the number of attempts
        self.assertIn(str(DOMAIN_READINESS_MAX_ATTEMPTS), str(context.exception))
        self.assertIn('did not become responsive', str(context.exception))

        # Assert that OpenSearchClient was instantiated max attempts times
        self.assertEqual(DOMAIN_READINESS_MAX_ATTEMPTS, mock_opensearch_client.call_count)
