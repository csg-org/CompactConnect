import json
from unittest.mock import patch

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
        compact: str = 'aslp',
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
        event = self._create_api_event(compact='aslp', body={'query': {'match_all': {}}})

        response = search_api_handler(event, self.mock_context)

        # Verify search was called
        mock_opensearch_client.search.assert_called_once()

        # Verify the search was called with correct parameters
        mock_opensearch_client.search.assert_called_once_with(
            index_name='compact_aslp_providers', body={'query': {'match_all': {}}, 'size': 100}
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
        event = self._create_api_event('aslp', body={'query': custom_query, 'from': 20})

        search_api_handler(event, self.mock_context)

        # Verify the custom query was passed through
        mock_opensearch_client.search.assert_called_once_with(
            index_name='compact_aslp_providers',
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
        event = self._create_api_event('aslp', body={'query': {'match_all': {}}, 'size': 500})

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

        sort_config = [{'providerId': {'order': 'asc'}}, {'dateOfUpdate': {'order': 'desc'}}]
        search_after_values = ['provider-uuid-123']
        event = self._create_api_event(
            'aslp',
            body={
                'query': {'match_all': {}},
                'sort': sort_config,
                'search_after': search_after_values,
            },
        )

        search_api_handler(event, self.mock_context)

        mock_opensearch_client.search.assert_called_once_with(
            index_name='compact_aslp_providers',
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
            'aslp',
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
        event = self._create_api_event('aslp', body={'size': 10})

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

        event = self._create_api_event('aslp', body={'query': {'match_all': {}}})

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])
        self.assertEqual(
            {
                'providers': [
                    {
                        'birthMonthDay': '06-15',
                        'compact': 'aslp',
                        'compactEligibility': 'eligible',
                        'dateOfExpiration': '2025-12-31',
                        'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                        'familyName': 'Doe',
                        'givenName': 'John',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'licenseJurisdiction': 'oh',
                        'militaryStatus': 'notApplicable',
                        'licenseStatus': 'active',
                        'privilegeJurisdictions': [],
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
            'aslp',
            body={
                'query': {'match_all': {}},
                'sort': [{'providerId': {'order': 'asc'}}, {'dateOfUpdate': {'order': 'asc'}}],
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
        for compact in ['aslp', 'octp', 'coun']:
            mock_opensearch_client.reset_mock()

            event = self._create_api_event(compact, body={'query': {'match_all': {}}})
            search_api_handler(event, self.mock_context)

            call_args = mock_opensearch_client.search.call_args
            self.assertEqual(f'compact_{compact}_providers', call_args.kwargs['index_name'])

    def test_missing_scopes_returns_403(self):
        """Test that missing auth scope returns a 403 error."""
        from handlers.search import search_api_handler

        # Create event with unsupported route
        event = self._create_api_event(compact='aslp', scopes_override='openid email')

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(403, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Access denied', body['message'])

    def test_query_with_index_key_returns_400(self):
        """Test that queries containing 'index' key are rejected with 400 error."""
        from handlers.search import search_api_handler

        # Test with 'index' key (terms lookup attack pattern)
        event = self._create_api_event(
            'aslp',
            body={
                'query': {
                    'terms': {
                        'providerId': {
                            'index': 'compact_octp_providers',
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
        """
        Test that queries containing an '_index' key are rejected with a 400 error.

        The original vector for '_index' was more_like_this, which the query clause allowlist now
        rejects outright (covered by test_search_with_disallowed_free_form_clauses_returns_400).
        This exercises the cross-index check itself, by placing '_index' inside an allowlisted
        clause so it has to be caught on its own merits rather than by the allowlist.
        """
        from handlers.search import search_api_handler

        event = self._create_api_event(
            'aslp',
            body={
                'query': {
                    'terms': {
                        'providerId': {
                            '_index': 'compact_octp_providers',
                            '_id': 'target-provider-uuid',
                        }
                    }
                }
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Cross-index queries are not allowed', body['message'])
        self.assertIn("'_index'", body['message'])

    @patch('handlers.search.opensearch_client')
    def test_search_with_query_string_clause_returns_400(self, mock_opensearch_client):
        """
        A free-form query_string clause must be rejected outright.

        query_string smuggles the field reference inside a string value rather than exposing it as
        a structural key, which defeats any field-name-based permission gate and lets a caller use
        hit-vs-no-hit as an oracle against fields they should not be able to query.
        """
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        event = self._create_api_event(
            'aslp',
            body={
                'query': {
                    'bool': {
                        'must': [
                            {'term': {'providerId': ''}},
                            {'query_string': {'query': 'licenses.ssnLastFour:1234'}},
                        ]
                    }
                }
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('query_string', body['message'])
        mock_opensearch_client.search.assert_not_called()

    @patch('handlers.search.opensearch_client')
    def test_search_with_disallowed_free_form_clauses_returns_400(self, mock_opensearch_client):
        """Every free-form/scripted clause type outside the allowlist must be rejected with a 400."""
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        disallowed_queries = {
            'simple_query_string': {'simple_query_string': {'query': 'licenses.ssnLastFour:1234'}},
            'wildcard': {'wildcard': {'familyName': {'value': 'Do*'}}},
            'regexp': {'regexp': {'familyName': 'Do.*'}},
            'script': {'script': {'script': {'source': "doc['familyName'].size() > 0"}}},
            'exists': {'exists': {'field': 'licenses.ssnLastFour'}},
            'multi_match': {'multi_match': {'query': 'Doe', 'fields': ['givenName', 'licenses.ssnLastFour']}},
            'more_like_this': {'more_like_this': {'like': [{'_index': 'compact_octp_providers'}]}},
        }

        for clause_name, query in disallowed_queries.items():
            with self.subTest(clause=clause_name):
                event = self._create_api_event('aslp', body={'query': query})

                response = search_api_handler(event, self.mock_context)

                self.assertEqual(400, response['statusCode'])
                body = json.loads(response['body'])
                self.assertIn(clause_name, body['message'])

        mock_opensearch_client.search.assert_not_called()

    @patch('handlers.search.opensearch_client')
    def test_search_with_disallowed_clause_nested_deep_in_query_returns_400(self, mock_opensearch_client):
        """A disallowed clause buried inside nested/bool structures must still be rejected."""
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        event = self._create_api_event(
            'aslp',
            body={
                'query': {
                    'bool': {
                        'must': [
                            {'match': {'givenName': 'John'}},
                            {
                                'nested': {
                                    'path': 'privileges',
                                    'query': {
                                        'bool': {
                                            'should': [
                                                {'term': {'privileges.jurisdiction': 'oh'}},
                                                {'query_string': {'query': 'privileges.privilegeId:*'}},
                                            ]
                                        }
                                    },
                                }
                            },
                        ]
                    }
                }
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('query_string', body['message'])
        mock_opensearch_client.search.assert_not_called()

    @patch('handlers.search.opensearch_client')
    def test_search_accepts_the_full_query_shape_built_by_the_frontend(self, mock_opensearch_client):
        """
        Regression guard: the complete clause vocabulary the frontend builds must remain accepted.

        Mirrors prepRequestSearchParams in webroot/src/network/searchApi/data.api.ts, combining every
        clause type it can emit into a single request.
        """
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        event = self._create_api_event(
            'aslp',
            body={
                'query': {
                    'bool': {
                        'must': [
                            {'match_phrase_prefix': {'givenName': 'Jo'}},
                            {'match_phrase_prefix': {'familyName': 'Do'}},
                            {'term': {'licenseJurisdiction': 'oh'}},
                            {'term': {'militaryStatus': 'active'}},
                            {'match': {'npi': '1234567890'}},
                            {'match': {'licenseNumber': 'A-123'}},
                            {
                                'nested': {
                                    'path': 'privileges',
                                    'inner_hits': {'size': 100},
                                    'query': {
                                        'bool': {
                                            'must': [{'term': {'privileges.jurisdiction': 'ky'}}],
                                            'should': [
                                                {'range': {'privileges.dateOfIssuance': {'gte': '2024-01-01'}}},
                                                {'range': {'privileges.dateOfRenewal': {'lte': '2024-12-31'}}},
                                            ],
                                            'minimum_should_match': 1,
                                        }
                                    },
                                }
                            },
                            {
                                'bool': {
                                    'must_not': [
                                        {
                                            'nested': {
                                                'path': 'licenses',
                                                'query': {
                                                    'nested': {
                                                        'path': 'licenses.investigations',
                                                        'query': {
                                                            'term': {'licenses.investigations.type': 'investigation'}
                                                        },
                                                    }
                                                },
                                            }
                                        }
                                    ]
                                }
                            },
                        ]
                    }
                },
                'size': 25,
                'from': 25,
                'sort': [{'familyName.keyword': {'order': 'asc'}}],
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        mock_opensearch_client.search.assert_called_once()

    def test_query_with_nested_index_key_returns_400(self):
        """Test that queries with nested 'index' key at any level are rejected."""
        from handlers.search import search_api_handler

        # Test with 'index' key nested deep in the query structure
        event = self._create_api_event(
            'aslp',
            body={
                'query': {
                    'bool': {
                        'should': [
                            {
                                'terms': {
                                    'familyName.keyword': {
                                        'index': 'compact_octp_providers',
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
        from cc_common.exceptions import CCInvalidRequestException
        from handlers.search import search_api_handler

        # Create a RequestError with realistic OpenSearch error structure
        error_reason = (
            'Invalid search query: Text fields are not optimised for operations that require per-document field data '
            'like aggregations and sorting, so these operations are disabled by default. '
            'Please use a keyword field instead.'
        )
        mock_opensearch_client.search.side_effect = CCInvalidRequestException(error_reason)

        event = self._create_api_event(
            'aslp',
            body={
                'query': {'match_all': {}},
                'sort': [{'familyName.keyword': {'order': 'asc'}}],
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertEqual(error_reason, body['message'])

    @patch('handlers.search.opensearch_client')
    def test_provider_with_mismatched_compact_is_filtered_from_response(self, mock_opensearch_client):
        """Test that a provider with a compact field that doesn't match the path parameter is filtered from results."""
        from handlers.search import search_api_handler

        # Create a provider hit with a different compact than the path parameter
        provider_id = '00000000-0000-0000-0000-000000000001'
        hit = {
            '_index': 'compact_aslp_providers',
            '_id': provider_id,
            '_score': 1.0,
            '_source': {
                'providerId': provider_id,
                'type': 'provider',
                'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                'compact': 'octp',  # Different from path parameter 'aslp'
                'licenseJurisdiction': 'oh',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
                'givenName': 'John',
                'familyName': 'Doe',
                'dateOfExpiration': '2025-12-31',
                'jurisdictionUploadedLicenseStatus': 'active',
                'jurisdictionUploadedCompactEligibility': 'eligible',
                'birthMonthDay': '06-15',
            },
        }
        search_response = {
            'hits': {
                'total': {'value': 1, 'relation': 'eq'},
                'hits': [hit],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        # Currently, with our safeguards in place, it is not possible for a bad actor to reach across
        # indices when searching. This may change in the future with new OpenSearch features that are added
        # over time. Because we don't have a valid query to trigger this branch of logic, we're just using a
        # generic query here in place of some future query that can get past our safeguards and search provider
        # data across compact indices. The mock above is returning a provider from a different compact to
        # trigger the branch of logic where we catch this discrepancy, log the error so an alert fires, and
        # filter the document from the response
        custom_query = {'match_all': {}}

        # Request for 'aslp' compact but provider has 'octp' compact
        event = self._create_api_event('aslp', body={'query': custom_query})

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])
        # should be empty list with total value of 0
        self.assertEqual({'providers': [], 'total': {'relation': 'eq', 'value': 0}}, body)

    @patch('handlers.search.opensearch_client')
    def test_search_with_script_sort_returns_400(self, mock_opensearch_client):
        """
        A scripted sort must be rejected outright.

        A _script sort computes an arbitrary value per document, and the handler echoes sort values
        straight back to the caller as `lastSort` -- outside the response schema that otherwise
        strips restricted fields. That makes a scripted sort a direct read primitive for any indexed
        field, not merely an oracle, so it must never reach OpenSearch.
        """
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        event = self._create_api_event(
            'aslp',
            body={
                'query': {'match_all': {}},
                'sort': [
                    {
                        '_script': {
                            'type': 'string',
                            'script': {'source': "doc['licenses.emailAddress'].value"},
                            'order': 'asc',
                        }
                    }
                ],
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('_script', body['message'])
        mock_opensearch_client.search.assert_not_called()

    @patch('handlers.search.opensearch_client')
    def test_search_with_nested_filter_in_sort_returns_400(self, mock_opensearch_client):
        """
        A sort entry's `nested.filter` is a full query-DSL position, so it must not be accepted.

        Without this, a free-form clause could be smuggled through sort even though the query itself
        is allowlisted, re-opening the restricted-field oracle through a different door.
        """
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        event = self._create_api_event(
            'aslp',
            body={
                'query': {'match_all': {}},
                'sort': [
                    {
                        'dateOfExpiration': {
                            'order': 'asc',
                            'nested': {
                                'path': 'licenses',
                                'filter': {
                                    'query_string': {'query': 'licenses.emailAddress:[1985-01-01 TO 1985-06-30]'}
                                },
                            },
                        }
                    }
                ],
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('nested', body['message'])
        mock_opensearch_client.search.assert_not_called()

    @patch('handlers.search.opensearch_client')
    def test_search_with_disallowed_sort_options_returns_400(self, mock_opensearch_client):
        """Only the `order` sort option the frontend emits is accepted; every other option is rejected."""
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        disallowed_sorts = {
            'nested': [{'dateOfExpiration': {'order': 'asc', 'nested': {'path': 'licenses'}}}],
            'missing': [{'familyName.keyword': {'order': 'asc', 'missing': '_last'}}],
            'unmapped_type': [{'familyName.keyword': {'order': 'asc', 'unmapped_type': 'keyword'}}],
            'mode': [{'dateOfExpiration': {'order': 'asc', 'mode': 'max'}}],
            'format': [{'dateOfExpiration': {'order': 'asc', 'format': 'strict_date_optional_time'}}],
        }

        for option_name, sort in disallowed_sorts.items():
            with self.subTest(option=option_name):
                event = self._create_api_event('aslp', body={'query': {'match_all': {}}, 'sort': sort})

                response = search_api_handler(event, self.mock_context)

                self.assertEqual(400, response['statusCode'])
                body = json.loads(response['body'])
                self.assertIn(option_name, body['message'])

        mock_opensearch_client.search.assert_not_called()

    @patch('handlers.search.opensearch_client')
    def test_search_with_invalid_sort_order_value_returns_400(self, mock_opensearch_client):
        """The sort order must be one of the two values the frontend's SortDirection enum can emit."""
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        event = self._create_api_event(
            'aslp',
            body={'query': {'match_all': {}}, 'sort': [{'familyName.keyword': {'order': 'sideways'}}]},
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('sideways', body['message'])
        mock_opensearch_client.search.assert_not_called()

    @patch('handlers.search.opensearch_client')
    def test_search_accepts_the_sort_shape_built_by_the_frontend(self, mock_opensearch_client):
        """
        Regression guard: the sort shape the frontend builds must remain accepted.

        Mirrors prepRequestSearchParams in webroot/src/network/searchApi/data.api.ts, which emits
        [{'<sortBy>.keyword': {'order': 'asc' | 'desc'}}].
        """
        from handlers.search import search_api_handler

        for order in ('asc', 'desc'):
            with self.subTest(order=order):
                mock_opensearch_client.reset_mock()
                self._when_testing_mock_opensearch_client(mock_opensearch_client)

                event = self._create_api_event(
                    'aslp',
                    body={'query': {'match_all': {}}, 'sort': [{'familyName.keyword': {'order': order}}]},
                )

                response = search_api_handler(event, self.mock_context)

                self.assertEqual(200, response['statusCode'])
                mock_opensearch_client.search.assert_called_once()

    @patch('handlers.search.opensearch_client')
    def test_search_accepts_multi_field_sort_for_search_after_pagination(self, mock_opensearch_client):
        """Multiple sort entries must remain accepted, since search_after pagination needs a tiebreaker."""
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        event = self._create_api_event(
            'aslp',
            body={
                'query': {'match_all': {}},
                'sort': [{'familyName.keyword': {'order': 'asc'}}, {'providerId': {'order': 'asc'}}],
                'search_after': ['Doe', '00000000-0000-0000-0000-000000000001'],
            },
        )

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        mock_opensearch_client.search.assert_called_once()

    @patch('handlers.search.opensearch_client')
    def test_search_with_non_allowlisted_sort_field_returns_400(self, mock_opensearch_client):
        """
        Sorting is restricted to an allowlist of non-sensitive fields.

        Sort values are echoed back to the caller as `lastSort`, outside the response schema that
        strips restricted fields. Restricting which fields can be sorted on is what keeps that echo
        from becoming a read primitive for sensitive data.
        """
        from handlers.search import search_api_handler

        self._when_testing_mock_opensearch_client(mock_opensearch_client)

        sensitive_sort_fields = [
            'licenses.emailAddress',
            'licenses.phoneNumber',
            'licenses.homeAddressStreet1',
            'licenses.homeAddressPostalCode',
            'ssnLastFour',
        ]

        for field_name in sensitive_sort_fields:
            with self.subTest(field=field_name):
                event = self._create_api_event(
                    'aslp',
                    body={'query': {'match_all': {}}, 'sort': [{field_name: {'order': 'asc'}}]},
                )

                response = search_api_handler(event, self.mock_context)

                self.assertEqual(400, response['statusCode'])
                body = json.loads(response['body'])
                self.assertIn(field_name, body['message'])

        mock_opensearch_client.search.assert_not_called()

    @patch('handlers.search.opensearch_client')
    def test_search_accepts_every_allowlisted_sort_field(self, mock_opensearch_client):
        """Regression guard: each allowlisted sort field must remain usable."""
        from handlers.search import search_api_handler

        allowed_sort_fields = [
            'familyName.keyword',
            'givenName.keyword',
            'providerId',
            'dateOfUpdate',
            'dateOfExpiration',
        ]

        for field_name in allowed_sort_fields:
            with self.subTest(field=field_name):
                mock_opensearch_client.reset_mock()
                self._when_testing_mock_opensearch_client(mock_opensearch_client)

                event = self._create_api_event(
                    'aslp',
                    body={'query': {'match_all': {}}, 'sort': [{field_name: {'order': 'asc'}}]},
                )

                response = search_api_handler(event, self.mock_context)

                self.assertEqual(200, response['statusCode'])
                mock_opensearch_client.search.assert_called_once()
