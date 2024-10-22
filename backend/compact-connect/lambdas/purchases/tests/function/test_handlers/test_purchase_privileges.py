import json

from moto import mock_aws
from unittest.mock import patch, MagicMock

from tests.function import TstFunction

TEST_COMPACT = 'aslp'
# this value is defined in the provider.json file
TEST_PROVIDER_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'


def _generate_test_request_body():
    return  json.dumps({
        "selectedJurisdictions": ["oh"],
        "orderInformation": {
        "card": {
            "number": "<card number>",
            "expiration": "<expiration date>",
            "cvv": "<cvv>"
        },
        "billing":  {
            "firstName": "testFirstName",
            "lastName": "testLastName",
            "streetAddress": "123 Test St",
            "streetAddress2": "", # optional
            "state": "OH",
            "zip": "12345",
        }
      }
    }
    )


@mock_aws
class TestPostPurchasePrivileges(TstFunction):
    def _when_testing_provider_user_event_with_custom_claims(self, test_compact=TEST_COMPACT):
        self._load_compact_configuration_data()
        self._load_provider_data()
        with open('tests/resources/api-event.json') as f:
            event = json.load(f)
            event['requestContext']['authorizer']['claims']['custom:providerId'] = TEST_PROVIDER_ID
            event['requestContext']['authorizer']['claims']['custom:compact'] = test_compact

        return event

    def _when_purchase_client_successfully_processes_request(self, mock_purchase_client_constructor):
        mock_purchase_client = MagicMock()
        mock_purchase_client_constructor.return_value = mock_purchase_client
        mock_purchase_client.process_charge_for_licensee_privileges.return_value = {"transactionId": "1234"}

        return mock_purchase_client

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_calls_purchase_client_with_expected_parameters(self,
                                                                                     mock_purchase_client_constructor):
        from handlers.privileges import post_purchase_privileges
        mock_purchase_client = self._when_purchase_client_successfully_processes_request(
            mock_purchase_client_constructor)
        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])

        purchase_client_call_kwargs = mock_purchase_client.process_charge_for_licensee_privileges.call_args.kwargs

        self.assertEqual(json.loads(event['body'])['orderInformation'],
                         purchase_client_call_kwargs['order_information'])
        self.assertEqual(TEST_COMPACT, purchase_client_call_kwargs['compact_configuration'].compactName)
        self.assertEqual(["oh"], [jurisdiction.postalAbbreviation for jurisdiction
                                  in purchase_client_call_kwargs['selected_jurisdictions']])
        self.assertEqual(False, purchase_client_call_kwargs['user_active_military'])

    @patch('handlers.privileges.PurchaseClient')
    def test_post_purchase_privileges_returns_transaction_id(self, mock_purchase_client_constructor):
        from handlers.privileges import post_purchase_privileges
        self._when_purchase_client_successfully_processes_request(mock_purchase_client_constructor)

        event = self._when_testing_provider_user_event_with_custom_claims()
        event['body'] = _generate_test_request_body()

        resp = post_purchase_privileges(event, self.mock_context)
        self.assertEqual(200, resp['statusCode'])
        response_body = json.loads(resp['body'])

        self.assertEqual({"transactionId": "1234"}, response_body)

