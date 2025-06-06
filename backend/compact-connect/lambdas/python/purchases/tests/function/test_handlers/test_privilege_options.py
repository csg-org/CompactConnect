import json

from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'
TEST_PROVIDER_ID = 'some-provider-id'

MOCK_PUBLIC_CLIENT_KEY = 'some-public-client-key'
MOCK_API_LOGIN_ID = 'some-api-login-id'


@mock_aws
class TestGetPurchasePrivilegeOptions(TstFunction):
    def _when_testing_provider_user_event_with_custom_claims(self, test_compact=TEST_COMPACT):
        self.test_data_generator.put_default_compact_configuration_in_configuration_table(
            value_overrides={
                'paymentProcessorPublicFields': {
                    'publicClientKey': MOCK_PUBLIC_CLIENT_KEY,
                    'apiLoginId': MOCK_API_LOGIN_ID,
                }
            }
        )
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table()
        self._load_provider_data()
        with open('../common/tests/resources/api-event.json') as f:
            event = json.load(f)
            event['requestContext']['authorizer']['claims']['custom:providerId'] = TEST_PROVIDER_ID
            event['requestContext']['authorizer']['claims']['custom:compact'] = test_compact

        return event

    def test_get_purchase_privilege_options_returns_expected_jurisdiction_option(self):
        from handlers.privileges import get_purchase_privilege_options

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = get_purchase_privilege_options(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        privilege_options = json.loads(resp['body'])

        # the jurisdiction configuration is stored in the dynamo db as part of the
        # parent TstFunction setup, so we can compare the response directly
        jurisdiction_options = [option for option in privilege_options['items'] if option['type'] == 'jurisdiction']
        self.assertEqual(1, len(jurisdiction_options))
        jurisdiction_option = jurisdiction_options[0]
        self.assertEqual(
            {
                'compact': 'aslp',
                'jurisdictionName': 'Kentucky',
                'jurisprudenceRequirements': {
                    'linkToDocumentation': 'https://example.com/jurisprudence',
                    'required': True,
                },
                'postalAbbreviation': 'ky',
                'privilegeFees': [
                    {'amount': 50, 'licenseTypeAbbreviation': 'slp', 'militaryRate': 50},
                    {'amount': 50, 'licenseTypeAbbreviation': 'aud', 'militaryRate': 50},
                ],
                'type': 'jurisdiction',
            },
            jurisdiction_option,
        )

    def test_get_purchase_privilege_options_returns_expected_compact_option(self):
        from handlers.privileges import get_purchase_privilege_options

        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = get_purchase_privilege_options(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        privilege_options = json.loads(resp['body'])

        # the compact configuration is stored in the dynamo db as part of the
        # parent TstFunction setup, so we can compare the response directly
        compact_options = [option for option in privilege_options['items'] if option['type'] == 'compact']
        # there should only be one compact option for a given user, since the cognito user is tied to a compact
        self.assertEqual(1, len(compact_options))
        compact_option = compact_options[0]
        self.assertEqual(
            {
                'compactAbbr': 'aslp',
                'compactCommissionFee': {'feeAmount': 10, 'feeType': 'FLAT_RATE'},
                'compactName': 'Audiology and Speech Language Pathology',
                'isSandbox': True,
                'paymentProcessorPublicFields': {
                    'apiLoginId': 'some-api-login-id',
                    'publicClientKey': 'some-public-client-key',
                },
                'transactionFeeConfiguration': {
                    'licenseeCharges': {'active': True, 'chargeAmount': 10, 'chargeType': 'FLAT_FEE_PER_PRIVILEGE'}
                },
                'type': 'compact',
            },
            compact_option,
        )

    def test_get_purchase_privilege_options_returns_400_if_api_call_made_without_proper_claims(self):
        from handlers.privileges import get_purchase_privilege_options

        event = self._when_testing_provider_user_event_with_custom_claims()

        # remove custom attributes in the cognito claims
        del event['requestContext']['authorizer']['claims']['custom:providerId']
        del event['requestContext']['authorizer']['claims']['custom:compact']

        resp = get_purchase_privilege_options(event, self.mock_context)

        self.assertEqual(400, resp['statusCode'])

    def test_get_purchase_privilege_options_returns_empty_list_if_user_compact_do_not_match_any_option_in_db(self):
        from handlers.privileges import get_purchase_privilege_options

        event = self._when_testing_provider_user_event_with_custom_claims(test_compact='some-compact')

        resp = get_purchase_privilege_options(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        privilege_options = json.loads(resp['body'])

        self.assertEqual([], privilege_options['items'])
