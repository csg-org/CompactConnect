import json
from urllib.parse import quote

from moto import mock_aws

from .. import TstFunction


@mock_aws
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
        self._generate_providers(home='ne', privilege='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege='ne', start_serial=9899)

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
        self._generate_providers(home='ne', privilege='oh', start_serial=9999, names=names)
        # We'll leave the last 10 names to be randomly generated to let the Faker data set come up with some
        # interesting values, to leave the door open to identify new edge cases.
        self._generate_providers(home='oh', privilege='ne', start_serial=9899)

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
            privilege='ne',
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
            privilege='ne',
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
        self._generate_providers(home='ne', privilege='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege='ne', start_serial=9899)

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
        self._generate_providers(home='ne', privilege='oh', start_serial=9999)
        self._generate_providers(home='oh', privilege='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for aslp
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email aslp/readGeneral'
        event['pathParameters'] = {'compact': 'aslp'}
        event['body'] = json.dumps({'query': {'jurisdiction': 'oh'}, 'sorting': {'key': 'invalid'}})

        resp = query_providers(event, self.mock_context)

        # Should reject the query, with 400
        self.assertEqual(400, resp['statusCode'])


@mock_aws
class TestGetProvider(TstFunction):
    @staticmethod
    def _get_sensitive_hash():
        with open('../common/tests/resources/dynamo/license-update.json') as f:
            sk = json.load(f)['sk']
        # The actual sensitive part is the hash at the end of the key
        return sk.split('/')[-1]

    def _when_testing_get_provider_response_based_on_read_access(
        self, scopes: str, expected_provider: dict, delete_home_jurisdiction_selection: bool = False
    ):
        self._load_provider_data()
        if delete_home_jurisdiction_selection:
            # removing homeJurisdictionSelection to simulate a user that has not registered with the system
            self.config.provider_table.delete_item(
                Key={
                    'pk': 'aslp#PROVIDER#89a6377e-c3a5-40e5-bca5-317ec854c570',
                    'sk': 'aslp#PROVIDER#home-jurisdiction#',
                },
            )

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

    def test_get_provider_does_not_return_home_jurisdiction_selection_if_user_has_not_registered(self):
        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)
            del expected_provider['homeJurisdictionSelection']

        self._when_testing_get_provider_response_based_on_read_access(
            scopes='openid email aslp/readGeneral aslp/readPrivate',
            expected_provider=expected_provider,
            delete_home_jurisdiction_selection=True,
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
