import json

from cc_common.exceptions import CCInternalException
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
                'configuredStates': [
                    {'postalAbbreviation': 'ky', 'isLive': True}  # Make Kentucky live
                ],
                'paymentProcessorPublicFields': {
                    'publicClientKey': MOCK_PUBLIC_CLIENT_KEY,
                    'apiLoginId': MOCK_API_LOGIN_ID,
                },
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

        # Set up compact configuration with mixed live statuses
        self.test_data_generator.put_default_compact_configuration_in_configuration_table(
            value_overrides={
                'configuredStates': [
                    {'postalAbbreviation': 'ky', 'isLive': True},  # Live
                    {'postalAbbreviation': 'oh', 'isLive': False},  # Not live
                ],
                'paymentProcessorPublicFields': {
                    'publicClientKey': MOCK_PUBLIC_CLIENT_KEY,
                    'apiLoginId': MOCK_API_LOGIN_ID,
                },
            }
        )

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

    def test_get_purchase_privilege_options_filters_out_jurisdictions_with_licensee_registration_disabled(self):
        from handlers.privileges import get_purchase_privilege_options

        event = self._when_testing_provider_user_event_with_custom_claims()

        # Set up compact configuration. In this case, because ohio has not elected to go live, it does not show up
        # in the list of configured states
        self.test_data_generator.put_default_compact_configuration_in_configuration_table(
            value_overrides={
                'configuredStates': [
                    {'postalAbbreviation': 'ky', 'isLive': True}  # Make Kentucky live
                ],
                'paymentProcessorPublicFields': {
                    'publicClientKey': MOCK_PUBLIC_CLIENT_KEY,
                    'apiLoginId': MOCK_API_LOGIN_ID,
                },
            }
        )

        # Create jurisdiction with licenseeRegistrationEnabled = True
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'postalAbbreviation': 'ky',
                'jurisdictionName': 'Kentucky',
                'licenseeRegistrationEnabled': True,
            }
        )

        # Create jurisdiction with licenseeRegistrationEnabled = False
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'postalAbbreviation': 'oh',
                'jurisdictionName': 'Ohio',
                'licenseeRegistrationEnabled': False,
            }
        )

        self._load_provider_data()

        resp = get_purchase_privilege_options(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        privilege_options = json.loads(resp['body'])

        # ensure the compact and privilege were returned
        self.assertEqual(2, len(privilege_options['items']))

        # Filter to only jurisdiction options
        jurisdiction_options = [option for option in privilege_options['items'] if option['type'] == 'jurisdiction']

        # Should only return the jurisdiction with licenseeRegistrationEnabled = True
        self.assertEqual(1, len(jurisdiction_options))
        returned_jurisdiction = jurisdiction_options[0]
        self.assertEqual('ky', returned_jurisdiction['postalAbbreviation'])
        self.assertEqual('Kentucky', returned_jurisdiction['jurisdictionName'])

    def test_get_purchase_privilege_options_raises_exception_if_no_live_configured_states(self):
        """Test that jurisdictions not in configuredStates are filtered out."""
        from handlers.privileges import get_purchase_privilege_options

        event = self._when_testing_provider_user_event_with_custom_claims()

        # Set up compact configuration with empty configuredStates
        self.test_data_generator.put_default_compact_configuration_in_configuration_table(
            value_overrides={
                'configuredStates': [],  # Empty configuredStates
                'paymentProcessorPublicFields': {
                    'publicClientKey': MOCK_PUBLIC_CLIENT_KEY,
                    'apiLoginId': MOCK_API_LOGIN_ID,
                },
            }
        )

        # Create jurisdiction with licenseeRegistrationEnabled = True
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'postalAbbreviation': 'ky',
                'jurisdictionName': 'Kentucky',
                'licenseeRegistrationEnabled': True,
            }
        )

        with self.assertRaises(CCInternalException):
            get_purchase_privilege_options(event, self.mock_context)

    def test_get_purchase_privilege_options_includes_live_jurisdictions_in_configured_states(self):
        """Test that only jurisdictions with isLive=true are included."""
        from handlers.privileges import get_purchase_privilege_options

        event = self._when_testing_provider_user_event_with_custom_claims()

        # Set up compact configuration with mixed live statuses
        self.test_data_generator.put_default_compact_configuration_in_configuration_table(
            value_overrides={
                'configuredStates': [
                    {'postalAbbreviation': 'ky', 'isLive': True},  # Live
                    {'postalAbbreviation': 'oh', 'isLive': False},  # Not live
                ],
                'paymentProcessorPublicFields': {
                    'publicClientKey': MOCK_PUBLIC_CLIENT_KEY,
                    'apiLoginId': MOCK_API_LOGIN_ID,
                },
            }
        )

        # Create both jurisdictions with licenseeRegistrationEnabled = True
        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'postalAbbreviation': 'ky',
                'jurisdictionName': 'Kentucky',
                'licenseeRegistrationEnabled': True,
            }
        )

        self.test_data_generator.put_default_jurisdiction_configuration_in_configuration_table(
            value_overrides={
                'postalAbbreviation': 'oh',
                'jurisdictionName': 'Ohio',
                'licenseeRegistrationEnabled': True,
            }
        )

        resp = get_purchase_privilege_options(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        privilege_options = json.loads(resp['body'])

        # Should return compact option + 1 live jurisdiction
        self.assertEqual(2, len(privilege_options['items']))

        # Verify compact option and one jurisdiction option are returned
        compact_options = [option for option in privilege_options['items'] if option['type'] == 'compact']
        jurisdiction_options = [option for option in privilege_options['items'] if option['type'] == 'jurisdiction']

        self.assertEqual(1, len(compact_options))
        self.assertEqual(1, len(jurisdiction_options))

        # Verify only the live jurisdiction (Kentucky) is returned
        returned_jurisdiction = jurisdiction_options[0]
        self.assertEqual('ky', returned_jurisdiction['postalAbbreviation'])
        self.assertEqual('Kentucky', returned_jurisdiction['jurisdictionName'])
