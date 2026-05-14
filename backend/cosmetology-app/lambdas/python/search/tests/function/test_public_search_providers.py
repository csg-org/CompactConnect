import json
from datetime import date
from unittest.mock import patch

from common_test.test_constants import (
    DEFAULT_LICENSE_ISSUANCE_DATE,
    DEFAULT_LICENSE_UPDATE_DATETIME,
    DEFAULT_PROVIDER_UPDATE_DATETIME,
)
from moto import mock_aws

from . import TstFunction

# Public search always scopes nested license clauses to the per-type "home" indexed row.
_MOST_RECENT_LICENSE_FOR_TYPE_TERM = {'term': {'licenses.mostRecentLicenseForType': True}}

_DEFAULT_PUBLIC_SEARCH_SORT_FAMILY_NAME_ASC = [
    {'licenses.familyName.keyword': {'order': 'asc', 'nested': {'path': 'licenses'}}},
    {'licenses.givenName.keyword': {'order': 'asc', 'nested': {'path': 'licenses'}}},
    {'providerId': 'asc'},
    {'_id': 'asc'},
]

_DEFAULT_PUBLIC_SEARCH_SORT_FAMILY_NAME_DESC = [
    {'licenses.familyName.keyword': {'order': 'desc', 'nested': {'path': 'licenses'}}},
    {'licenses.givenName.keyword': {'order': 'desc', 'nested': {'path': 'licenses'}}},
    {'providerId': 'desc'},
    {'_id': 'asc'},
]

_PUBLIC_SEARCH_SORT_DATE_OF_UPDATE_ASC = [{'dateOfUpdate': 'asc'}, {'_id': 'asc'}]
_PUBLIC_SEARCH_SORT_DATE_OF_UPDATE_DESC = [{'dateOfUpdate': 'desc'}, {'_id': 'asc'}]


@mock_aws
class TestPublicSearchProviders(TstFunction):
    """Test suite for public_search_api_handler - public license search via OpenSearch."""

    def setUp(self):
        super().setUp()

    @staticmethod
    def _expected_public_search_request_body(
        *,
        licenses_nested_must: list,
        page_size: int = 10,
        sort: list | None = None,
        compact: str = 'cosm',
        search_after: list | None = None,
    ) -> dict:
        """Full OpenSearch search body for public license query (must stay aligned with public_search handler)."""
        body: dict = {
            'query': {
                'bool': {
                    'must': [
                        {'term': {'compact': compact}},
                        {
                            'nested': {
                                'path': 'licenses',
                                'query': {'bool': {'must': licenses_nested_must}},
                            }
                        },
                    ]
                }
            },
            'size': page_size,
            'sort': sort or _DEFAULT_PUBLIC_SEARCH_SORT_FAMILY_NAME_ASC,
        }
        if search_after is not None:
            body['search_after'] = search_after
        return body

    def _ingest_style_sanitize_opensearch_source(self, source: dict) -> dict:
        """
        Mirror production ingest behavior used by provider_update_ingest/populate_provider_documents.

        In prod we build raw docs then do:
        ProviderOpenSearchDocumentSchema().load(raw_doc) -> json roundtrip via ResponseEncoder
        (see lambdas/python/search/utils.py generate_provider_opensearch_documents).
        """
        from cc_common.data_model.schema.provider.api import ProviderOpenSearchDocumentSchema
        from cc_common.utils import ResponseEncoder

        # Only sanitize for supported compacts. Some tests intentionally construct
        # mismatched compacts to verify handler filtering; those documents would
        # never be produced by ingest and will fail schema validation.
        if source.get('compact') != 'cosm':
            return source

        schema = ProviderOpenSearchDocumentSchema()
        sanitized = schema.load(source)
        return json.loads(json.dumps(sanitized, cls=ResponseEncoder))

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

    def _minimal_opensearch_license(
        self,
        *,
        provider_id: str,
        compact: str,
        jurisdiction: str,
        license_number: str,
        license_type: str,
        given_name: str,
        family_name: str,
        date_of_expiration: str,
        license_status: str = 'active',
        jurisdiction_uploaded_compact_eligibility: str = 'eligible',
        adverse_actions: list | None = None,
    ) -> dict:
        """Nested license object sufficient for ProviderOpenSearchDocumentSchema / LicenseGeneralResponseSchema."""
        return {
            'providerId': provider_id,
            'type': 'license',
            'dateOfUpdate': DEFAULT_LICENSE_UPDATE_DATETIME,
            'compact': compact,
            'jurisdiction': jurisdiction,
            'licenseType': license_type,
            'licenseStatusName': 'OK',
            'licenseStatus': license_status,
            'jurisdictionUploadedLicenseStatus': 'active',
            # for simplicity in the test setup, we set this field to whatever was passed
            # in for the 'jurisdictionUploadedCompactEligibility' field. It will be recalculated
            # to its actual value when run through the '_ingest_style_sanitize_opensearch_source' method
            'compactEligibility': jurisdiction_uploaded_compact_eligibility,
            'jurisdictionUploadedCompactEligibility': jurisdiction_uploaded_compact_eligibility,
            'licenseNumber': license_number,
            'givenName': given_name,
            'familyName': family_name,
            'dateOfIssuance': DEFAULT_LICENSE_ISSUANCE_DATE,
            'dateOfExpiration': date_of_expiration,
            'dateOfBirth': '1985-06-06',
            'homeAddressStreet1': '123 A St.',
            'homeAddressCity': 'Columbus',
            'homeAddressState': 'oh',
            'homeAddressPostalCode': '43004',
            'mostRecentLicenseForType': True,
            'adverseActions': adverse_actions if adverse_actions is not None else [],
            'investigations': [],
        }

    def _minimal_opensearch_privilege(
        self,
        *,
        provider_id: str,
        compact: str,
        license_jurisdiction: str,
        license_type: str,
        privilege_jurisdiction: str,
        date_of_expiration: str,
        adverse_actions: list | None = None,
    ) -> dict:
        """Privilege row sufficient for PrivilegeGeneralResponseSchema / ingest sanitize."""
        return {
            'type': 'privilege',
            'providerId': provider_id,
            'compact': compact,
            'jurisdiction': privilege_jurisdiction,
            'licenseJurisdiction': license_jurisdiction,
            'licenseType': license_type,
            'dateOfExpiration': date_of_expiration,
            'adverseActions': adverse_actions if adverse_actions is not None else [],
            'investigations': [],
            'administratorSetStatus': 'active',
            'status': 'active',
        }

    def _generate_unlifted_license_adverse_action(self, *, provider_id: str) -> dict:
        return {
            'type': 'adverseAction',
            'compact': 'cosm',
            'providerId': provider_id,
            'jurisdiction': 'oh',
            'licenseTypeAbbreviation': 'cos',
            'licenseType': 'cosmetologist',
            'actionAgainst': 'license',
            'effectiveStartDate': '2024-01-01',
            'creationDate': '2024-01-01T00:00:00+00:00',
            'adverseActionId': 'aa-license-unlifted',
            'dateOfUpdate': '2024-01-02T00:00:00+00:00',
            'encumbranceType': 'suspension',
            'clinicalPrivilegeActionCategories': ['fraud'],
            'submittingUser': {'userId': 'staff-1'},
        }

    def _minimal_opensearch_provider_source(
        self,
        *,
        provider_id: str,
        compact: str,
        given_name: str,
        family_name: str,
        license_nested: dict,
        provider_adverse_actions: list | None = None,
        privileges: list | None = None,
    ) -> dict:
        """Top-level OpenSearch provider document sufficient for ProviderOpenSearchDocumentSchema."""
        lic_exp = license_nested['dateOfExpiration']
        source = {
            'providerId': provider_id,
            'type': 'provider',
            'dateOfUpdate': DEFAULT_PROVIDER_UPDATE_DATETIME,
            'compact': compact,
            'licenseJurisdiction': license_nested['jurisdiction'],
            'licenseStatus': license_nested['licenseStatus'],
            'compactEligibility': 'eligible',
            'givenName': given_name,
            'familyName': family_name,
            'dateOfExpiration': lic_exp,
            'jurisdictionUploadedLicenseStatus': 'active',
            'jurisdictionUploadedCompactEligibility': 'eligible',
            'birthMonthDay': '06-06',
            'licenses': [license_nested],
            'privileges': privileges if privileges is not None else [],
            'adverseActions': provider_adverse_actions or [],
        }
        return self._ingest_style_sanitize_opensearch_source(source)

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
        license_nested: dict | None = None,
        provider_adverse_actions: list | None = None,
        privileges: list | None = None,
    ) -> dict:
        """Create a mock OpenSearch hit for one document per license."""
        doc_id = f'{provider_id}#{jurisdiction}#{license_type}'
        nested = license_nested or self._minimal_opensearch_license(
            provider_id=provider_id,
            compact=compact,
            jurisdiction=jurisdiction,
            license_number=license_number,
            license_type=license_type,
            given_name=given_name,
            family_name=family_name,
            date_of_expiration='2035-01-01',
        )
        source = self._minimal_opensearch_provider_source(
            provider_id=provider_id,
            compact=compact,
            given_name=given_name,
            family_name=family_name,
            license_nested=nested,
            provider_adverse_actions=provider_adverse_actions,
            privileges=privileges,
        )
        hit = {
            '_index': f'compact_{compact}_providers',
            '_id': doc_id,
            '_source': source,
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
        self.assertEqual(
            self._expected_public_search_request_body(
                licenses_nested_must=[
                    _MOST_RECENT_LICENSE_FOR_TYPE_TERM,
                    {'term': {'licenses.licenseNumber': 'LN999'}},
                ],
            ),
            call_body,
        )

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
        self.assertEqual(
            self._expected_public_search_request_body(
                licenses_nested_must=[
                    _MOST_RECENT_LICENSE_FOR_TYPE_TERM,
                    {'term': {'licenses.jurisdiction': 'oh'}},
                    {'match': {'licenses.familyName': 'Smith'}},
                ],
            ),
            call_body,
        )

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
        self.assertEqual(
            self._expected_public_search_request_body(
                licenses_nested_must=[
                    _MOST_RECENT_LICENSE_FOR_TYPE_TERM,
                    {'match': {'licenses.familyName': 'Jones'}},
                ],
            ),
            call_body,
        )

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
        self.assertEqual(
            self._expected_public_search_request_body(
                licenses_nested_must=[
                    _MOST_RECENT_LICENSE_FOR_TYPE_TERM,
                    {'match': {'licenses.familyName': 'Doe'}},
                ],
            ),
            call_body,
        )
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
        self.assertEqual(
            self._expected_public_search_request_body(
                licenses_nested_must=[
                    _MOST_RECENT_LICENSE_FOR_TYPE_TERM,
                    {'match': {'licenses.familyName': 'Doe'}},
                ],
            ),
            call_body,
        )
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
        self.assertEqual(
            self._expected_public_search_request_body(
                licenses_nested_must=[
                    _MOST_RECENT_LICENSE_FOR_TYPE_TERM,
                    {'match': {'licenses.familyName': 'Doe'}},
                ],
                sort=_DEFAULT_PUBLIC_SEARCH_SORT_FAMILY_NAME_DESC,
            ),
            call_body,
        )
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
            self._expected_public_search_request_body(
                licenses_nested_must=[
                    _MOST_RECENT_LICENSE_FOR_TYPE_TERM,
                    {'term': {'licenses.licenseNumber': 'LN999'}},
                ],
                sort=_PUBLIC_SEARCH_SORT_DATE_OF_UPDATE_ASC,
            ),
            call_body,
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
            self._expected_public_search_request_body(
                licenses_nested_must=[
                    _MOST_RECENT_LICENSE_FOR_TYPE_TERM,
                    {'term': {'licenses.licenseNumber': 'LN999'}},
                ],
                sort=_PUBLIC_SEARCH_SORT_DATE_OF_UPDATE_DESC,
            ),
            call_body,
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
        call_body = mock_opensearch_client.search.call_args.kwargs['body']
        self.assertEqual(
            self._expected_public_search_request_body(
                licenses_nested_must=[
                    _MOST_RECENT_LICENSE_FOR_TYPE_TERM,
                    {'term': {'licenses.jurisdiction': 'oh'}},
                ],
            ),
            call_body,
        )
        body = json.loads(response['body'])
        self.assertIn('sorting', body)
        self.assertEqual({'key', 'direction'}, set(body['sorting'].keys()))

    @patch('handlers.public_search.opensearch_client')
    def test_unsupported_compact_returns_400(self, mock_opensearch_client):
        """Path compact not in config.compacts returns 400 and does not call OpenSearch."""
        from handlers.public_search import public_search_api_handler

        event = self._create_public_api_event(
            'not-a-compact',
            body={'query': {'familyName': 'Doe'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('compact', body['message'].lower())
        mock_opensearch_client.search.assert_not_called()

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

    @patch('handlers.public_search.opensearch_client')
    def test_no_search_criteria_returns_200(self, mock_opensearch_client):
        """Test that caller can provide an empty query body and still get a successful response."""
        from handlers.public_search import public_search_api_handler

        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 0, 'relation': 'eq'}, 'hits': []},
        }

        event = self._create_public_api_event(
            'cosm',
            body={'query': {}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(200, response['statusCode'])
        call_body = mock_opensearch_client.search.call_args.kwargs['body']
        self.assertEqual(
            self._expected_public_search_request_body(licenses_nested_must=[_MOST_RECENT_LICENSE_FOR_TYPE_TERM]),
            call_body,
        )
        body = json.loads(response['body'])
        self.assertEqual(
            {
                'pagination': {'lastKey': None, 'pageSize': 10, 'prevLastKey': None},
                'providers': [],
                'query': {},
                'sorting': {'direction': 'ascending', 'key': 'familyName'},
            },
            body,
        )

    def test_provider_id_in_query_returns_400(self):
        """Public query must not accept query.providerId (blocked at schema validation)."""
        from handlers.public_search import public_search_api_handler

        event = self._create_public_api_event(
            'cosm',
            body={
                'query': {
                    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'familyName': 'Doe',
                },
                'pagination': {'pageSize': 10},
            },
        )
        response = public_search_api_handler(event, self.mock_context)
        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('providerId', body['message'])

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
        self.assertEqual(
            self._expected_public_search_request_body(
                licenses_nested_must=[
                    _MOST_RECENT_LICENSE_FOR_TYPE_TERM,
                    {'match': {'licenses.familyName': 'Doe'}},
                ],
                page_size=25,
                search_after=['doe', 'jane', 'uuid-123', 'uuid-123#oh#cosmetologist'],
            ),
            call_body,
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

        single_hit = self._create_mock_hit()
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
        allowed = {
            'providerId',
            'givenName',
            'familyName',
            'licenseJurisdiction',
            'compact',
            'licenseType',
            'licenseNumber',
            'licenseEligibility',
        }
        self.assertEqual(set(provider.keys()), allowed)
        self.assertEqual(provider['licenseJurisdiction'], 'oh')
        self.assertEqual(provider['licenseType'], 'cosmetologist')
        self.assertEqual(provider['licenseNumber'], 'LN123')
        self.assertEqual(provider['licenseEligibility'], 'eligible')

    @patch('handlers.public_search.opensearch_client')
    @patch('cc_common.config._Config.expiration_resolution_date', date(2030, 1, 1))
    def test_license_eligibility_ineligible_when_license_expired(self, mock_opensearch_client):
        """Expired license (inactive after schema correction) yields licenseEligibility ineligible."""
        from handlers.public_search import public_search_api_handler

        pid = '00000000-0000-0000-0000-0000000000aa'
        nested = self._minimal_opensearch_license(
            provider_id=pid,
            compact='cosm',
            jurisdiction='oh',
            license_number='LN-EXP',
            license_type='cosmetologist',
            given_name='John',
            family_name='Doe',
            date_of_expiration='2020-01-01',
            license_status='active',
        )
        mock_hit = self._create_mock_hit(
            provider_id=pid,
            license_number='LN-EXP',
            license_nested=nested,
        )
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'licenseNumber': 'LN-EXP'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertEqual('ineligible', body['providers'][0]['licenseEligibility'])

    @patch('handlers.public_search.opensearch_client')
    @patch('cc_common.config._Config.expiration_resolution_date', date(2030, 1, 1))
    def test_license_eligibility_eligible_when_no_unlifted_adverse_action_on_license_or_privileges(
        self, mock_opensearch_client
    ):
        """LicenseEligibility is eligible when there are no unlifted adverse actions on the license or privileges."""
        from handlers.public_search import public_search_api_handler

        pid = '00000000-0000-0000-0000-0000000000bb'
        # create a unlifted adverse action for another license
        # which should not be considered
        unlifted = {
            'type': 'adverseAction',
            'compact': 'cosm',
            'providerId': pid,
            'jurisdiction': 'oh',
            'licenseTypeAbbreviation': 'cos',
            'licenseType': 'esthetician',
            'actionAgainst': 'license',
            'effectiveStartDate': '2024-01-01',
            'creationDate': '2024-01-01T00:00:00+00:00',
            'adverseActionId': 'aa-unlifted',
            'dateOfUpdate': '2024-01-02T00:00:00+00:00',
            'encumbranceType': 'suspension',
            'clinicalPrivilegeActionCategories': ['fraud'],
            'submittingUser': {'userId': 'staff-1'},
        }
        mock_hit = self._create_mock_hit(
            provider_id=pid,
            license_number='LN-AA',
            provider_adverse_actions=[unlifted],
        )
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'licenseNumber': 'LN-AA'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertEqual(body['providers'][0]['licenseEligibility'], 'eligible')

    @patch('handlers.public_search.opensearch_client')
    @patch('cc_common.config._Config.expiration_resolution_date', date(2030, 1, 1))
    def test_license_eligibility_set_to_ineligible_if_adverse_action_on_license(self, mock_opensearch_client):
        """Unlifted adverse action on the indexed license row marks licenseEligibility ineligible."""
        from handlers.public_search import public_search_api_handler

        pid = '00000000-0000-0000-0000-0000000000ee'
        unlifted = self._generate_unlifted_license_adverse_action(provider_id=pid)
        nested = self._minimal_opensearch_license(
            provider_id=pid,
            compact='cosm',
            jurisdiction='oh',
            license_number='LN-LIC-AA',
            license_type='cosmetologist',
            given_name='John',
            family_name='Doe',
            date_of_expiration='2035-01-01',
            adverse_actions=[unlifted],
        )
        mock_hit = self._create_mock_hit(
            provider_id=pid,
            license_number='LN-LIC-AA',
            license_nested=nested,
            provider_adverse_actions=[],
        )
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'licenseNumber': 'LN-LIC-AA'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertEqual('ineligible', body['providers'][0]['licenseEligibility'])

    @patch('handlers.public_search.opensearch_client')
    @patch('cc_common.config._Config.expiration_resolution_date', date(2030, 1, 1))
    def test_license_eligibility_set_to_ineligible_if_unlifted_adverse_action_on_privilege_for_license(
        self, mock_opensearch_client
    ):
        """Unlifted adverse action on a privilege bundled with the license doc marks licenseEligibility ineligible."""
        from handlers.public_search import public_search_api_handler

        pid = '00000000-0000-0000-0000-0000000000ff'
        unlifted = {
            'type': 'adverseAction',
            'compact': 'cosm',
            'providerId': pid,
            'jurisdiction': 'mi',
            'licenseTypeAbbreviation': 'cos',
            'licenseType': 'cosmetologist',
            'actionAgainst': 'privilege',
            'effectiveStartDate': '2024-01-01',
            'creationDate': '2024-01-01T00:00:00+00:00',
            'adverseActionId': 'aa-priv-unlifted',
            'dateOfUpdate': '2024-01-02T00:00:00+00:00',
            'encumbranceType': 'suspension',
            'clinicalPrivilegeActionCategories': ['fraud'],
            'submittingUser': {'userId': 'staff-1'},
        }
        nested = self._minimal_opensearch_license(
            provider_id=pid,
            compact='cosm',
            jurisdiction='oh',
            license_number='LN-PRIV-AA',
            license_type='cosmetologist',
            given_name='John',
            family_name='Doe',
            date_of_expiration='2035-01-01',
            adverse_actions=[],
        )
        privilege = self._minimal_opensearch_privilege(
            provider_id=pid,
            compact='cosm',
            license_jurisdiction='oh',
            license_type='cosmetologist',
            privilege_jurisdiction='mi',
            date_of_expiration='2035-01-01',
            adverse_actions=[unlifted],
        )
        mock_hit = self._create_mock_hit(
            provider_id=pid,
            license_number='LN-PRIV-AA',
            license_nested=nested,
            provider_adverse_actions=[],
            privileges=[privilege],
        )
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'licenseNumber': 'LN-PRIV-AA'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertEqual('ineligible', body['providers'][0]['licenseEligibility'])

    @patch('handlers.public_search.opensearch_client')
    @patch('cc_common.config._Config.expiration_resolution_date', date(2030, 1, 1))
    def test_license_eligibility_ineligible_when_jurisdiction_uploaded_ineligible(self, mock_opensearch_client):
        """jurisdictionUploadedCompactEligibility ineligible on the matched license yields ineligible."""
        from handlers.public_search import public_search_api_handler

        pid = '00000000-0000-0000-0000-0000000000cc'
        nested = self._minimal_opensearch_license(
            provider_id=pid,
            compact='cosm',
            jurisdiction='oh',
            license_number='LN-JUR',
            license_type='cosmetologist',
            given_name='John',
            family_name='Doe',
            date_of_expiration='2035-01-01',
            jurisdiction_uploaded_compact_eligibility='ineligible',
        )
        mock_hit = self._create_mock_hit(
            provider_id=pid,
            license_number='LN-JUR',
            license_nested=nested,
        )
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'licenseNumber': 'LN-JUR'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertEqual('ineligible', body['providers'][0]['licenseEligibility'])

    @patch('handlers.public_search.opensearch_client')
    @patch('cc_common.config._Config.expiration_resolution_date', date(2030, 1, 1))
    def test_license_eligibility_eligible_when_no_blocking_factors(self, mock_opensearch_client):
        """Active license, eligible jurisdiction upload, lifted adverse only -> eligible."""
        from handlers.public_search import public_search_api_handler

        pid = '00000000-0000-0000-0000-0000000000dd'
        lifted = {
            'type': 'adverseAction',
            'compact': 'cosm',
            'providerId': pid,
            'jurisdiction': 'oh',
            'licenseTypeAbbreviation': 'cos',
            'licenseType': 'cosmetologist',
            'actionAgainst': 'license',
            'effectiveStartDate': '2024-01-01',
            'creationDate': '2024-01-01T00:00:00+00:00',
            'adverseActionId': 'aa-lifted',
            'dateOfUpdate': '2024-06-01T00:00:00+00:00',
            'effectiveLiftDate': '2024-06-01',
            'encumbranceType': 'suspension',
            'clinicalPrivilegeActionCategories': ['fraud'],
            'submittingUser': {'userId': 'staff-1'},
        }
        mock_hit = self._create_mock_hit(
            provider_id=pid,
            license_number='LN-OK',
            provider_adverse_actions=[lifted],
        )
        mock_opensearch_client.search.return_value = {
            'hits': {'total': {'value': 1, 'relation': 'eq'}, 'hits': [mock_hit]},
        }
        event = self._create_public_api_event(
            'cosm',
            body={'query': {'licenseNumber': 'LN-OK'}, 'pagination': {'pageSize': 10}},
        )
        response = public_search_api_handler(event, self.mock_context)
        body = json.loads(response['body'])
        self.assertEqual(body['providers'][0]['licenseEligibility'], 'eligible')

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
