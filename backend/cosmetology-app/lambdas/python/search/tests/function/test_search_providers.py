import json
from unittest.mock import patch

from cc_common.exceptions import CCInvalidRequestException
from moto import mock_aws

from . import TstFunction


@mock_aws
class TestSearchProviders(TstFunction):
    """Test suite for search_api_handler - provider search functionality."""

    def setUp(self):
        super().setUp()

    def _create_api_event(
        self,
        compact: str,
        body: dict = None,
        scopes_override: str = None,
    ) -> dict:
        """Create a standard API Gateway event for search_providers."""
        return {
            'resource': '/v1/compacts/{compact}/providers/search',
            'path': f'/v1/compacts/{compact}/providers/search',
            'httpMethod': 'POST',
            'headers': {
                'accept': 'application/json',
                'content-type': 'application/json',
                'Content-Type': 'application/json',
                'origin': 'https://example.org',
                'Host': 'api.test.example.com',
            },
            'multiValueHeaders': {},
            'queryStringParameters': None,
            'pathParameters': {'compact': compact},
            'requestContext': {
                'resourcePath': '/v1/compacts/{compact}/providers/search',
                'httpMethod': 'POST',
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-id',
                        'cognito:username': 'test-user',
                        'scope': f'openid email {compact}/readGeneral' if not scopes_override else scopes_override,
                    }
                },
            },
            'body': json.dumps(body) if body else None,
            'isBase64Encoded': False,
        }

    def _when_testing_mock_opensearch_client(self, mock_opensearch_client, search_response: dict = None):
        """
        Configure the mock OpenSearchClient for testing.

        :param mock_opensearch_client: The patched opensearch_client instance
        :param search_response: The response to return from the search method
        :return: The mock client instance
        """
        if not search_response:
            search_response = {
                'hits': {
                    'total': {'value': 0, 'relation': 'eq'},
                    'hits': [],
                }
            }

        # mock_opensearch_client is the patched instance, not the class
        mock_opensearch_client.search.return_value = search_response
        return mock_opensearch_client

    def _create_mock_provider_hit(
        self,
        provider_id: str = '00000000-0000-0000-0000-000000000001',
        compact: str = 'cosm',
        sort_values: list = None,
    ) -> dict:
        """Create a mock OpenSearch hit for a provider document."""
        hit = {
            '_index': f'compact_{compact}_providers',
            '_id': provider_id,
            '_score': 1.0,
            '_source': {
                'providerId': provider_id,
                'type': 'provider',
                'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                'compact': compact,
                'licenseJurisdiction': 'oh',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
                'givenName': 'John',
                'familyName': 'Doe',
                'dateOfExpiration': '2025-12-31',
                'jurisdictionUploadedLicenseStatus': 'active',
                'jurisdictionUploadedCompactEligibility': 'eligible',
                'birthMonthDay': '06-15',
                # adding a couple of fields that are not recognized in the
                # ProviderGeneralResponseSchema. Although these are not currently
                # stored in OpenSearch, this mock data ensures we are sanitizing
                # these private fields by the search serialization logic
                'someNewField': 'somePrivateValue',
                'ssnLastFour': '1234',
                'emailAddress': 'someemail@address.com',
                'dateOfBirth': '1984-12-11',
            },
        }
        if sort_values:
            hit['sort'] = sort_values
        return hit

    @patch('handlers.search.opensearch_client')
    def test_basic_search_with_match_all_query(self, mock_opensearch_client):
        """Test that a basic search with no query uses match_all."""
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Create event with minimal body - just the required query field
        event = self._create_api_event(compact='cosm', body={'query': {'match_all': {}}})

        response = search_api_handler(event, self.mock_context)

        # Verify search was called
        mock_opensearch_client.search.assert_called_once()

        # Verify the search was called with correct parameters
        mock_opensearch_client.search.assert_called_once_with(
            index_name='compact_cosm_providers', body={'query': {'match_all': {}}, 'size': 100}
        )

        # Verify response structure
        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])
        self.assertEqual({'providers': [], 'total': {'relation': 'eq', 'value': 0}}, body)

    @patch('handlers.search.opensearch_client')
    def test_search_with_custom_query(self, mock_opensearch_client):
        """Test that a custom OpenSearch query is passed through correctly."""
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Create a custom bool query
        custom_query = {
            'bool': {
                'must': [
                    {'match': {'givenName': 'John'}},
                    {'term': {'licenseStatus': 'active'}},
                ]
            }
        }
        event = self._create_api_event('cosm', body={'query': custom_query, 'from': 20})

        search_api_handler(event, self.mock_context)

        # Verify the custom query was passed through
        mock_opensearch_client.search.assert_called_once_with(
            index_name='compact_cosm_providers',
            body={
                'query': {'bool': {'must': [{'match': {'givenName': 'John'}}, {'term': {'licenseStatus': 'active'}}]}},
                'size': 100,
                'from': 20,
            },
        )

    @patch('handlers.search.opensearch_client')
    def test_search_size_capped_at_max(self, mock_opensearch_client):
        """Test that size parameter is capped at MAX_SIZE (100)."""
        from handlers.search import search_api_handler

        # Request size larger than MAX_SIZE
        event = self._create_api_event('cosm', body={'query': {'match_all': {}}, 'size': 500})

        result = search_api_handler(event, self.mock_context)
        self.assertEqual(400, result['statusCode'])
        self.assertEqual(
            {
                'message': 'Invalid request: '
                "{'size': ['Must be greater than or equal to 1 and less than or equal to 100.']}"
            },
            json.loads(result['body']),
        )
        mock_opensearch_client.search.assert_not_called()

    @patch('handlers.search.opensearch_client')
    def test_search_with_sort_parameter(self, mock_opensearch_client):
        """Test that sort parameter is included in the search body."""
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        sort_config = [{'providerId': 'asc'}, {'dateOfUpdate': 'desc'}]
        search_after_values = ['provider-uuid-123']
        event = self._create_api_event(
            'cosm',
            body={
                'query': {'match_all': {}},
                'sort': sort_config,
                'search_after': search_after_values,
            },
        )

        search_api_handler(event, self.mock_context)

        mock_opensearch_client.search.assert_called_once_with(
            index_name='compact_cosm_providers',
            body={
                'query': {'match_all': {}},
                'size': 100,
                'sort': sort_config,
                'search_after': search_after_values,
            },
        )

    @patch('handlers.search.opensearch_client')
    def test_search_after_without_sort_returns_400(self, mock_opensearch_client):
        """Test that search_after without sort raises an error."""
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # search_after without sort should fail
        event = self._create_api_event(
            'cosm',
            body={
                'query': {'match_all': {}},
                'search_after': ['provider-uuid-123'],
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('sort is required when using search_after pagination', body['message'])

    def test_invalid_request_body_returns_400(self):
        """Test that an invalid request body returns a 400 error."""
        from handlers.search import search_api_handler

        # Create event with missing required 'query' field
        event = self._create_api_event('cosm', body={'size': 10})

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Invalid request', body['message'])

    @patch('handlers.search.opensearch_client')
    def test_search_returns_sanitized_providers(self, mock_opensearch_client):
        """Test that provider records are sanitized through ProviderGeneralResponseSchema."""
        from handlers.search import search_api_handler

        # Create a mock response with provider hits
        mock_hit = self._create_mock_provider_hit()
        search_response = {
            'hits': {
                'total': {'value': 1, 'relation': 'eq'},
                'hits': [mock_hit],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        event = self._create_api_event('cosm', body={'query': {'match_all': {}}})

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])
        self.assertEqual(
            {
                'providers': [
                    {
                        'birthMonthDay': '06-15',
                        'compact': 'cosm',
                        'compactEligibility': 'eligible',
                        'dateOfExpiration': '2025-12-31',
                        'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                        'familyName': 'Doe',
                        'givenName': 'John',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'licenseJurisdiction': 'oh',
                        'licenseStatus': 'active',
                        'providerId': '00000000-0000-0000-0000-000000000001',
                        'type': 'provider',
                    }
                ],
                'total': {'relation': 'eq', 'value': 1},
            },
            body,
        )

    @patch('handlers.search.opensearch_client')
    def test_search_response_includes_last_sort_for_pagination(self, mock_opensearch_client):
        """Test that lastSort is included in response for search_after pagination."""
        from handlers.search import search_api_handler

        # Create hits with sort values
        mock_hit = self._create_mock_provider_hit(sort_values=['provider-uuid-123', '2024-01-15T10:30:00+00:00'])
        search_response = {
            'hits': {
                'total': {'value': 1, 'relation': 'eq'},
                'hits': [mock_hit],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        event = self._create_api_event(
            'cosm',
            body={
                'query': {'match_all': {}},
                'sort': [{'providerId': 'asc'}, {'dateOfUpdate': 'asc'}],
            },
        )

        response = search_api_handler(event, self.mock_context)

        body = json.loads(response['body'])
        self.assertIn('lastSort', body)
        self.assertEqual(['provider-uuid-123', '2024-01-15T10:30:00+00:00'], body['lastSort'])

    @patch('handlers.search.opensearch_client')
    def test_search_uses_correct_index_for_compact(self, mock_opensearch_client):
        """Test that the correct index name is used based on the compact parameter."""
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        # Test with different compacts
        for compact in ['cosm']:
            mock_opensearch_client.reset_mock()

            event = self._create_api_event(compact, body={'query': {'match_all': {}}})
            search_api_handler(event, self.mock_context)

            call_args = mock_opensearch_client.search.call_args
            self.assertEqual(f'compact_{compact}_providers', call_args.kwargs['index_name'])

    def test_missing_scopes_returns_403(self):
        """Test that missing auth scope returns a 403 error."""
        from handlers.search import search_api_handler

        # Create event with unsupported route
        event = self._create_api_event(compact='cosm', scopes_override='openid email')

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(403, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Access denied', body['message'])

    def test_query_with_index_key_returns_400(self):
        """Test that queries containing 'index' key are rejected with 400 error."""
        from handlers.search import search_api_handler

        # Test with 'index' key (terms lookup attack pattern)
        event = self._create_api_event(
            'cosm',
            body={
                'query': {
                    'terms': {
                        'providerId': {
                            'index': 'compact_cosm_providers',
                            'id': 'some-uuid',
                            'path': 'providerId',
                        }
                    }
                }
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Cross-index queries are not allowed', body['message'])
        self.assertIn("'index'", body['message'])

    def test_query_with_underscore_index_key_returns_400(self):
        """Test that queries containing '_index' key are rejected with 400 error."""
        from handlers.search import search_api_handler

        # Test with '_index' key (more_like_this attack pattern)
        event = self._create_api_event(
            'cosm',
            body={
                'query': {
                    'more_like_this': {
                        'fields': ['familyName', 'givenName'],
                        'like': [
                            {
                                '_index': 'compact_cosm_providers',
                                '_id': 'target-provider-uuid',
                            }
                        ],
                    }
                }
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Cross-index queries are not allowed', body['message'])
        self.assertIn("'_index'", body['message'])

    def test_query_with_nested_index_key_returns_400(self):
        """Test that queries with nested 'index' key at any level are rejected."""
        from handlers.search import search_api_handler

        # Test with 'index' key nested deep in the query structure
        event = self._create_api_event(
            'cosm',
            body={
                'query': {
                    'bool': {
                        'should': [
                            {
                                'terms': {
                                    'familyName.keyword': {
                                        'index': 'compact_cosm_providers',
                                        'id': 'target-uuid',
                                        'path': 'familyName.keyword',
                                    }
                                }
                            }
                        ]
                    }
                }
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Cross-index queries are not allowed', body['message'])
        self.assertIn("'index'", body['message'])

    @patch('handlers.search.opensearch_client')
    def test_opensearch_request_error_returns_400_with_error_message(self, mock_opensearch_client):
        """Test that OpenSearch RequestError with status 400 returns error message to caller."""
        from handlers.search import search_api_handler

        # Create a RequestError with realistic OpenSearch error structure
        error_reason = (
            'Invalid search query: Text fields are not optimised for operations that require per-document field data '
            'like aggregations and sorting, so these operations are disabled by default. '
            'Please use a keyword field instead.'
        )
        mock_opensearch_client.search.side_effect = CCInvalidRequestException(error_reason)

        event = self._create_api_event(
            'cosm',
            body={
                'query': {'match_all': {}},
                'sort': [{'familyName': 'asc'}],  # Sorting on text field causes this error
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertEqual(error_reason, body['message'])


@mock_aws
class TestPublicSearchProviders(TstFunction):
    """Test suite for public_search_api_handler - public license search via OpenSearch."""

    def setUp(self):
        super().setUp()

    def _create_public_api_event(self, compact: str, body: dict = None) -> dict:
        """Create API Gateway event for public query providers (no auth)."""
        return {
            'resource': '/v1/public/compacts/{compact}/providers/query',
            'path': f'/v1/public/compacts/{compact}/providers/query',
            'httpMethod': 'POST',
            'headers': {'accept': 'application/json', 'content-type': 'application/json'},
            'multiValueHeaders': {},
            'queryStringParameters': None,
            'pathParameters': {'compact': compact},
            'requestContext': {
                'httpMethod': 'POST',
                'resourcePath': '/v1/public/compacts/{compact}/providers/query',
            },
            'body': json.dumps(body) if body else None,
            'isBase64Encoded': False,
        }

    def _create_mock_hit_with_inner_hits(
        self,
        provider_id: str = '00000000-0000-0000-0000-000000000001',
        compact: str = 'cosm',
        jurisdiction: str = 'oh',
        license_number: str = 'LN123',
        family_name: str = 'Doe',
        given_name: str = 'John',
        sort_values: list = None,
    ) -> dict:
        """Create a mock OpenSearch hit with inner_hits for nested licenses."""
        hit = {
            '_index': f'compact_{compact}_providers',
            '_id': provider_id,
            '_source': {
                'providerId': provider_id,
                'compact': compact,
                'givenName': given_name,
                'familyName': family_name,
            },
            'inner_hits': {
                'licenses': {
                    'hits': {
                        'hits': [
                            {
                                '_source': {
                                    'providerId': provider_id,
                                    'givenName': given_name,
                                    'familyName': family_name,
                                    'jurisdiction': jurisdiction,
                                    'compact': compact,
                                    'licenseNumber': license_number,
                                }
                            }
                        ]
                    }
                }
            },
        }
        if sort_values is not None:
            hit['sort'] = sort_values
        return hit

    @patch('handlers.search.opensearch_client')
    def test_license_number_search_builds_nested_query(self, mock_opensearch_client):
        """Test that licenseNumber in query builds nested term query on licenses.licenseNumber."""
        from handlers.search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'licenseNumber': 'LN999'}, 'pagination': {'pageSize': 10}},
        )
        public_search_api_handler(event, self.mock_context)
        call_body = mock_opensearch_client.search.call_args.kwargs['body']
        self.assertIn('query', call_body)
        must = call_body['query']['bool']['must']
        nested = next(m for m in must if 'nested' in m)
        self.assertEqual('licenses', nested['nested']['path'])
        inner_must = nested['nested']['query']['bool']['must']
        self.assertIn({'term': {'licenses.licenseNumber': 'LN999'}}, inner_must)

    @patch('handlers.search.opensearch_client')
    def test_jurisdiction_and_name_search_builds_nested_query(self, mock_opensearch_client):
        """Test that jurisdiction and familyName build correct nested query."""
        from handlers.search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        event = self._create_public_api_event(
            'cosm',
            body={
                'query': {'jurisdiction': 'oh', 'familyName': 'Smith'},
                'pagination': {'pageSize': 10},
            },
        )
        public_search_api_handler(event, self.mock_context)
        call_body = mock_opensearch_client.search.call_args.kwargs['body']
        must = call_body['query']['bool']['must']
        nested = next(m for m in must if 'nested' in m)
        inner_must = nested['nested']['query']['bool']['must']
        self.assertIn({'term': {'licenses.jurisdiction': 'oh'}}, inner_must)
        self.assertTrue(any('licenses.familyName' in str(m) for m in inner_must))

    @patch('handlers.search.opensearch_client')
    def test_name_only_search_builds_nested_query(self, mock_opensearch_client):
        """Test that familyName only builds nested match on licenses.familyName."""
        from handlers.search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Jones'}, 'pagination': {'pageSize': 10}},
        )
        public_search_api_handler(event, self.mock_context)
        call_body = mock_opensearch_client.search.call_args.kwargs['body']
        must = call_body['query']['bool']['must']
        nested = next(m for m in must if 'nested' in m)
        inner_must = nested['nested']['query']['bool']['must']
        self.assertTrue(any('familyName' in str(m) for m in inner_must))

    def test_given_name_without_family_name_returns_400(self):
        """Test that givenName without familyName returns 400."""
        from handlers.search import public_search_api_handler

        event = self._create_public_api_event(
            'cosm',
            body={'query': {'givenName': 'John'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('familyName is required if givenName is provided', body['message'])

    def test_no_search_criteria_returns_400(self):
        """Test that at least one of licenseNumber, jurisdiction, or familyName is required."""
        from handlers.search import public_search_api_handler

        event = self._create_public_api_event(
            'cosm',
            body={'query': {}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('At least one of licenseNumber, jurisdiction, or familyName', body['message'])

    @patch('handlers.search.opensearch_client')
    def test_pagination_page_size_maps_to_size_and_search_after_from_last_key(self, mock_opensearch_client):
        """Test that pageSize maps to size and lastKey decodes to search_after."""
        from base64 import b64encode

        from handlers.search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        last_key_str = b64encode(b'{"search_after": ["doe", "jane", "uuid-123"]}').decode('utf-8')
        event = self._create_public_api_event(
            'cosm',
            body={
                'query': {'familyName': 'Doe'},
                'pagination': {'pageSize': 25, 'lastKey': last_key_str},
            },
        )
        public_search_api_handler(event, self.mock_context)
        call_body = mock_opensearch_client.search.call_args.kwargs['body']
        self.assertEqual(25, call_body['size'])
        self.assertEqual(['doe', 'jane', 'uuid-123'], call_body['search_after'])

    @patch('handlers.search.opensearch_client')
    def test_response_includes_last_key_when_more_results_and_null_when_done(self, mock_opensearch_client):
        """Test that lastKey is set when full page returned, null when fewer results than pageSize."""
        from base64 import b64decode

        from handlers.search import public_search_api_handler

        mock_hit = self._create_mock_hit_with_inner_hits(sort_values=['doe', 'john', '00000000-0000-0000-0000-000000000001'])
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 1}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertIn('lastKey', body['pagination'])
        self.assertIsNotNone(body['pagination']['lastKey'])
        decoded = json.loads(b64decode(body['pagination']['lastKey']).decode('utf-8'))
        self.assertEqual(decoded['search_after'], ['doe', 'john', '00000000-0000-0000-0000-000000000001'])

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event['body'] = json.dumps({'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 100}})
        response2 = public_search_api_handler(event, self.mock_context)
        body2 = json.loads(response2['body'])
        self.assertIsNone(body2['pagination']['lastKey'])

    @patch('handlers.search.opensearch_client')
    def test_response_contains_only_allowed_license_fields(self, mock_opensearch_client):
        """Test that each item in providers has only providerId, givenName, familyName, licenseJurisdiction, compact, licenseNumber."""
        from handlers.search import public_search_api_handler

        mock_hit = self._create_mock_hit_with_inner_hits()
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'licenseNumber': 'LN123'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertEqual(len(body['providers']), 1)
        provider = body['providers'][0]
        allowed = {'providerId', 'givenName', 'familyName', 'licenseJurisdiction', 'compact', 'licenseNumber'}
        self.assertEqual(set(provider.keys()), allowed)
        self.assertEqual(provider['licenseJurisdiction'], 'oh')
        self.assertEqual(provider['licenseNumber'], 'LN123')

    @patch('handlers.search.opensearch_client')
    def test_compact_mismatch_filtered_out(self, mock_opensearch_client):
        """Test that hits with compact != path compact are not included in results."""
        from handlers.search import public_search_api_handler

        mock_hit = self._create_mock_hit_with_inner_hits(compact='other')
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertEqual(body['providers'], [])

    def test_invalid_request_body_returns_400(self):
        """Test that invalid or missing body returns 400."""
        from handlers.search import public_search_api_handler

        event = self._create_public_api_event('cosm', body=None)
        event['body'] = 'not valid json'
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Invalid request', body['message'])

    def test_unsupported_route_returns_400(self):
        """Test that wrong method/path returns 400."""
        from handlers.search import public_search_api_handler

        event = self._create_public_api_event('cosm', body={'query': {'familyName': 'x'}})
        event['resource'] = '/v1/public/compacts/{compact}/providers/other'
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        self.assertIn('Unsupported method or resource', json.loads(response['body'])['message'])
