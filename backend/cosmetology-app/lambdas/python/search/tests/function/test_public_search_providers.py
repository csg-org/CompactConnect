import json
from unittest.mock import patch

from moto import mock_aws

from . import TstFunction

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
        inner_license_count: int = 1,
    ) -> dict:
        """Create a mock OpenSearch hit with inner_hits for nested licenses.
        inner_license_count: number of license inner hits (deterministic order: jurisdiction, licenseType, licenseNumber).
        """
        inner_sources = []
        for i in range(inner_license_count):
            inner_sources.append({
                '_source': {
                    'providerId': provider_id,
                    'givenName': given_name,
                    'familyName': family_name,
                    'jurisdiction': jurisdiction,
                    'compact': compact,
                    'licenseNumber': f'{license_number}-{i}' if inner_license_count > 1 else license_number,
                    'licenseType': f'type{i}',
                }
            })
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
                        'hits': inner_sources,
                    }
                }
            },
        }
        if sort_values is not None:
            hit['sort'] = sort_values
        return hit

    @patch('handlers.public_search.opensearch_client')
    def test_license_number_search_builds_nested_query(self, mock_opensearch_client):
        """Test that licenseNumber in query builds nested term query on licenses.licenseNumber."""
        from handlers.public_search import public_search_api_handler

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

    @patch('handlers.public_search.opensearch_client')
    def test_jurisdiction_and_name_search_builds_nested_query(self, mock_opensearch_client):
        """Test that jurisdiction and familyName build correct nested query."""
        from handlers.public_search import public_search_api_handler

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

    @patch('handlers.public_search.opensearch_client')
    def test_name_only_search_builds_nested_query(self, mock_opensearch_client):
        """Test that familyName only builds nested match on licenses.familyName."""
        from handlers.public_search import public_search_api_handler

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
        from handlers.public_search import public_search_api_handler

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
        from handlers.public_search import public_search_api_handler

        event = self._create_public_api_event(
            'cosm',
            body={'query': {}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('At least one of licenseNumber, jurisdiction, or familyName', body['message'])

    @patch('handlers.public_search.opensearch_client')
    def test_pagination_page_size_maps_to_size_and_search_after_from_last_key(self, mock_opensearch_client):
        """Test that pageSize maps to size and lastKey decodes to search_after."""
        from base64 import b64encode

        from handlers.public_search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        last_key_payload = json.dumps({'search_after': ['doe', 'jane', 'uuid-123']})
        last_key_str = b64encode(last_key_payload.encode('utf-8')).decode('utf-8')
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

    @patch('handlers.public_search.opensearch_client')
    def test_response_includes_last_key_when_more_results_and_null_when_done(self, mock_opensearch_client):
        """Test that lastKey is set when full page returned, null when fewer results than pageSize."""
        from base64 import b64decode

        from handlers.public_search import public_search_api_handler

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

    @patch('handlers.public_search.opensearch_client')
    def test_response_contains_only_allowed_license_fields(self, mock_opensearch_client):
        """Test that each item in providers has only providerId, givenName, familyName, licenseJurisdiction, compact, licenseNumber."""
        from handlers.public_search import public_search_api_handler

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

    @patch('handlers.public_search.opensearch_client')
    def test_compact_mismatch_filtered_out(self, mock_opensearch_client):
        """Test that hits with compact != path compact are not included in results."""
        from handlers.public_search import public_search_api_handler

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
        from handlers.public_search import public_search_api_handler

        event = self._create_public_api_event('cosm', body=None)
        event['body'] = 'not valid json'
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Invalid request', body['message'])

    def test_unsupported_route_returns_400(self):
        """Test that wrong method/path returns 400."""
        from handlers.public_search import public_search_api_handler

        event = self._create_public_api_event('cosm', body={'query': {'familyName': 'x'}})
        event['resource'] = '/v1/public/compacts/{compact}/providers/other'
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        self.assertIn('Unsupported method or resource', json.loads(response['body'])['message'])

    # --- Custom cursor (license-level page size) tests ---

    @patch('handlers.public_search.opensearch_client')
    def test_providers_array_length_never_exceeds_page_size_large_license_matches(self, mock_opensearch_client):
        """License-level paging: returned providers (license records) must be <= pageSize."""
        from handlers.public_search import public_search_api_handler

        # One provider with 20 matching licenses; pageSize 10 -> must return exactly 10
        mock_hit = self._create_mock_hit_with_inner_hits(
            provider_id='pid-1',
            sort_values=['doe', 'john', 'pid-1'],
            inner_license_count=20,
        )
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertLessEqual(
            len(body['providers']),
            10,
            'providers array must not exceed pageSize',
        )
        self.assertEqual(len(body['providers']), 10, 'first page should return exactly pageSize when available')

    @patch('handlers.public_search.opensearch_client')
    def test_providers_array_length_never_exceeds_page_size_when_many_providers_match(self, mock_opensearch_client):
        """License-level paging: returned providers (license records) must be <= pageSize."""
        from handlers.public_search import public_search_api_handler

        # One provider with 20 matching licenses; pageSize 10 -> must return exactly 10
        mock_hits = []

        for i in range(30):
            mock_hits.append(self._create_mock_hit_with_inner_hits(
                provider_id=f'pid-{i}',
                sort_values=['doe', 'john', f'pid-{i}'],
                inner_license_count=1,
            ))
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 30, 'relation': 'eq'}, 'hits': mock_hits},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 25}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertEqual(len(body['providers']), 25, 'first page should return exactly pageSize when available')

    @patch('handlers.public_search.opensearch_client')
    def test_last_key_uses_cursor_format_with_resume_fields_when_mid_provider(self, mock_opensearch_client):
        """lastKey when mid-provider includes resume_provider_sort, resume_provider_id, license_offset; search_after optional."""
        from base64 import b64decode

        from handlers.public_search import public_search_api_handler

        mock_hit = self._create_mock_hit_with_inner_hits(
            provider_id='pid-1',
            sort_values=['doe', 'john', 'pid-1'],
            inner_license_count=15,
        )
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertIsNotNone(body['pagination']['lastKey'], 'should have next page when more licenses exist')
        decoded = json.loads(b64decode(body['pagination']['lastKey']).decode('utf-8'))
        self.assertEqual(decoded.get('resume_provider_id'), 'pid-1')
        self.assertEqual(decoded.get('resume_provider_sort'), ['doe', 'john', 'pid-1'])
        self.assertEqual(decoded.get('license_offset'), 10, 'first page consumed 10 licenses from this provider')
        if decoded.get('search_after') is not None:
            self.assertEqual(decoded['search_after'], ['doe', 'john', 'pid-1'])

    @patch('handlers.public_search.opensearch_client')
    def test_terminal_page_returns_last_key_null(self, mock_opensearch_client):
        """When no more license records exist, lastKey must be null."""
        from handlers.public_search import public_search_api_handler

        mock_hit = self._create_mock_hit_with_inner_hits(
            provider_id='pid-1',
            sort_values=['doe', 'john', 'pid-1'],
            inner_license_count=3,
        )
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertIsNone(body['pagination']['lastKey'], 'no more results -> lastKey null')

    @patch('handlers.public_search.opensearch_client')
    def test_resume_from_cursor_skips_license_offset_and_returns_next_page(self, mock_opensearch_client):
        """Using lastKey with license_offset resumes from that provider at offset; next page has no duplicates."""
        from handlers.public_search import public_search_api_handler

        mock_hit = self._create_mock_hit_with_inner_hits(
            provider_id='pid-1',
            sort_values=['doe', 'john', 'pid-1'],
            inner_license_count=15,
        )
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 10}},
        )
        response1 = public_search_api_handler(event, self.mock_context)
        body1 = json.loads(response1['body'])
        self.assertEqual(len(body1['providers']), 10)
        last_key = body1['pagination']['lastKey']
        self.assertIsNotNone(last_key)

        # Second request with lastKey: same single provider hit returned by OpenSearch; we resume at offset 10
        event2 = self._create_public_api_event(
            'cosm',
            body={
                'query': {'familyName': 'Doe'},
                'pagination': {'pageSize': 10, 'lastKey': last_key},
            },
        )
        response2 = public_search_api_handler(event2, self.mock_context)
        body2 = json.loads(response2['body'])
        self.assertEqual(len(body2['providers']), 5, 'remaining 5 licenses from same provider')
        first_license_page2 = body2['providers'][0].get('licenseNumber')
        last_license_page1 = body1['providers'][-1].get('licenseNumber')
        self.assertNotEqual(first_license_page2, last_license_page1, 'no duplicate at boundary')

    @patch('handlers.public_search.opensearch_client')
    def test_resume_from_cursor_skips_license_offset_and_returns_next_page_multi_provider(self, mock_opensearch_client):
        """Using lastKey with license_offset resumes from that provider at offset; next page has no duplicates."""
        from handlers.public_search import public_search_api_handler

        mock_hits = []
        # this sets up five providers that match, each with two licenses (10 total)
        for i in range(5):
            mock_hits.append(self._create_mock_hit_with_inner_hits(
                provider_id=f'pid-{i}',
                license_number=f'LIC-{i}',
                sort_values=['doe', 'john', f'pid-{i}'],
                inner_license_count=2,
            ))
        # This mock simulates the first request returning all matching providers, then the second request returning the
        # remaining 3 after the search_after cursor is applied.
        mock_opensearch_client.search.side_effect = [
            {
                'hits': {'total': {'value': 5, 'relation': 'eq'}, 'hits': mock_hits},
            },
            {
                'hits': {'total': {'value': 3, 'relation': 'eq'}, 'hits': mock_hits[2:]},
            }
        ]
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 5}},
        )
        response1 = public_search_api_handler(event, self.mock_context)
        body1 = json.loads(response1['body'])
        self.assertEqual(len(body1['providers']), 5)
        last_key = body1['pagination']['lastKey']
        self.assertIsNotNone(last_key)

        # Second request with lastKey: same single provider hit returned by OpenSearch; we resume at offset 25
        event2 = self._create_public_api_event(
            'cosm',
            body={
                'query': {'familyName': 'Doe'},
                'pagination': {'pageSize': 5, 'lastKey': last_key},
            },
        )
        response2 = public_search_api_handler(event2, self.mock_context)
        body2 = json.loads(response2['body'])
        self.assertEqual(len(body2['providers']), 5, 'remaining 5 licenses')
        first_license_page2 = body2['providers'][0].get('licenseNumber')
        last_license_page1 = body1['providers'][-1].get('licenseNumber')
        self.assertNotEqual(first_license_page2, last_license_page1, 'duplicate license numbers detected when paging')

    @patch('handlers.public_search.opensearch_client')
    def test_invalid_last_key_format_returns_400(self, mock_opensearch_client):
        """Malformed or invalid lastKey must return 400."""
        from base64 import b64encode

        from handlers.public_search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        # Cursor must have search_after or resume fields; empty object is invalid
        bad_payload = json.dumps({})
        last_key = b64encode(bad_payload.encode('utf-8')).decode('utf-8')
        event = self._create_public_api_event(
            'cosm',
            body={
                'query': {'familyName': 'Doe'},
                'pagination': {'pageSize': 10, 'lastKey': last_key},
            },
        )
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertIn('lastkey', body['message'].lower())
