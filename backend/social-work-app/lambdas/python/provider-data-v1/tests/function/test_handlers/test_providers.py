import json
from datetime import date, datetime
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

        # The user has read permission for cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral socw/readPrivate'
        event['pathParameters'] = {'compact': 'socw'}
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

        # 20 providers with licenses in oh (two batches)
        self._generate_providers(home='oh', start_serial=9999)
        self._generate_providers(home='oh', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral socw/readPrivate'
        event['pathParameters'] = {'compact': 'socw'}
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

        # 20 providers with licenses in oh (two batches); first 10 have challenging name characters
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
        self._generate_providers(home='oh', start_serial=9999, names=names)
        self._generate_providers(home='oh', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral'
        event['pathParameters'] = {'compact': 'socw'}
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

        # 10 providers with licenses in oh, including Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral'
        event['pathParameters'] = {'compact': 'socw'}
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

        # 10 providers with licenses in oh, including Tess and Ted Testerly
        self._generate_providers(
            home='oh',
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral'
        event['pathParameters'] = {'compact': 'socw'}
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

        # 20 providers with licenses (10 in oh, 10 in ne)
        self._generate_providers(home='oh', start_serial=9999)
        self._generate_providers(home='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral'
        event['pathParameters'] = {'compact': 'socw'}
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

        # 20 providers with licenses (10 in oh, 10 in ne)
        self._generate_providers(home='oh', start_serial=9999)
        self._generate_providers(home='ne', start_serial=9899)

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral'
        event['pathParameters'] = {'compact': 'socw'}
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
            start_serial=9999,
            names=(('Testerly', 'Tess'), ('Testerly', 'Ted')),
        )

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral'
        event['pathParameters'] = {'compact': 'socw'}

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
    def setUp(self):
        super().setUp()
        self.set_live_compact_jurisdictions_for_test({'socw': ['ne']})

    @staticmethod
    def _get_sensitive_hash():
        with open('../common/tests/resources/dynamo/license-update.json') as f:
            sk = json.load(f)['sk']
        # The actual sensitive part is the hash at the end of the key
        return sk.split('/')[-1]

    def _call_get_provider_and_return_provider_data(self, scopes: str):
        from handlers.providers import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for cosm
        event['requestContext']['authorizer']['claims']['scope'] = scopes
        event['pathParameters'] = {'compact': 'socw', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])
        # The sk for a license-update record is sensitive so we'll do an extra, pretty broad, check just to make sure
        # we guard against future changes that might accidentally send the key out via the API. See discussion on
        # key generation in the LicenseUpdateRecordSchema for details.
        sensitive_hash = self._get_sensitive_hash()
        self.assertNotIn(sensitive_hash, resp['body'])

        return provider_data

    def _when_testing_get_provider_response_based_on_read_access(self, scopes: str, expected_provider: dict):
        self._load_provider_data()

        provider_data = self._call_get_provider_and_return_provider_data(scopes)
        self.assertEqual(expected_provider, provider_data)

    def _when_testing_get_provider_with_read_private_access(self, scopes: str):
        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)
        self._expect_canned_provider_history(expected_provider)

        self._when_testing_get_provider_response_based_on_read_access(scopes, expected_provider)

    def _expect_canned_provider_history(self, provider: dict) -> None:
        """History produced from the canned dynamo fixtures, which have no firstUploadDate.

        license-update.json is a renewal of the single-state license. The multi-state license and the
        privilege have no history events.
        """
        canned_renewal = {
            'updateType': 'renewal',
            'effectiveDate': '2024-11-08T23:59:59+00:00',
            'createDate': '2024-11-08T23:59:59+00:00',
        }
        for license_record in provider['licenses']:
            if license_record['licenseScope'] == 'single-state':
                license_record['history'] = [canned_renewal]
            else:
                license_record['history'] = []
        for privilege in provider['privileges']:
            privilege['history'] = []

    def test_get_provider_with_compact_level_read_private_access(self):
        self._when_testing_get_provider_with_read_private_access(
            scopes='openid email socw/readGeneral socw/readPrivate',
        )

    def test_get_provider_with_matching_license_jurisdiction_level_read_private_access(self):
        # test provider has a license in oh
        self._when_testing_get_provider_with_read_private_access(
            scopes='openid email socw/readGeneral oh/socw.readPrivate'
        )

    def test_get_provider_missing_provider_id(self):
        from handlers.providers import get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # The user has read permission for cosm
        event['requestContext']['authorizer']['claims']['scope'] = 'openid email socw/readGeneral'
        # providerId _should_ be included in these pathParameters. We're leaving it out for this test.
        event['pathParameters'] = {'compact': 'socw'}
        event['queryStringParameters'] = None

        resp = get_provider(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_get_provider_returns_expected_general_response_when_caller_does_not_have_read_private_scope(self):
        with open('../common/tests/resources/api/provider-detail-response.json') as f:
            expected_provider = json.load(f)
            expected_provider.pop('ssnLastFour')
            expected_provider.pop('dateOfBirth')

            for license_record in expected_provider['licenses']:
                license_record.pop('ssnLastFour', None)
                license_record.pop('dateOfBirth', None)
            self._expect_canned_provider_history(expected_provider)

        self._when_testing_get_provider_response_based_on_read_access(
            scopes='openid email socw/readGeneral', expected_provider=expected_provider
        )

    def _stamp_multi_state_first_upload_date(self):
        key = {
            'pk': 'socw#PROVIDER#89a6377e-c3a5-40e5-bca5-317ec854c570',
            'sk': 'socw#PROVIDER#license/oh/lcsw/multi-state#',
        }
        item = self._provider_table.get_item(Key=key)['Item']
        item['firstUploadDate'] = '2021-03-15T00:00:00+00:00'
        self._provider_table.put_item(Item=item)

    def _seed_home_jurisdiction_change(self):
        previous = self.test_data_generator.generate_default_provider({'licenseJurisdiction': 'az'})
        self.test_data_generator.put_default_provider_update_record_in_provider_table(
            {
                'updateType': 'homeJurisdictionChange',
                'createDate': datetime.fromisoformat('2022-06-01T14:32:00+00:00'),
                'previous': previous.to_dict(),
                'updatedValues': {'licenseJurisdiction': 'oh'},
            }
        )

    def _seed_multi_state_renewal(self):
        self.test_data_generator.put_default_license_update_record_in_provider_table(
            {
                'updateType': 'renewal',
                'licenseScope': 'multi-state',
                'jurisdiction': 'oh',
                'licenseType': 'licensed clinical social worker',
                'effectiveDate': datetime.fromisoformat('2023-03-15T00:00:00+00:00'),
                'createDate': datetime.fromisoformat('2023-03-15T00:00:00+00:00'),
            }
        )

    def _seed_encumbrance(self, *, action_against, jurisdiction, license_scope, start, recorded_at, lift_on, action_id):
        self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            {
                'actionAgainst': action_against,
                'jurisdiction': jurisdiction,
                'licenseScope': license_scope,
                'licenseType': 'licensed clinical social worker',
                'licenseTypeAbbreviation': 'lcsw',
                'effectiveStartDate': start,
                'effectiveLiftDate': lift_on,
                'creationDate': recorded_at,
                'encumbranceType': 'required supervision',
                'clinicalPrivilegeActionCategories': [
                    'Substandard Care or Patient Neglect/Abuse',
                    'Fraud, Deception, or Misrepresentation',
                ],
                'adverseActionId': action_id,
            }
        )

    def test_staff_get_provider_response_includes_full_license_history(self):
        self._load_provider_data()
        self._stamp_multi_state_first_upload_date()
        self._seed_multi_state_renewal()
        self._seed_encumbrance(
            action_against='license',
            jurisdiction='oh',
            license_scope='multi-state',
            start=date(2022, 9, 10),
            recorded_at=datetime.fromisoformat('2022-09-10T18:45:00+00:00'),
            lift_on=date(2023, 1, 5),
            action_id='11111111-1111-1111-1111-111111111111',
        )
        self._seed_home_jurisdiction_change()

        provider_data = self._call_get_provider_and_return_provider_data('openid email socw/readGeneral')
        multi_state = next(
            license_record
            for license_record in provider_data['licenses']
            if license_record['licenseScope'] == 'multi-state'
        )
        history = multi_state['history']
        self.assertEqual(
            ['issuance', 'homeJurisdictionChange', 'encumbrance', 'liftingEncumbrance', 'renewal'],
            [event['updateType'] for event in history],
        )
        encumbrance = next(event for event in history if event['updateType'] == 'encumbrance')
        self.assertEqual('required supervision', encumbrance['encumbranceType'])
        self.assertEqual(
            ['Substandard Care or Patient Neglect/Abuse', 'Fraud, Deception, or Misrepresentation'],
            encumbrance['npdbCategories'],
        )
        single_state = next(
            license_record
            for license_record in provider_data['licenses']
            if license_record['licenseScope'] == 'single-state'
        )
        self.assertNotIn(
            'homeJurisdictionChange',
            [event['updateType'] for event in single_state['history']],
        )

    def test_staff_get_provider_response_includes_full_privilege_history(self):
        self._load_provider_data()
        self._stamp_multi_state_first_upload_date()
        self._seed_encumbrance(
            action_against='privilege',
            jurisdiction='ne',
            license_scope='single-state',
            start=date(2023, 5, 20),
            recorded_at=datetime.fromisoformat('2023-05-20T11:00:00+00:00'),
            lift_on=date(2024, 1, 1),
            action_id='22222222-2222-2222-2222-222222222222',
        )
        self._seed_home_jurisdiction_change()

        provider_data = self._call_get_provider_and_return_provider_data('openid email socw/readGeneral')
        privilege = next(
            privilege_record
            for privilege_record in provider_data['privileges']
            if privilege_record['jurisdiction'] == 'ne'
        )
        history = privilege['history']
        self.assertEqual(
            ['issuance', 'homeJurisdictionChange', 'encumbrance', 'liftingEncumbrance'],
            [event['updateType'] for event in history],
        )
        encumbrance = next(event for event in history if event['updateType'] == 'encumbrance')
        self.assertEqual('required supervision', encumbrance['encumbranceType'])
        self.assertEqual(
            ['Substandard Care or Patient Neglect/Abuse', 'Fraud, Deception, or Misrepresentation'],
            encumbrance['npdbCategories'],
        )
        self.assertEqual('az', history[1]['previousHomeJurisdiction'])
        self.assertEqual('oh', history[1]['newHomeJurisdiction'])
