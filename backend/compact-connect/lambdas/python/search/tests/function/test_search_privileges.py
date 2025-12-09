import json
from unittest.mock import Mock, patch

from moto import mock_aws

from . import TstFunction


@mock_aws
class TestExportPrivileges(TstFunction):
    """Test suite for search_api_handler - privilege export functionality."""

    def setUp(self):
        super().setUp()

    def _create_api_event(self, compact: str, body: dict = None) -> dict:
        """Create a standard API Gateway event for export_privileges."""
        return {
            'resource': '/v1/compacts/{compact}/privileges/export',
            'path': f'/v1/compacts/{compact}/privileges/export',
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
                'resourcePath': '/v1/compacts/{compact}/privileges/export',
                'httpMethod': 'POST',
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-id',
                        'cognito:username': 'test-user',
                    }
                },
            },
            'body': json.dumps(body) if body else None,
            'isBase64Encoded': False,
        }

    def _when_testing_mock_opensearch_client(self, mock_opensearch_client, search_response: dict = None):
        """
        Configure the mock OpenSearchClient for testing.

        :param mock_opensearch_client: The patched OpenSearchClient class
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

        mock_client_instance = Mock()
        mock_opensearch_client.return_value = mock_client_instance
        mock_client_instance.search.return_value = search_response
        return mock_client_instance

    def _create_mock_provider_hit_with_privileges(
        self,
        provider_id: str = '00000000-0000-0000-0000-000000000001',
        compact: str = 'aslp',
        sort_values: list = None,
    ) -> dict:
        """Create a mock OpenSearch hit for a provider document with privileges and licenses."""
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
                'licenses': [
                    {
                        'providerId': provider_id,
                        'type': 'license-home',
                        'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                        'compact': compact,
                        'jurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'licenseStatus': 'active',
                        'compactEligibility': 'eligible',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
                        'givenName': 'John',
                        'familyName': 'Doe',
                        'dateOfIssuance': '2020-01-01',
                        'dateOfRenewal': '2024-01-01',
                        'dateOfExpiration': '2025-12-31',
                        'npi': '1234567890',
                        'licenseNumber': 'AUD-12345',
                    }
                ],
                'privileges': [
                    {
                        'type': 'privilege',
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': 'ky',
                        'licenseJurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'dateOfIssuance': '2024-01-15',
                        'dateOfRenewal': '2024-01-15',
                        'dateOfExpiration': '2025-01-15',
                        'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                        'administratorSetStatus': 'active',
                        'privilegeId': 'PRIV-001',
                        'status': 'active',
                    }
                ],
            },
        }
        if sort_values:
            hit['sort'] = sort_values
        return hit

    @patch('handlers.search.OpenSearchClient')
    def test_privilege_export_returns_presigned_url(self, mock_opensearch_client):
        """Test that privilege export returns a presigned URL to a CSV file."""
        from handlers.search import search_api_handler

        # Create a mock response with provider hits containing privileges
        mock_hit = self._create_mock_provider_hit_with_privileges()
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

        # Verify response contains fileUrl
        self.assertIn('fileUrl', body)
        self.assertIsInstance(body['fileUrl'], str)
        # Verify the URL contains expected parts
        self.assertIn('test-export-results-bucket', body['fileUrl'])
        self.assertIn('compact/aslp/privilegeSearch', body['fileUrl'])
        self.assertIn('test-user-id', body['fileUrl'])  # caller user id from event
        self.assertIn('export.csv', body['fileUrl'])

        # Verify the CSV file was uploaded to S3 by checking the bucket
        import boto3

        s3_client = boto3.client('s3')
        response = s3_client.list_objects_v2(
            Bucket='test-export-results-bucket', Prefix='compact/aslp/privilegeSearch/caller/test-user-id'
        )
        self.assertEqual(1, response['KeyCount'])

        # Get the CSV content and verify it contains the expected data
        key = response['Contents'][0]['Key']
        csv_obj = s3_client.get_object(Bucket='test-export-results-bucket', Key=key)
        csv_content = csv_obj['Body'].read().decode('utf-8')

        # Verify CSV contains header and data
        self.assertIn('type,providerId,compact,jurisdiction', csv_content)
        self.assertIn('statePrivilege', csv_content)
        self.assertIn('00000000-0000-0000-0000-000000000001', csv_content)
        self.assertIn('PRIV-001', csv_content)

    @patch('handlers.search.OpenSearchClient')
    def test_privilege_export_with_empty_results_returns_404(self, mock_opensearch_client):
        """Test that privilege export with no results returns a 404 error."""
        from handlers.search import search_api_handler

        search_response = {
            'hits': {
                'total': {'value': 0, 'relation': 'eq'},
                'hits': [],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        event = self._create_api_event('aslp', body={'query': {'match_all': {}}})

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(404, response['statusCode'])
        body = json.loads(response['body'])

        # Verify response contains error message
        self.assertIn('message', body)
        self.assertEqual('The search parameters did not match any privileges.', body['message'])

        # Verify no CSV file was uploaded to S3
        import boto3

        s3_client = boto3.client('s3')
        response = s3_client.list_objects_v2(
            Bucket='test-export-results-bucket', Prefix='compact/aslp/privilegeSearch/caller/test-user-id'
        )
        # Should have no objects
        self.assertEqual(0, response.get('KeyCount', 0))

    @patch('handlers.search.OpenSearchClient')
    def test_privilege_export_skips_provider_without_privileges_returns_404(self, mock_opensearch_client):
        """Test that providers without privileges result in a 404 error."""
        from handlers.search import search_api_handler

        # Create a provider hit without privileges
        hit = {
            '_index': 'compact_aslp_providers',
            '_id': 'provider-1',
            '_score': 1.0,
            '_source': {
                'providerId': 'provider-1',
                'type': 'provider',
                'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                'compact': 'aslp',
                'licenseJurisdiction': 'oh',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
                'givenName': 'Jane',
                'familyName': 'Smith',
                'dateOfExpiration': '2025-12-31',
                'jurisdictionUploadedLicenseStatus': 'active',
                'jurisdictionUploadedCompactEligibility': 'eligible',
                'birthMonthDay': '03-20',
                'licenses': [],
                'privileges': [],
            },
        }
        search_response = {
            'hits': {
                'total': {'value': 1, 'relation': 'eq'},
                'hits': [hit],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        event = self._create_api_event('aslp', body={'query': {'match_all': {}}})

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(404, response['statusCode'])
        body = json.loads(response['body'])

        # Verify response contains error message
        self.assertIn('message', body)
        self.assertEqual('The search parameters did not match any privileges.', body['message'])

        # Verify no CSV file was uploaded to S3
        import boto3

        s3_client = boto3.client('s3')
        response = s3_client.list_objects_v2(
            Bucket='test-export-results-bucket', Prefix='compact/aslp/privilegeSearch/caller/test-user-id'
        )
        # Should have no objects
        self.assertEqual(0, response.get('KeyCount', 0))

    @patch('handlers.search.OpenSearchClient')
    def test_privilege_export_with_multiple_inner_hits_exports_all_matched(self, mock_opensearch_client):
        """Test that when inner_hits contains multiple matches, all are exported to CSV."""
        from handlers.search import search_api_handler

        provider_id = '00000000-0000-0000-0000-000000000001'
        compact = 'aslp'

        # Create a provider with multiple privileges, inner_hits matches two of them
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
                'licenses': [
                    {
                        'providerId': provider_id,
                        'type': 'license-home',
                        'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                        'compact': compact,
                        'jurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'licenseStatus': 'active',
                        'compactEligibility': 'eligible',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
                        'givenName': 'John',
                        'familyName': 'Doe',
                        'dateOfIssuance': '2020-01-01',
                        'dateOfRenewal': '2024-01-01',
                        'dateOfExpiration': '2025-12-31',
                        'npi': '1234567890',
                        'licenseNumber': 'AUD-12345',
                    }
                ],
                # Provider has THREE privileges
                'privileges': [
                    {
                        'type': 'privilege',
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': 'ky',
                        'licenseJurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'dateOfIssuance': '2024-01-15',
                        'dateOfRenewal': '2024-01-15',
                        'dateOfExpiration': '2025-01-15',
                        'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                        'administratorSetStatus': 'active',
                        'privilegeId': 'PRIV-KY-001',
                        'status': 'active',
                    },
                    {
                        'type': 'privilege',
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': 'ne',
                        'licenseJurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'dateOfIssuance': '2024-02-01',
                        'dateOfRenewal': '2024-02-01',
                        'dateOfExpiration': '2025-02-01',
                        'dateOfUpdate': '2024-02-01T10:30:00+00:00',
                        'administratorSetStatus': 'active',
                        'privilegeId': 'PRIV-NE-001',
                        'status': 'active',
                    },
                    {
                        'type': 'privilege',
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': 'co',
                        'licenseJurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'dateOfIssuance': '2024-03-01',
                        'dateOfRenewal': '2024-03-01',
                        'dateOfExpiration': '2025-03-01',
                        'dateOfUpdate': '2024-03-01T10:30:00+00:00',
                        'administratorSetStatus': 'inactive',
                        'privilegeId': 'PRIV-CO-001',
                        'status': 'inactive',
                    },
                ],
            },
            # inner_hits contains TWO active privileges (simulating nested query for status: active)
            'inner_hits': {
                'privileges': {
                    'hits': {
                        'total': {'value': 2, 'relation': 'eq'},
                        'hits': [
                            {
                                '_index': f'compact_{compact}_providers',
                                '_id': provider_id,
                                '_nested': {'field': 'privileges', 'offset': 0},
                                '_score': 1.0,
                                '_source': {
                                    'type': 'privilege',
                                    'providerId': provider_id,
                                    'compact': compact,
                                    'jurisdiction': 'ky',
                                    'licenseJurisdiction': 'oh',
                                    'licenseType': 'audiologist',
                                    'dateOfIssuance': '2024-01-15',
                                    'dateOfRenewal': '2024-01-15',
                                    'dateOfExpiration': '2025-01-15',
                                    'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                                    'administratorSetStatus': 'active',
                                    'privilegeId': 'PRIV-KY-001',
                                    'status': 'active',
                                },
                            },
                            {
                                '_index': f'compact_{compact}_providers',
                                '_id': provider_id,
                                '_nested': {'field': 'privileges', 'offset': 1},
                                '_score': 1.0,
                                '_source': {
                                    'type': 'privilege',
                                    'providerId': provider_id,
                                    'compact': compact,
                                    'jurisdiction': 'ne',
                                    'licenseJurisdiction': 'oh',
                                    'licenseType': 'audiologist',
                                    'dateOfIssuance': '2024-02-01',
                                    'dateOfRenewal': '2024-02-01',
                                    'dateOfExpiration': '2025-02-01',
                                    'dateOfUpdate': '2024-02-01T10:30:00+00:00',
                                    'administratorSetStatus': 'active',
                                    'privilegeId': 'PRIV-NE-001',
                                    'status': 'active',
                                },
                            },
                        ],
                    }
                }
            },
        }

        search_response = {
            'hits': {
                'total': {'value': 1, 'relation': 'eq'},
                'hits': [hit],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        event = self._create_api_event('aslp', body={'query': {'match_all': {}}})

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])

        # Verify response contains fileUrl
        self.assertIn('fileUrl', body)

        # Verify the CSV contains only the 2 matched privileges
        import boto3

        s3_client = boto3.client('s3')
        response = s3_client.list_objects_v2(
            Bucket='test-export-results-bucket', Prefix='compact/aslp/privilegeSearch/caller/test-user-id'
        )
        key = response['Contents'][0]['Key']
        csv_obj = s3_client.get_object(Bucket='test-export-results-bucket', Key=key)
        csv_content = csv_obj['Body'].read().decode('utf-8')

        lines = csv_content.strip().split('\n')
        self.assertEqual(3, len(lines))# Header + 2 data rows
        self.assertEqual('type,providerId,compact,jurisdiction,licenseType,privilegeId,status,compactEligibility,dateOfExpiration,dateOfIssuance,dateOfRenewal,familyName,givenName,middleName,suffix,licenseJurisdiction,licenseStatus,licenseStatusName,licenseNumber,npi\r', lines[0])
        self.assertEqual('statePrivilege,00000000-0000-0000-0000-000000000001,aslp,ky,audiologist,PRIV-KY-001,active,eligible,2025-01-15,2024-01-15,2024-01-15,Doe,John,,,oh,active,,AUD-12345,1234567890\r', lines[1])
        self.assertEqual('statePrivilege,00000000-0000-0000-0000-000000000001,aslp,ne,audiologist,PRIV-NE-001,active,eligible,2025-02-01,2024-02-01,2024-02-01,Doe,John,,,oh,active,,AUD-12345,1234567890', lines[2])

    @patch('handlers.search.OpenSearchClient')
    def test_privilege_export_without_inner_hits_exports_all_privileges(self, mock_opensearch_client):
        """Test that without inner_hits, all privileges for matching providers are exported."""
        from handlers.search import search_api_handler

        provider_id = '00000000-0000-0000-0000-000000000001'
        compact = 'aslp'

        # Create a provider with multiple privileges and NO inner_hits
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
                'licenses': [
                    {
                        'providerId': provider_id,
                        'type': 'license-home',
                        'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                        'compact': compact,
                        'jurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'licenseStatus': 'active',
                        'compactEligibility': 'eligible',
                        'jurisdictionUploadedLicenseStatus': 'active',
                        'jurisdictionUploadedCompactEligibility': 'eligible',
                        'givenName': 'John',
                        'familyName': 'Doe',
                        'dateOfIssuance': '2020-01-01',
                        'dateOfRenewal': '2024-01-01',
                        'dateOfExpiration': '2025-12-31',
                        'npi': '1234567890',
                        'licenseNumber': 'AUD-12345',
                    }
                ],
                # Provider has THREE privileges
                'privileges': [
                    {
                        'type': 'privilege',
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': 'ky',
                        'licenseJurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'dateOfIssuance': '2024-01-15',
                        'dateOfRenewal': '2024-01-15',
                        'dateOfExpiration': '2025-01-15',
                        'dateOfUpdate': '2024-01-15T10:30:00+00:00',
                        'administratorSetStatus': 'active',
                        'privilegeId': 'PRIV-KY-001',
                        'status': 'active',
                    },
                    {
                        'type': 'privilege',
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': 'ne',
                        'licenseJurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'dateOfIssuance': '2024-02-01',
                        'dateOfRenewal': '2024-02-01',
                        'dateOfExpiration': '2025-02-01',
                        'dateOfUpdate': '2024-02-01T10:30:00+00:00',
                        'administratorSetStatus': 'active',
                        'privilegeId': 'PRIV-NE-001',
                        'status': 'active',
                    },
                    {
                        'type': 'privilege',
                        'providerId': provider_id,
                        'compact': compact,
                        'jurisdiction': 'co',
                        'licenseJurisdiction': 'oh',
                        'licenseType': 'audiologist',
                        'dateOfIssuance': '2024-03-01',
                        'dateOfRenewal': '2024-03-01',
                        'dateOfExpiration': '2025-03-01',
                        'dateOfUpdate': '2024-03-01T10:30:00+00:00',
                        'administratorSetStatus': 'inactive',
                        'privilegeId': 'PRIV-CO-001',
                        'status': 'inactive',
                    },
                ],
            },
            # No inner_hits - regular query without nested
        }

        search_response = {
            'hits': {
                'total': {'value': 1, 'relation': 'eq'},
                'hits': [hit],
            }
        }
        self._when_testing_mock_opensearch_client(mock_opensearch_client, search_response=search_response)

        event = self._create_api_event('aslp', body={'query': {'match_all': {}}})

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(200, response['statusCode'])
        body = json.loads(response['body'])

        # Verify response contains fileUrl
        self.assertIn('fileUrl', body)

        # Verify the CSV contains all 3 privileges
        import boto3

        s3_client = boto3.client('s3')
        response = s3_client.list_objects_v2(
            Bucket='test-export-results-bucket', Prefix='compact/aslp/privilegeSearch/caller/test-user-id'
        )
        key = response['Contents'][0]['Key']
        csv_obj = s3_client.get_object(Bucket='test-export-results-bucket', Key=key)
        csv_content = csv_obj['Body'].read().decode('utf-8')

        lines = csv_content.strip().split('\n')
        self.assertEqual(4, len(lines))  # Header + 3 data rows
        self.assertEqual('type,providerId,compact,jurisdiction,licenseType,privilegeId,status,compactEligibility,dateOfExpiration,dateOfIssuance,dateOfRenewal,familyName,givenName,middleName,suffix,licenseJurisdiction,licenseStatus,licenseStatusName,licenseNumber,npi\r', lines[0])
        self.assertEqual('statePrivilege,00000000-0000-0000-0000-000000000001,aslp,ky,audiologist,PRIV-KY-001,active,eligible,2025-01-15,2024-01-15,2024-01-15,Doe,John,,,oh,active,,AUD-12345,1234567890\r', lines[1])
        self.assertEqual('statePrivilege,00000000-0000-0000-0000-000000000001,aslp,ne,audiologist,PRIV-NE-001,active,eligible,2025-02-01,2024-02-01,2024-02-01,Doe,John,,,oh,active,,AUD-12345,1234567890\r', lines[2])
        self.assertEqual('statePrivilege,00000000-0000-0000-0000-000000000001,aslp,co,audiologist,PRIV-CO-001,inactive,eligible,2025-03-01,2024-03-01,2024-03-01,Doe,John,,,oh,active,,AUD-12345,1234567890', lines[3])


    def test_unsupported_route_returns_400(self):
        """Test that unsupported routes return a 400 error."""
        from handlers.search import search_api_handler

        # Create event with unsupported route
        event = {
            'resource': '/v1/compacts/{compact}/unknown/search',
            'path': '/v1/compacts/aslp/unknown/search',
            'httpMethod': 'POST',
            'headers': {
                'Content-Type': 'application/json',
                'origin': 'https://example.org',
            },
            'multiValueHeaders': {},
            'queryStringParameters': None,
            'pathParameters': {'compact': 'aslp'},
            'requestContext': {
                'resourcePath': '/v1/compacts/{compact}/unknown/search',
                'httpMethod': 'POST',
                'authorizer': {
                    'claims': {
                        'sub': 'test-user-id',
                        'cognito:username': 'test-user',
                    }
                },
            },
            'body': json.dumps({'query': {'match_all': {}}}),
            'isBase64Encoded': False,
        }

        response = search_api_handler(event, self.mock_context)

        self.assertEqual(400, response['statusCode'])
        body = json.loads(response['body'])
        self.assertIn('Unsupported method or resource', body['message'])
