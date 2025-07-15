import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import quote

from moto import mock_aws

from .. import TstFunction


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestQueryProviders(TstFunction):
    def test_query_by_provider_id_sanitizes_data_even_with_read_private_permission(self):
        self._load_provider_data()

        from handlers.providers import query_providers

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral aslp/readPrivate'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps({'query': {'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}})

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        with open('../common/tests/resources/api/provider-response.json') as f:
            expected_provider = json.load(f)

        body = json.loads(resp['body'])
        self.assertEqual(
            {
                'providers': [expected_provider],
                'pagination': {'pageSize': 100, 'lastKey': None, 'prevLastKey': None},
                'query': {'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'},
            },
            body,
        )

    def test_query_providers_updated_sorting(self):
        from handlers.providers import query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        self._generate_providers(home='ne', privilege_jurisdiction='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral aslp/readPrivate'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {'sorting': {'key': 'dateOfUpdate'}, 'query': {'jurisdiction': 'oh'}, 'pagination': {'pageSize': 10}},
        )

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(10, len(body['providers']))
        self.assertEqual({'providers', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertIsInstance(body['pagination']['lastKey'], str)
        # Check we're actually sorted
        dates_of_update = [provider['dateOfUpdate'] for provider in body['providers']]
        self.assertListEqual(sorted(dates_of_update), dates_of_update)

    def test_query_providers_family_name_sorting(self):
        from handlers.providers import query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        # We'll force the first 10 names, to be a set of values we know are challenging characters
        names = [
            ('山田', '1'),
            ('後藤', '2'),
            ('清水', '3'),
            ('近藤', '4'),
            ('Anderson', '5'),
            ('Bañuelos', '6'),
            ('de la Fuente', '7'),
            ('Dennis', '8'),
            ('Figueroa', '9'),
            ('Frías', '10'),
        ]
        self._generate_providers(home='ne', privilege_jurisdiction='oh', start_serial=9999, names=names)
        # We'll leave the last 10 names to be randomly generated to let the Faker data set come up with some
        # interesting values, to leave the door open to identify new edge cases.
        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {'sorting': {'key': 'familyName'}, 'query': {'jurisdiction': 'oh'}, 'pagination': {'pageSize': 10}},
        )

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(10, len(body['providers']))
        self.assertEqual({'providers', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertEqual({'key': 'familyName', 'direction': 'ascending'}, body['sorting'])
        self.assertIsInstance(body['pagination']['lastKey'], str)
        # Check we're actually sorted
        family_names = [provider['familyName'].lower() for provider in body['providers']]
        self.assertListEqual(sorted(family_names, key=quote), family_names)

    def test_query_providers_by_family_name(self):
        from handlers.providers import query_providers

        # 10 providers, licenses in oh, and privileges in ne, including a Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            privilege_jurisdiction='ne',
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {
                'sorting': {'key': 'familyName'},
                'query': {'jurisdiction': 'oh', 'familyName': 'Testerly'},
                'pagination': {'pageSize': 10},
            },
        )

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(2, len(body['providers']))

    def test_query_providers_given_name_only_not_allowed(self):
        from handlers.providers import query_providers

        # 10 providers, licenses in oh, and privileges in ne, including a Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            privilege_jurisdiction='ne',
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps(
            {
                'sorting': {'key': 'familyName'},
                'query': {'jurisdiction': 'oh', 'givenName': 'Tess'},
                'pagination': {'pageSize': 10},
            },
        )

        resp = query_providers(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_query_providers_default_sorting(self):
        """If sorting is not specified, familyName is default"""
        from handlers.providers import query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        self._generate_providers(home='ne', privilege_jurisdiction='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps({'query': {}})

        resp = query_providers(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(20, len(body['providers']))
        self.assertEqual({'providers', 'pagination', 'query', 'sorting'}, body.keys())
        self.assertEqual({'key': 'familyName', 'direction': 'ascending'}, body['sorting'])
        self.assertIsNone(body['pagination']['lastKey'])
        # Check we're actually sorted
        family_names = [provider['familyName'].lower() for provider in body['providers']]
        self.assertListEqual(sorted(family_names, key=quote), family_names)

    def test_query_providers_invalid_sorting(self):
        from handlers.providers import query_providers

        # 20 providers, 10 with licenses in oh, 10 with privileges in oh
        self._generate_providers(home='ne', privilege_jurisdiction='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege_jurisdiction='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps({'query': {'jurisdiction': 'oh'}, 'sorting': {'key': 'invalid'}})

        resp = query_providers(event, self.mock_context)

        # Should reject the query, with 400
        self.assertEqual(400, resp['statusCode'])

    def test_query_providers_strips_whitespace_from_query_fields(self):
        """Test that whitespace is stripped from multiple fields simultaneously."""
        from handlers.providers import query_providers

        # Create providers with known names for testing
        self._generate_providers(
            home='oh',
            privilege_jurisdiction='ne',
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral'
        event['pathParameters'] = {'compact': 'aslp'}

        # Test multiple fields with whitespace
        event['body'] = json.dumps(
            {
                'query': {
                    'givenName': '  Ted  ',
                    'familyName': '  Testerly  ',
                    'jurisdiction': '  oh  ',
                },
                'pagination': {'pageSize': 10},
            }
        )

        resp = query_providers(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        body = json.loads(resp['body'])
        self.assertEqual(1, len(body['providers']))  # Should find Ted Testerly
        found_provider = body['providers'][0]
        self.assertEqual('Ted', found_provider['givenName'])
        self.assertEqual('Testerly', found_provider['familyName'])


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestGetProvider(TstFunction):
    @staticmethod
    def _get_sensitive_hash():
        with open('../common/tests/resources/dynamo/license-update.json') as f:
            sk = json.load(f)['sk']
        # The actual sensitive part is the hash at the end of the key
        return sk.split('/')[-1]

    def _when_testing_get_provider_response_based_on_read_access(self, scopes: str, expected_provider: dict):
        self._load_provider_data()

        from handlers.providers import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = scopes
        event['pathParameters'] = {'compact': 'aslp', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])
        self.assertEqual(expected_provider, provider_data)

        # The sk for a license-update record is sensitive so we'll do an extra, pretty broad, check just to make sure
        # we guard against future changes that might accidentally send the key out via the API. See discussion on
        # key generation in the LicenseUpdateRecordSchema for details.
        sensitive_hash = self._get_sensitive_hash()
        self.assertNotIn(sensitive_hash, resp['body'])

    def _when_testing_get_provider_with_read_private_access(self, scopes: str):
        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)

        self._when_testing_get_provider_response_based_on_read_access(scopes, expected_provider)

    def test_get_provider_with_compact_level_read_private_access(self):
        self._when_testing_get_provider_with_read_private_access(
            scopes='openid email aslp/readGeneral aslp/readPrivate',
        )

    def test_get_provider_with_matching_license_jurisdiction_level_read_private_access(self):
        # test provider has a license in oh and a privilege in ne
        self._when_testing_get_provider_with_read_private_access(
            scopes='openid email aslp/readGeneral oh/aslp.readPrivate'
        )

    def test_get_provider_with_matching_privilege_jurisdiction_level_read_private_access(self):
        # test provider has a license in oh and a privilege in ne
        self._when_testing_get_provider_with_read_private_access(
            scopes='openid email aslp/readGeneral ne/aslp.readPrivate'
        )

    def test_get_provider_wrong_compact(self):
        """Provider detail response"""
        self._load_provider_data()

        from handlers.providers import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral'
        event['pathParameters'] = {'compact': 'octp', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = get_provider(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])

    def test_get_provider_missing_provider_id(self):
        from handlers.providers import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral'
        # providerId _should_ be included in these pathParameters. We're leaving it out for this test.
        event['pathParameters'] = {'compact': 'aslp'}
        event['queryStringParameters'] = None

        resp = get_provider(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_get_provider_returns_expected_general_response_when_caller_does_not_have_read_private_scope(self):
        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)
            expected_provider.pop('ssnLastFour')
            expected_provider.pop('dateOfBirth')

            # we do not return the military affiliation document keys if the caller does not have read private scope
            expected_provider['militaryAffiliations'][0].pop('documentKeys')
            del expected_provider['licenses'][0]['ssnLastFour']
            del expected_provider['licenses'][0]['dateOfBirth']
            del expected_provider['licenses'][0]['history'][0]['previous']['ssnLastFour']
            del expected_provider['licenses'][0]['history'][0]['previous']['dateOfBirth']

        self._when_testing_get_provider_response_based_on_read_access(
            scopes='openid email aslp/readGeneral', expected_provider=expected_provider
        )


@mock_aws
class TestGetProviderSSN(TstFunction):
    def _when_testing_rate_limiting(self, previous_attempt_count: int, provider_id: str):
        test_email = 'test@example.com'
        # create the test user and get their user id
        resp = self.config.cognito_client.admin_create_user(
            UserPoolId=self.config.user_pool_id,
            Username=test_email,
            UserAttributes=[
                {'Name': 'email', 'Value': test_email},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
        )
        user_id = resp['User']['Username']

        now_datetime = self.config.current_standard_datetime
        for attempt in range(previous_attempt_count):
            self.config.rate_limiting_table.put_item(
                Item={
                    'pk': 'READ_SSN_REQUESTS',
                    # separate each attempt by one minute
                    'sk': f'TIME#{(now_datetime - timedelta(minutes=attempt)).timestamp()}#REQUEST#{uuid.uuid4()}',
                    'compact': 'aslp',
                    'providerId': provider_id,
                    'staffUserId': user_id,
                }
            )

        return user_id

    def _make_ssn_request_with_unique_request_id(self, event: dict):
        from handlers.providers import get_provider_ssn

        self.mock_context.aws_request_id = uuid.uuid4()
        return get_provider_ssn(event, self.mock_context)

    def test_get_provider_ssn_returns_ssn_if_caller_has_read_ssn_compact_level_scope(self):
        self._load_provider_data()

        from handlers.providers import get_provider_ssn

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral aslp/readSSN'
        event['pathParameters'] = {'compact': 'aslp', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}

        resp = get_provider_ssn(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual({'ssn': '123-12-1234'}, json.loads(resp['body']))

    def test_get_provider_ssn_returns_ssn_if_caller_has_read_ssn_license_jurisdiction_scope(self):
        """
        The provider has a license in oh, and the caller has readSSN permission for oh.
        """
        self._load_provider_data()

        from handlers.providers import get_provider_ssn

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral oh/aslp.readSSN'
        event['pathParameters'] = {'compact': 'aslp', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}

        resp = get_provider_ssn(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual({'ssn': '123-12-1234'}, json.loads(resp['body']))

    def test_get_provider_ssn_returns_ssn_if_caller_has_read_ssn_privilege_jurisdiction_scope(self):
        """
        The provider has a privilege in ne, and the caller has readSSN permission for ne.
        """
        self._load_provider_data()

        from handlers.providers import get_provider_ssn

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral ne/aslp.readSSN'
        event['pathParameters'] = {'compact': 'aslp', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}

        resp = get_provider_ssn(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        self.assertEqual({'ssn': '123-12-1234'}, json.loads(resp['body']))

    def test_get_provider_ssn_forbidden_without_correct_jurisdiction_level_scope(self):
        """
        The provider has no license or privilege in ky, and the caller has readSSN permission for ky.
        """
        self._load_provider_data()

        from handlers.providers import get_provider_ssn

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email ky/aslp.readSSN'
        event['pathParameters'] = {'compact': 'aslp', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}

        resp = get_provider_ssn(event, self.mock_context)

        self.assertEqual(403, resp['statusCode'])

    def test_get_provider_ssn_throttled_and_deactivated_if_staff_user_goes_beyond_rate_limit(self):
        """
        The staff user has called this endpoint more than the set limit, so the endpoint throttles the user (which will
        cause an alert to trigger from CloudWatch) and, after one more request, their account is deactivated.
        """
        self._load_provider_data()

        test_provider_id = '89a6377e-c3a5-40e5-bca5-317ec854c570'
        # add 4 previous calls to the endpoint
        staff_user_id = self._when_testing_rate_limiting(previous_attempt_count=4, provider_id=test_provider_id)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['requestContext']['authorizer']['claims']['sub'] = staff_user_id

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral aslp/readSSN'
        event['pathParameters'] = {'compact': 'aslp', 'providerId': test_provider_id}

        # the fifth request should succeed, being right at the limit
        resp = self._make_ssn_request_with_unique_request_id(event)
        self.assertEqual(200, resp['statusCode'])
        # next request should be throttled, but should not deactivate their account
        resp = self._make_ssn_request_with_unique_request_id(event)
        self.assertEqual(429, resp['statusCode'])
        # assert that the user's account has not been deactivated yet.
        user = self.config.cognito_client.admin_get_user(UserPoolId=self.config.user_pool_id, Username=staff_user_id)
        self.assertEqual(user['Enabled'], True)

        # make another request to trigger deactivation
        resp = self._make_ssn_request_with_unique_request_id(event)
        self.assertEqual(429, resp['statusCode'])

        # assert that the user's account has been deactivated.
        user = self.config.cognito_client.admin_get_user(UserPoolId=self.config.user_pool_id, Username=staff_user_id)
        self.assertEqual(user['Enabled'], False)

    @patch('handlers.providers.config.lambda_client', autospec=True)
    def test_get_provider_ssn_endpoint_throttled_if_endpoint_calls_exceed_global_rate_limit(self, mock_lambda_client):
        """
        If this endpoint is invoked more than the set global limit within a 24-hour period, we throttle this endpoint
        by setting its reserved concurrency to 0, to prevent a concentrated attack.
        """
        self._load_provider_data()

        test_provider_id = '89a6377e-c3a5-40e5-bca5-317ec854c570'
        # add 15 previous calls to the endpoint
        staff_user_id = self._when_testing_rate_limiting(previous_attempt_count=15, provider_id=test_provider_id)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['requestContext']['authorizer']['claims']['sub'] = staff_user_id

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral aslp/readSSN'
        event['pathParameters'] = {'compact': 'aslp', 'providerId': test_provider_id}

        # request should be throttled
        self.mock_context.function_name = 'testLambdaName'
        resp = self._make_ssn_request_with_unique_request_id(event)
        self.assertEqual(429, resp['statusCode'])

        # assert that the lambda client was called with expected parameters
        mock_lambda_client.put_function_concurrency.assert_called_once_with(
            FunctionName='testLambdaName', ReservedConcurrentExecutions=0
        )
