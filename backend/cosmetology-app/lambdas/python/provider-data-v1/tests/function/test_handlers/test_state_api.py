import json
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from common_test.sign_request import sign_request
from moto import mock_aws

from tests.function import TstFunction


@mock_aws
class SignatureTestBase(TstFunction):
    """Base class for tests that require signature authentication setup."""

    def setUp(self):
        super().setUp()
        # Load test keys for signature authentication
        with open('../common/tests/resources/client_private_key.pem') as f:
            self.private_key_pem = f.read()
        with open('../common/tests/resources/client_public_key.pem') as f:
            self.public_key_pem = f.read()

        # Load signature public keys into the compact configuration table for functional testing
        self._setup_signature_keys()

    def _setup_signature_keys(self):
        """Setup signature keys for testing. Override in subclasses to customize key setup."""
        # Default setup - load keys for 'cosm' compact with 'oh' and 'ne' jurisdictions
        self._load_signature_public_key('cosm', 'oh', 'test-key-001', self.public_key_pem)
        self._load_signature_public_key('cosm', 'ne', 'test-key-001', self.public_key_pem)

    def _load_signature_public_key(self, compact: str, jurisdiction: str, key_id: str, public_key_pem: str):
        """Load a signature public key into the compact configuration table."""
        item = {
            'pk': f'{compact}#SIGNATURE_KEYS#{jurisdiction}',
            'sk': f'{compact}#JURISDICTION#{jurisdiction}#{key_id}',
            'publicKey': public_key_pem,
            'compact': compact,
            'jurisdiction': jurisdiction,
            'keyId': key_id,
            'createdAt': '2024-01-01T00:00:00Z',
        }
        self._compact_configuration_table.put_item(Item=item)

    def _create_signed_event(self, event: dict) -> dict:
        """Add signature headers to an event for signature authentication."""
        from cc_common.config import config

        # Generate current timestamp and nonce
        timestamp = config.current_standard_datetime
        nonce = str(uuid4())
        key_id = 'test-key-001'

        # Sign the request
        headers = sign_request(
            method=event['httpMethod'],
            path=event['path'],
            query_params=event.get('queryStringParameters') or {},
            timestamp=timestamp.isoformat(),
            nonce=nonce,
            key_id=key_id,
            private_key_pem=self.private_key_pem,
        )

        # Add signature headers to event
        event['headers'].update(headers)
        return event


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestQueryJurisdictionProviders(SignatureTestBase):
    def _generate_multiple_providers_with_privileges(
        self,
        count: int,
        privilege_jurisdiction: str,
        license_jurisdiction: str,
        date_of_update: datetime,
        start_serial: int = 9999,
    ) -> list[str]:
        """Helper method to generate multiple providers with privileges in a specific jurisdiction."""
        provider_ids = []

        for i in range(count):
            # Generate unique provider ID for each provider
            provider_id = str(uuid4())
            provider_ids.append(provider_id)

            # Create provider record with privilegeJurisdictions already set correctly
            self.test_data_generator.put_default_provider_record_in_provider_table(
                value_overrides={
                    'providerId': provider_id,
                    'licenseJurisdiction': license_jurisdiction,
                    # Set the jurisdiction where we'll create privileges
                    'privilegeJurisdictions': {privilege_jurisdiction},
                    'ssnLastFour': str(start_serial - i),
                    'npi': f'{start_serial - i:010d}',
                    'givenName': f'Provider{i}',
                    'familyName': f'TestFamily{i}',
                },
                date_of_update_override=date_of_update.isoformat(),
            )

            # Create license record
            self.test_data_generator.put_default_license_record_in_provider_table(
                value_overrides={
                    'providerId': provider_id,
                    'jurisdiction': license_jurisdiction,
                    'ssnLastFour': str(start_serial - i),
                    'npi': f'{start_serial - i:010d}',
                    'licenseNumber': f'TEST-{start_serial - i}',
                    'givenName': f'Provider{i}',
                    'familyName': f'TestFamily{i}',
                },
                date_of_update_override=date_of_update.isoformat(),
            )

            # Create privilege record directly using TestDataGenerator
            self.test_data_generator.put_default_privilege_record_in_provider_table(
                value_overrides={
                    'providerId': provider_id,
                    'jurisdiction': privilege_jurisdiction,
                    'licenseJurisdiction': license_jurisdiction,
                    'privilegeId': f'SLP-{privilege_jurisdiction.upper()}-{start_serial - i}',
                },
                date_of_update_override=date_of_update.isoformat(),
            )

        return provider_ids

    def test_query_jurisdiction_providers_success(self):
        # Use a specific date for our test data
        date_of_update = datetime.fromisoformat('2024-11-08T12:00:00+00:00')

        # Generate 10 providers with privileges in 'oh' (home='ne', privilege_jurisdiction='oh')
        self._generate_multiple_providers_with_privileges(
            count=10,
            privilege_jurisdiction='oh',
            license_jurisdiction='ne',
            date_of_update=date_of_update,
            start_serial=9999,
        )

        # Generate 20 providers with licenses in 'oh' but privileges in 'ne' (not the target jurisdiction)
        # These should NOT be returned since the jurisdiction API only returns providers with privileges in the
        # requested jurisdiction.
        self._generate_multiple_providers_with_privileges(
            count=20,
            privilege_jurisdiction='ne',  # Privileges in 'ne', not target 'oh'
            license_jurisdiction='oh',
            date_of_update=date_of_update,
            start_serial=9989,
        )

        from handlers.state_api import query_jurisdiction_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        query = {'startDateTime': date_of_update.isoformat(), 'endDateTime': date_of_update.isoformat()}
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}
        event['body'] = json.dumps(
            {'query': query, 'pagination': {'pageSize': 30}, 'sorting': {'direction': 'ascending'}}
        )

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = query_jurisdiction_providers(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        # Should only return the 10 providers with privileges in 'oh', not the 20 with licenses in 'oh'
        self.assertEqual(10, len(body['providers']))
        self.assertEqual({'providers', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertEqual(query, body['query'])
        self.assertEqual({'direction': 'ascending'}, body['sorting'])
        # Check we're actually sorted by date of update
        dates_of_update = [provider['dateOfUpdate'] for provider in body['providers']]
        self.assertListEqual(sorted(dates_of_update), dates_of_update)

    def test_query_jurisdiction_providers_invalid_request_body(self):
        from handlers.state_api import query_jurisdiction_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}
        event['body'] = json.dumps({'invalid': 'field'})

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = query_jurisdiction_providers(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])

    def test_query_jurisdiction_providers_with_start_date_time_filter_not_supported(self):
        from handlers.state_api import query_jurisdiction_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}
        event['body'] = json.dumps(
            {
                'query': {'startDateTime': '2024-11-09T12:00:00+00:00'},
                'pagination': {'pageSize': 20},
                'sorting': {'direction': 'ascending'},
            }
        )

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = query_jurisdiction_providers(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])

    def test_query_jurisdiction_providers_with_end_date_time_filter_not_supported(self):
        from handlers.state_api import query_jurisdiction_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}
        event['body'] = json.dumps(
            {
                'query': {'endDateTime': '2024-11-08T12:00:00+00:00'},
                'pagination': {'pageSize': 20},
                'sorting': {'direction': 'ascending'},
            }
        )

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = query_jurisdiction_providers(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])

    def test_query_jurisdiction_providers_with_date_range_filter(self):
        # Generate providers with different update dates
        middle_date = datetime.fromisoformat('2024-11-08T23:59:59+00:00')
        early_date = middle_date - timedelta(hours=2)
        late_date = middle_date + timedelta(hours=2)

        # Providers with early date (should be excluded)
        self._generate_multiple_providers_with_privileges(
            count=10,
            privilege_jurisdiction='oh',
            license_jurisdiction='ne',
            date_of_update=early_date,
            start_serial=9999,
        )

        # Providers with middle date (should be included)
        self._generate_multiple_providers_with_privileges(
            count=10,
            privilege_jurisdiction='oh',
            license_jurisdiction='ne',
            date_of_update=middle_date,
            start_serial=9989,
        )

        # Providers with late date (should be excluded)
        self._generate_multiple_providers_with_privileges(
            count=10,
            privilege_jurisdiction='oh',
            license_jurisdiction='ne',
            date_of_update=late_date,
            start_serial=9979,
        )

        from handlers.state_api import query_jurisdiction_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}
        event['body'] = json.dumps(
            {
                'query': {
                    'startDateTime': (middle_date - timedelta(hours=1)).isoformat(),
                    'endDateTime': (middle_date + timedelta(hours=1)).isoformat(),
                },
                'pagination': {'pageSize': 30},
                'sorting': {'direction': 'ascending'},
            }
        )

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = query_jurisdiction_providers(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        # Should only return the 10 providers updated within the date range
        self.assertEqual(10, len(body['providers']))
        self.assertEqual({'providers', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertEqual(
            {
                'startDateTime': (middle_date - timedelta(hours=1)).isoformat(),
                'endDateTime': (middle_date + timedelta(hours=1)).isoformat(),
            },
            body['query'],
        )
        # All returned providers should have dateOfUpdate from the middle date
        for provider in body['providers']:
            self.assertEqual(provider['dateOfUpdate'], middle_date.isoformat())

    def test_query_jurisdiction_providers_with_invalid_date_format(self):
        from handlers.state_api import query_jurisdiction_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}
        event['body'] = json.dumps(
            {
                'query': {'startDateTime': 'invalid-date-format', 'endDateTime': 'invalid-date-format'},
                'pagination': {'pageSize': 10},
            }
        )

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = query_jurisdiction_providers(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])

    def test_query_jurisdiction_providers_date_filter_larger_than_7_days_not_allowed(self):
        from handlers.state_api import query_jurisdiction_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}
        event['body'] = json.dumps(
            {
                'query': {'startDateTime': '2024-11-08T12:00:00+00:00', 'endDateTime': '2024-11-15T12:01:00+00:00'},
                'pagination': {'pageSize': 10},
                'sorting': {'direction': 'ascending'},
            }
        )

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = query_jurisdiction_providers(event, self.mock_context)
        self.assertEqual(400, resp['statusCode'])

    def test_query_jurisdiction_providers_missing_signature_rejected(self):
        """Test that query jurisdiction providers is rejected when signature authentication is missing."""
        from handlers.state_api import query_jurisdiction_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}
        event['body'] = json.dumps({'query': {}, 'pagination': {'pageSize': 30}, 'sorting': {'direction': 'ascending'}})

        # Do NOT add signature authentication headers - this should cause the request to be rejected
        # since @required_signature_auth is used

        resp = query_jurisdiction_providers(event, self.mock_context)

        self.assertEqual(401, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertIn('message', body)
        # The error message should indicate missing required signature authentication headers
        self.assertIn('x-key-id', body['message'].lower())


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
@patch('cc_common.config._Config.api_base_url', 'https://app.compactconnect.org')
class TestGetProvider(SignatureTestBase):
    def _generate_provider_with_privilege_in_jurisdiction(
        self, privilege_jurisdiction: str, license_jurisdiction: str
    ) -> str:
        """Helper method to generate a provider with a privilege in a specific jurisdiction."""

        # Create a provider with privileges in the specified jurisdictions using test_data_generator
        provider = self.test_data_generator.put_default_provider_record_in_provider_table(
            value_overrides={
                'licenseJurisdiction': license_jurisdiction,
                # Set the jurisdiction where we'll create privileges
                'privilegeJurisdictions': {privilege_jurisdiction},
            }
        )

        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'providerId': str(provider.providerId),
                'jurisdiction': license_jurisdiction,
            }
        )

        # Create privilege record directly using TestDataGenerator
        self.test_data_generator.put_default_privilege_record_in_provider_table(
            value_overrides={
                'providerId': str(provider.providerId),
                'jurisdiction': privilege_jurisdiction,
                'licenseJurisdiction': license_jurisdiction,
                'privilegeId': f'SLP-{privilege_jurisdiction.upper()}-1',
            }
        )

        return str(provider.providerId)

    def test_get_provider_success_with_general_permissions(self):
        """Test successful provider retrieval with general read permissions."""
        # Create a provider with privileges in 'ne' jurisdiction (matches test data)
        provider = self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()
        self.test_data_generator.put_default_privilege_record_in_provider_table()
        provider_id = str(provider.providerId)

        from handlers.state_api import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'ne', 'providerId': provider_id}

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])

        # Prepare expected response based on test data
        expected_response = {
            'privileges': [
                {
                    'type': 'statePrivilege',
                    'providerId': provider_id,
                    'compact': 'cosm',
                    'jurisdiction': 'ne',
                    'licenseType': 'cosmetologist',
                    'privilegeId': 'COS-NE-1',
                    'licenseNumber': 'A0608337260',
                    'npi': '0608337260',
                    'status': 'active',
                    'compactEligibility': 'eligible',
                    'dateOfExpiration': '2025-04-04',
                    'dateOfIssuance': '2016-05-05T12:59:59+00:00',
                    'dateOfRenewal': '2020-05-05T12:59:59+00:00',
                    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                    'familyName': 'Guðmundsdóttir',
                    'givenName': 'Björk',
                    'licenseJurisdiction': 'oh',
                    'licenseStatus': 'active',
                    'middleName': 'Gunnar',
                    'licenseStatusName': 'DEFINITELY_A_HUMAN',
                    # Private fields should NOT be present
                }
            ],
            'providerUIUrl': f'https://app.compactconnect.org/cosm/Licensing/{provider_id}',
        }

        self.maxDiff = None
        self.assertEqual(expected_response, body)

        # Explicitly assert private fields are not present
        privilege = body['privileges'][0]
        self.assertNotIn('ssnLastFour', privilege)
        self.assertNotIn('emailAddress', privilege)
        self.assertNotIn('dateOfBirth', privilege)
        self.assertNotIn('homeAddressStreet1', privilege)
        self.assertNotIn('phoneNumber', privilege)

    def test_get_provider_success_with_private_permissions(self):
        """Test successful provider retrieval with private read permissions."""
        # Create a provider with privileges in 'ne' jurisdiction
        # Create a provider with privileges in 'ne' jurisdiction (matches test data)
        provider = self.test_data_generator.put_default_provider_record_in_provider_table()
        self.test_data_generator.put_default_license_record_in_provider_table()
        self.test_data_generator.put_default_privilege_record_in_provider_table()
        provider_id = str(provider.providerId)

        from handlers.state_api import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # Grant private read permissions
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral cosm/readPrivate'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'ne', 'providerId': provider_id}

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])

        # Prepare expected response with private fields included
        expected_response = {
            'privileges': [
                {
                    'type': 'statePrivilege',
                    'providerId': provider_id,
                    'compact': 'cosm',
                    'jurisdiction': 'ne',
                    'licenseType': 'cosmetologist',
                    'privilegeId': 'COS-NE-1',
                    'status': 'active',
                    'compactEligibility': 'eligible',
                    'dateOfExpiration': '2025-04-04',
                    'dateOfIssuance': '2016-05-05T12:59:59+00:00',
                    'dateOfRenewal': '2020-05-05T12:59:59+00:00',
                    'dateOfUpdate': '2024-11-08T23:59:59+00:00',
                    'familyName': 'Guðmundsdóttir',
                    'givenName': 'Björk',
                    'licenseJurisdiction': 'oh',
                    'licenseStatus': 'active',
                    'middleName': 'Gunnar',
                    'licenseStatusName': 'DEFINITELY_A_HUMAN',
                    # Private fields should be included
                    'ssnLastFour': '1234',
                    'emailAddress': 'björk@example.com',
                    'dateOfBirth': '1985-06-06',
                    'homeAddressStreet1': '123 A St.',
                    'homeAddressStreet2': 'Apt 321',
                    'homeAddressCity': 'Columbus',
                    'homeAddressState': 'oh',
                    'homeAddressPostalCode': '43004',
                    'phoneNumber': '+13213214321',
                    'npi': '0608337260',
                    'licenseNumber': 'A0608337260',
                }
            ],
            'providerUIUrl': f'https://app.compactconnect.org/cosm/Licensing/{provider_id}',
        }

        self.maxDiff = None
        self.assertEqual(expected_response, body)

    def test_get_provider_success_with_jurisdiction_specific_private_permissions(self):
        """Test successful provider retrieval with jurisdiction-specific private read permissions."""
        # Create a provider with privileges in 'ne' jurisdiction
        provider_id = self._generate_provider_with_privilege_in_jurisdiction(
            privilege_jurisdiction='ne', license_jurisdiction='oh'
        )

        from handlers.state_api import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # Grant jurisdiction-specific private read permissions for 'oh' (license jurisdiction)
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral oh/cosm.readPrivate'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'ne', 'providerId': provider_id}

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])

        # Should include private fields due to jurisdiction-specific permissions
        self.assertIn('ssnLastFour', body['privileges'][0])
        self.assertIn('emailAddress', body['privileges'][0])

    def test_get_provider_with_privilege_in_jurisdiction(self):
        """Test provider with a privilege in the requested jurisdiction."""
        # Create a provider with a privilege in 'ne'
        provider_id = self._generate_provider_with_privilege_in_jurisdiction(
            privilege_jurisdiction='ne', license_jurisdiction='oh'
        )

        from handlers.state_api import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'ne', 'providerId': provider_id}

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        # Should have the privilege in the requested jurisdiction
        self.assertEqual(len(body['privileges']), 1)

        # All privileges should be in the requested jurisdiction
        for privilege in body['privileges']:
            self.assertEqual('ne', privilege['jurisdiction'])

    def test_get_provider_no_privileges_in_jurisdiction(self):
        """Test provider with no privileges in the requested jurisdiction."""
        # Create a provider with privileges only in 'ne', not 'oh'
        provider_id = self._generate_provider_with_privilege_in_jurisdiction(
            privilege_jurisdiction='ne', license_jurisdiction='oh'
        )

        from handlers.state_api import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh', 'providerId': provider_id}

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = get_provider(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_get_provider_nonexistent_provider(self):
        """Test requesting a nonexistent provider."""
        from handlers.state_api import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'ne', 'providerId': 'nonexistent-provider'}

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = get_provider(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def test_get_provider_missing_parameters(self):
        """Test request with missing required parameters."""
        from handlers.state_api import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm'}  # Missing jurisdiction and providerId

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = get_provider(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_get_provider_missing_signature_rejected(self):
        """Test that get provider is rejected when signature authentication is missing."""
        from handlers.state_api import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'ne', 'providerId': 'test-provider-id'}

        # Do NOT add signature authentication headers - this should cause the request to be rejected
        # since @required_signature_auth is used

        resp = get_provider(event, self.mock_context)

        self.assertEqual(401, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertIn('message', body)
        # The error message should indicate missing required signature authentication headers
        self.assertIn('x-key-id', body['message'].lower())


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestBulkUploadUrlHandler(SignatureTestBase):
    def _setup_signature_keys(self):
        """Setup signature keys for testing. Only need 'oh' jurisdiction for this test."""

        self._load_signature_public_key('cosm', 'oh', 'test-key-001', self.public_key_pem)

    def test_bulk_upload_url_handler_success(self):
        """Test successful bulk upload URL generation with optional signature authentication."""
        from handlers.state_api import bulk_upload_url_handler

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for cosm/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral oh/cosm.write'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}

        # Add signature authentication headers
        event = self._create_signed_event(event)

        resp = bulk_upload_url_handler(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertIn('upload', body)
        upload = body['upload']
        self.assertIn('url', upload)
        self.assertIn('fields', upload)
        self.assertIn('key', upload['fields'])
        self.assertIn('policy', upload['fields'])
        self.assertIn('x-amz-algorithm', upload['fields'])
        self.assertIn('x-amz-credential', upload['fields'])
        self.assertIn('x-amz-date', upload['fields'])
        self.assertIn('x-amz-signature', upload['fields'])

        # Verify the key follows the expected pattern: compact/jurisdiction/uuid
        key = upload['fields']['key']
        self.assertTrue(key.startswith('cosm/oh/'))
        self.assertEqual(len(key.split('/')), 3)

    def test_bulk_upload_url_handler_missing_signature_rejected(self):
        """
        Test that bulk upload URL generation is rejected when signature keys are configured but no signature is
        provided.
        """
        from handlers.state_api import bulk_upload_url_handler

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has write permission for cosm/oh
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email cosm/readGeneral oh/cosm.write'
        event['pathParameters'] = {'compact': 'cosm', 'jurisdiction': 'oh'}

        # Do NOT add signature authentication headers - this should cause the request to be rejected
        # since signature keys are configured for this compact/jurisdiction

        resp = bulk_upload_url_handler(event, self.mock_context)

        self.assertEqual(401, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertIn('message', body)
        # The error message should indicate missing required signature authentication headers
        self.assertIn('x-key-id', body['message'].lower())
