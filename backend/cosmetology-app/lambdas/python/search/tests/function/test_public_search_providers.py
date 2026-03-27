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

    def _create_mock_hit(
        self,
        provider_id: str = '00000000-0000-0000-0000-000000000001',
        compact: str = 'cosm',
        jurisdiction: str = 'oh',
        license_number: str = 'LN123',
        family_name: str = 'Doe',
        given_name: str = 'John',
        sort_values: list = None,
        license_type: str = 'cosmetologist',
    ) -> dict:
        """Create a mock OpenSearch hit for one document per license."""
        doc_id = f'{provider_id}#{jurisdiction}#{license_type}'
        hit = {
            '_index': f'compact_{compact}_providers',
            '_id': doc_id,
            '_source': {
                'providerId': provider_id,
                'compact': compact,
                'givenName': given_name,
                'familyName': family_name,
                'licenses': [
                    {
                        'jurisdiction': jurisdiction,
                        'licenseNumber': license_number,
                        'licenseType': license_type,
                    }
                ],
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
        self.assertNotIn('inner_hits', nested['nested'])
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
        self.assertNotIn('inner_hits', nested['nested'])
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
        self.assertNotIn('inner_hits', nested['nested'])
        inner_must = nested['nested']['query']['bool']['must']
        self.assertTrue(any('familyName' in str(m) for m in inner_must))

    @patch('handlers.public_search.opensearch_client')
    def test_sort_includes_id_tiebreaker(self, mock_opensearch_client):
        """OpenSearch sort includes _id as the fourth tiebreaker for deterministic pagination."""
        from handlers.public_search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 10}},
        )
        public_search_api_handler(event, self.mock_context)
        call_body = mock_opensearch_client.search.call_args.kwargs['body']
        sort = call_body['sort']
        self.assertEqual(4, len(sort))
        self.assertEqual({'_id': 'asc'}, sort[3])

    @patch('handlers.public_search.opensearch_client')
    def test_default_sort_is_family_name_ascending(self, mock_opensearch_client):
        """Without sorting in request, default is familyName ascending; response echoes sorting."""
        from handlers.public_search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        call_body = mock_opensearch_client.search.call_args.kwargs['body']
        sort = call_body['sort']
        self.assertEqual(4, len(sort))
        self.assertEqual({'familyName.keyword': 'asc'}, sort[0])
        self.assertEqual({'givenName.keyword': 'asc'}, sort[1])
        self.assertEqual({'providerId': 'asc'}, sort[2])
        self.assertEqual({'_id': 'asc'}, sort[3])
        body = json.loads(response['body'])
        self.assertEqual(
            {'key': 'familyName', 'direction': 'ascending'},
            body['sorting'],
        )

    @patch('handlers.public_search.opensearch_client')
    def test_family_name_sort_descending(self, mock_opensearch_client):
        """sorting key familyName with descending direction maps to OpenSearch desc on name fields."""
        from handlers.public_search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        event = self._create_public_api_event(
            'cosm',
            body={
                'query': {'familyName': 'Doe'},
                'pagination': {'pageSize': 10},
                'sorting': {'key': 'familyName', 'direction': 'descending'},
            },
        )
        response = public_search_api_handler(event, self.mock_context)
        call_body = mock_opensearch_client.search.call_args.kwargs['body']
        sort = call_body['sort']
        self.assertEqual({'familyName.keyword': 'desc'}, sort[0])
        self.assertEqual({'givenName.keyword': 'desc'}, sort[1])
        self.assertEqual({'providerId': 'desc'}, sort[2])
        self.assertEqual({'_id': 'asc'}, sort[3])
        body = json.loads(response['body'])
        self.assertEqual(
            {'key': 'familyName', 'direction': 'descending'},
            body['sorting'],
        )

    @patch('handlers.public_search.opensearch_client')
    def test_date_of_update_sort_ascending(self, mock_opensearch_client):
        """sorting by dateOfUpdate uses top-level date field and _id tiebreaker."""
        from handlers.public_search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        event = self._create_public_api_event(
            'cosm',
            body={
                'query': {'licenseNumber': 'LN999'},
                'pagination': {'pageSize': 10},
                'sorting': {'key': 'dateOfUpdate', 'direction': 'ascending'},
            },
        )
        response = public_search_api_handler(event, self.mock_context)
        call_body = mock_opensearch_client.search.call_args.kwargs['body']
        self.assertEqual(
            [{'dateOfUpdate': 'asc'}, {'_id': 'asc'}],
            call_body['sort'],
        )
        body = json.loads(response['body'])
        self.assertEqual(
            {'key': 'dateOfUpdate', 'direction': 'ascending'},
            body['sorting'],
        )

    @patch('handlers.public_search.opensearch_client')
    def test_date_of_update_sort_descending(self, mock_opensearch_client):
        """dateOfUpdate descending keeps _id tiebreaker ascending."""
        from handlers.public_search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        event = self._create_public_api_event(
            'cosm',
            body={
                'query': {'licenseNumber': 'LN999'},
                'pagination': {'pageSize': 10},
                'sorting': {'key': 'dateOfUpdate', 'direction': 'descending'},
            },
        )
        public_search_api_handler(event, self.mock_context)
        call_body = mock_opensearch_client.search.call_args.kwargs['body']
        self.assertEqual(
            [{'dateOfUpdate': 'desc'}, {'_id': 'asc'}],
            call_body['sort'],
        )

    @patch('handlers.public_search.opensearch_client')
    def test_response_always_contains_sorting_field(self, mock_opensearch_client):
        """Successful public search responses include sorting with key and direction."""
        from handlers.public_search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'jurisdiction': 'oh'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('sorting', body)
        self.assertEqual({'key', 'direction'}, set(body['sorting'].keys()))

    @patch('handlers.public_search.opensearch_client')
    def test_invalid_sort_key_returns_400(self, mock_opensearch_client):
        """Unknown sorting.key returns 400."""
        from handlers.public_search import public_search_api_handler

        event = self._create_public_api_event(
            'cosm',
            body={
                'query': {'familyName': 'Doe'},
                'pagination': {'pageSize': 10},
                'sorting': {'key': 'invalidKey', 'direction': 'ascending'},
            },
        )
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Invalid sort key', body['message'])
        mock_opensearch_client.search.assert_not_called()

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
        last_key_payload = json.dumps({'search_after': ['doe', 'jane', 'uuid-123', 'uuid-123#oh#cosmetologist']})
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
        self.assertEqual(
            ['doe', 'jane', 'uuid-123', 'uuid-123#oh#cosmetologist'],
            call_body['search_after'],
        )

    @patch('handlers.public_search.opensearch_client')
    def test_response_last_key_encodes_last_hit_sort_when_full_page(self, mock_opensearch_client):
        """When OpenSearch returns a full page of hits, lastKey encodes search_after from the last hit."""
        from base64 import b64decode

        from handlers.public_search import public_search_api_handler

        mock_hits_full_page = []
        for i in range(5):
            sort_i = [
                'doe',
                'john',
                f'00000000-0000-0000-0000-00000000000{i}',
                f'00000000-0000-0000-0000-00000000000{i}#oh#cosmetologist',
            ]
            mock_hits_full_page.append(
                self._create_mock_hit(
                    provider_id=f'00000000-0000-0000-0000-00000000000{i}',
                    sort_values=sort_i,
                )
            )
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 10, 'relation': 'eq'}, 'hits': mock_hits_full_page},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 5}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertIn('lastKey', body['pagination'])
        self.assertIsNotNone(body['pagination']['lastKey'])
        decoded = json.loads(b64decode(body['pagination']['lastKey']).decode('utf-8'))
        self.assertEqual(decoded['search_after'], mock_hits_full_page[-1]['sort'])

    @patch('handlers.public_search.opensearch_client')
    def test_response_last_key_null_when_fewer_hits_than_page_size(self, mock_opensearch_client):
        """When hit count is below pageSize, there are no more pages and lastKey is null."""
        from handlers.public_search import public_search_api_handler

        sort_four = [
            'doe',
            'john',
            '00000000-0000-0000-0000-000000000001',
            '00000000-0000-0000-0000-000000000001#oh#cosmetologist',
        ]
        single_hit = self._create_mock_hit(sort_values=sort_four)
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [single_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 100}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertIsNone(body['pagination']['lastKey'])

    @patch('handlers.public_search.opensearch_client')
    def test_response_contains_only_allowed_license_fields(self, mock_opensearch_client):
        """Test that each item in providers has only expected fields."""
        from handlers.public_search import public_search_api_handler

        mock_hit = self._create_mock_hit()
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

        mock_hit = self._create_mock_hit(compact='other')
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

    @patch('handlers.public_search.opensearch_client')
    def test_terminal_page_returns_last_key_null(self, mock_opensearch_client):
        """When fewer hits than pageSize, lastKey must be null."""
        from handlers.public_search import public_search_api_handler

        mock_hits = [
            self._create_mock_hit(
                provider_id='pid-1',
                jurisdiction='oh',
                license_number='L1',
                sort_values=['doe', 'john', 'pid-1', 'pid-1#oh#cosmetologist'],
            ),
            self._create_mock_hit(
                provider_id='pid-1',
                jurisdiction='al',
                license_number='L2',
                sort_values=['doe', 'john', 'pid-1', 'pid-1#al#cosmetologist'],
            ),
            self._create_mock_hit(
                provider_id='pid-2',
                jurisdiction='oh',
                license_number='L3',
                sort_values=['doe', 'john', 'pid-2', 'pid-2#oh#cosmetologist'],
            ),
        ]
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 3, 'relation': 'eq'}, 'hits': mock_hits},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertIsNone(body['pagination']['lastKey'], 'no more results -> lastKey null')

    @patch('handlers.public_search.opensearch_client')
    def test_invalid_last_key_format_returns_400(self, mock_opensearch_client):
        """Malformed or invalid lastKey must return 400."""
        from base64 import b64encode

        from handlers.public_search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }
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
        mock_opensearch_client.search.assert_not_called()
