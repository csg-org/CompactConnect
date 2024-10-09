import json

from moto import mock_aws
from tests.function import TstFunction

TEST_COMPACT = "aslp"
TEST_PROVIDER_ID = "some-provider-id"
@mock_aws
class TestGetPurchasePrivilegeOptions(TstFunction):

    def _when_testing_provider_user_event_with_custom_claims(self, test_compact=TEST_COMPACT):
        self._load_compact_configuration_data()
        with open('tests/resources/api-event.json', 'r') as f:
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

        with open('tests/resources/dynamo/jurisdiction.json', 'r') as f:
            expected_jurisdiction_option = json.load(f)
            expected_jurisdiction_option.pop('pk')
            expected_jurisdiction_option.pop('sk')
            # we should not be returning email information in the response
            expected_jurisdiction_option.pop('jurisdictionOperationsTeamEmails')
            expected_jurisdiction_option.pop('jurisdictionAdverseActionsNotificationEmails')
            expected_jurisdiction_option.pop('jurisdictionSummaryReportNotificationEmails')
            # remove date fields as they are not needed in the response
            expected_jurisdiction_option.pop('dateOfUpdate')


        # the jurisdiction configuration is stored in the dynamo db as part of the
        # parent TstFunction setup, so we can compare the response directly
        jurisdiction_option = [option for option in privilege_options['items'] if option['type'] == 'jurisdiction'][0]
        self.assertEqual(expected_jurisdiction_option, jurisdiction_option)


    def test_get_purchase_privilege_options_returns_expected_compact_option(self):
        from handlers.privileges import get_purchase_privilege_options
        event = self._when_testing_provider_user_event_with_custom_claims()

        resp = get_purchase_privilege_options(event, self.mock_context)

        self.assertEqual(200, resp['statusCode'])
        privilege_options = json.loads(resp['body'])

        with open('tests/resources/dynamo/compact.json', 'r') as f:
            expected_compact_option = json.load(f)
            expected_compact_option.pop('pk')
            expected_compact_option.pop('sk')
            # we should not be returning email information in the response
            expected_compact_option.pop('compactOperationsTeamEmails')
            expected_compact_option.pop('compactAdverseActionsNotificationEmails')
            expected_compact_option.pop('compactSummaryReportNotificationEmails')
            # remove date fields as they are not needed in the response
            expected_compact_option.pop('dateOfUpdate')

        # the compact configuration is stored in the dynamo db as part of the
        # parent TstFunction setup, so we can compare the response directly
        compact_option = [option for option in privilege_options['items'] if option['type'] == 'compact'][0]
        self.assertEqual(expected_compact_option, compact_option)


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
