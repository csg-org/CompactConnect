import json
from datetime import date, datetime
from unittest.mock import patch

from moto import mock_aws

from .. import TstFunction

# ProviderPublicResponseSchema + LicensePublicResponseSchema + PrivilegePublicResponseSchema
EXPECTED_PROVIDER_RESPONSE = {
    'type': 'provider',
    'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
    'dateOfUpdate': '2024-07-08T23:59:59+00:00',
    'compact': 'socw',
    'licenseJurisdiction': 'oh',
    'licenseStatus': 'active',
    'compactEligibility': 'eligible',
    'publicCompactIdentifier': 'SWC-1234-1',
    'givenName': 'Björk',
    'middleName': 'Gunnar',
    'familyName': 'Guðmundsdóttir',
    'licenses': [
        {
            'type': 'license',
            'compact': 'socw',
            'jurisdiction': 'oh',
            'licenseType': 'licensed clinical social worker',
            'licenseScope': 'multi-state',
            'licenseStatus': 'active',
            'compactEligibility': 'eligible',
            'dateOfExpiration': '2025-04-04',
            'licenseNumber': 'B0608337260',
            'adverseActions': [],
            # Canned multi-state license has no firstUploadDate and no update records.
            'history': [],
        }
    ],
    'privileges': [
        {
            'type': 'privilege',
            'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570',
            'compact': 'socw',
            'jurisdiction': 'ne',
            'licenseJurisdiction': 'oh',
            'licenseType': 'licensed clinical social worker',
            'dateOfExpiration': '2025-04-04',
            'adverseActions': [],
            'administratorSetStatus': 'active',
            'status': 'active',
            'history': [],
        }
    ],
}


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-11-08T23:59:59+00:00'))
class TestPublicGetProvider(TstFunction):
    def setUp(self):
        super().setUp()
        self.set_live_compact_jurisdictions_for_test({'socw': ['ne']})

    def test_public_get_provider_response_with_expected_fields_filtered(self):
        self._load_provider_data()

        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'socw', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        self.assertEqual(EXPECTED_PROVIDER_RESPONSE, provider_data)

    def test_public_get_provider_response_includes_adverse_actions_without_categories(self):
        self._load_provider_data()
        # a privilege adverse action, using the default jurisdiction/license type that match the default privilege
        privilege_adverse_action = self.test_data_generator.put_default_adverse_action_record_in_provider_table()
        # a license adverse action, matching the default multi-state license
        license_adverse_action = self.test_data_generator.put_default_adverse_action_record_in_provider_table(
            value_overrides={
                'actionAgainst': 'license',
                'jurisdiction': 'oh',
                'licenseScope': 'multi-state',
                'adverseActionId': '11111111-1111-1111-1111-111111111111',
            }
        )

        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'socw', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        privilege_public_adverse_actions = provider_data['privileges'][0]['adverseActions']
        license_public_adverse_actions = provider_data['licenses'][0]['adverseActions']

        self.assertEqual(1, len(privilege_public_adverse_actions))
        self.assertEqual(1, len(license_public_adverse_actions))

        for adverse_action, expected_adverse_action_id in (
            (privilege_public_adverse_actions[0], str(privilege_adverse_action.adverseActionId)),
            (license_public_adverse_actions[0], str(license_adverse_action.adverseActionId)),
        ):
            self.assertEqual(expected_adverse_action_id, adverse_action['adverseActionId'])
            # NPDB categories and other staff-only fields must not be exposed publicly
            self.assertNotIn('clinicalPrivilegeActionCategories', adverse_action)
            self.assertNotIn('encumbranceType', adverse_action)
            self.assertNotIn('submittingUser', adverse_action)
            self.assertNotIn('liftingUser', adverse_action)

    def test_public_get_provider_response_only_returns_most_recent_licenses(self):
        self._load_provider_data()
        # adding another license for same license type from another state, with an older issuance and renewal date
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'dateOfIssuance': date(2019, 1, 1),
                'dateOfRenewal': date(2020, 1, 1),
                'licenseNumber': 'olderCosmLicense',
                'jurisdiction': 'az',
            }
        )

        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'socw', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        # the older license should not be included in the response
        self.assertEqual(EXPECTED_PROVIDER_RESPONSE, provider_data)

    def test_public_get_provider_response_returns_multiple_license_types(self):
        self._load_provider_data()
        # adding another license for same license type from another state, with an older issuance and renewal date
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'dateOfIssuance': date(2019, 1, 1),
                'dateOfRenewal': date(2020, 1, 1),
                'licenseNumber': 'olderCosmLicense',
                'jurisdiction': 'az',
            }
        )

        # add two more licenses for another license type
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'licenseType': 'licensed master social worker',
                'dateOfIssuance': date(2019, 1, 1),
                'dateOfRenewal': date(2020, 1, 1),
                'licenseNumber': 'olderEstLicense',
                'jurisdiction': 'az',
            }
        )
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'licenseType': 'licensed master social worker',
                'dateOfIssuance': date(2024, 1, 1),
                'dateOfRenewal': date(2025, 1, 1),
                'jurisdiction': 'oh',
                'licenseNumber': 'mostRecentEstLicense',
                'dateOfExpiration': date(2026, 1, 1),
            }
        )

        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'socw', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        # the older license should not be included in the response
        expected_licenses = [
            {
                'type': 'license',
                'compact': 'socw',
                'jurisdiction': 'oh',
                'licenseType': 'licensed clinical social worker',
                'licenseScope': 'multi-state',
                'licenseStatus': 'active',
                'compactEligibility': 'eligible',
                'dateOfExpiration': '2025-04-04',
                'licenseNumber': 'B0608337260',
                'adverseActions': [],
                'history': [],
            }
        ]
        self.assertEqual(expected_licenses, provider_data['licenses'])

    def test_public_get_provider_prefers_multi_state_when_single_state_is_newer(self):
        self._load_provider_data()
        self.test_data_generator.put_default_license_record_in_provider_table(
            value_overrides={
                'licenseScope': 'single-state',
                'licenseNumber': 'A0608337260',
                'dateOfIssuance': date(2024, 1, 1),
                'dateOfRenewal': date(2026, 1, 1),
                'dateOfExpiration': date(2030, 1, 1),
            }
        )

        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'socw', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        provider_data = json.loads(resp['body'])

        self.assertEqual(EXPECTED_PROVIDER_RESPONSE, provider_data)

    def test_public_get_provider_missing_provider_id(self):
        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        # public endpoint does not have authorizer
        del event['requestContext']['authorizer']
        # providerId _should_ be included in these pathParameters. We're leaving it out for this test.
        event['pathParameters'] = {'compact': 'socw'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_public_get_provider_returns_404_when_provider_has_only_single_state_licenses(self):
        from decimal import Decimal

        import boto3

        with open('../common/tests/resources/dynamo/provider.json') as f:
            provider_record = json.load(f, parse_float=Decimal)
        with open('../common/tests/resources/dynamo/license.json') as f:
            single_state_license = json.load(f, parse_float=Decimal)

        provider_table = boto3.resource('dynamodb').Table(self.config.provider_table_name)
        provider_table.put_item(Item=provider_record)
        provider_table.put_item(Item=single_state_license)

        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'socw', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)

        self.assertEqual(404, resp['statusCode'])

    def _public_provider(self):
        from handlers.public_lookup import public_get_provider

        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)

        del event['requestContext']['authorizer']
        event['pathParameters'] = {'compact': 'socw', 'providerId': '89a6377e-c3a5-40e5-bca5-317ec854c570'}
        event['queryStringParameters'] = None

        resp = public_get_provider(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        return json.loads(resp['body'])

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

    def _assert_no_staff_encumbrance_fields(self, history):
        for event in history:
            self.assertNotIn('npdbCategories', event)
            self.assertNotIn('encumbranceType', event)

    def test_public_get_provider_response_includes_full_license_history(self):
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

        provider_data = self._public_provider()
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
        self.assertEqual('2021-03-15T00:00:00+00:00', history[0]['effectiveDate'])
        self.assertEqual('2021-03-15T00:00:00+00:00', history[0]['createDate'])
        self.assertEqual('az', history[1]['previousHomeJurisdiction'])
        self.assertEqual('oh', history[1]['newHomeJurisdiction'])
        self.assertEqual('2022-09-10', history[2]['effectiveDate'])
        self.assertEqual('2023-01-05', history[3]['effectiveDate'])
        self.assertEqual('2023-03-15T00:00:00+00:00', history[4]['effectiveDate'])
        self._assert_no_staff_encumbrance_fields(history)

        for license_record in provider_data['licenses']:
            if license_record['licenseScope'] == 'single-state':
                update_types = [event['updateType'] for event in license_record['history']]
                self.assertNotIn('homeJurisdictionChange', update_types)

    def test_public_get_provider_response_includes_full_privilege_history(self):
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

        provider_data = self._public_provider()
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
        self.assertEqual('2021-03-15T00:00:00+00:00', history[0]['effectiveDate'])
        self.assertEqual('2021-03-15T00:00:00+00:00', history[0]['createDate'])
        self.assertEqual('az', history[1]['previousHomeJurisdiction'])
        self.assertEqual('oh', history[1]['newHomeJurisdiction'])
        self.assertEqual('2023-05-20', history[2]['effectiveDate'])
        self.assertEqual('2024-01-01', history[3]['effectiveDate'])
        self._assert_no_staff_encumbrance_fields(history)
