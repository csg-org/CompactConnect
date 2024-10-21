# ruff: noqa: ARG001 unused-argument
import json

from unittest.mock import MagicMock, patch
from tests import TstLambdas


EXPECTED_ASLP_SECRET_ID = "/compact-connect/env/test/compact/aslp/credentials/payment-processor"
MOCK_LOGIN_ID = "mock_login_id"
MOCK_TRANSACTION_KEY = "R2d237rZu59q123"
MOCK_ASLP_SECRET = {
    "processor": "authorize.net",
    "api_login_id": MOCK_LOGIN_ID,
    "transaction_key": MOCK_TRANSACTION_KEY
}


def json_to_magic_mock(json_obj):
    """
    Create a MagicMock object from a JSON object. This is useful for mocking the authorize.net SDK response object.

    Unfortunately, the authorize.net SDK response object uses attributes for all the values, which are not easily
    mocked. We create MagicMock objects that have the necessary attributes for each nested object
    """
    if isinstance(json_obj, dict):
        mock = MagicMock()
        for key, value in json_obj.items():
            setattr(mock, key, json_to_magic_mock(value))
        return mock
    elif isinstance(json_obj, list):
        return [json_to_magic_mock(item) for item in json_obj]
    else:
        return json_obj


class TestApiHandler(TstLambdas):
    """Testing that the api_handler decorator is working as expected."""

    def _generate_mock_secrets_manager_client(self):
        def get_secret_value_side_effect(SecretId):
            if SecretId == EXPECTED_ASLP_SECRET_ID:
                return {
                    'SecretString': json.dumps(MOCK_ASLP_SECRET)
                }
            else:
                raise ValueError(f"Unknown SecretId: {SecretId}")
        mock_secrets_manager_client = MagicMock()
        mock_secrets_manager_client.get_secret_value.side_effect = get_secret_value_side_effect

        return mock_secrets_manager_client


    def _set_default_behavior_for_create_transaction_controller(self, mock_create_transaction_controller,
                                                                success_message=True):

        mock_response = json_to_magic_mock({
        "messages": {
            "resultCode": "Ok" if success_message else "Error",
        },
        "transactionResponse": {
            "transId": "123456",
            "responseCode": "1",
            "messages": {
                "message": [
                    {
                        "code": "I00001",
                        "description": "Successful."
                    }
                ]
            }
        }
        })
        mock_transaction_controller = MagicMock()
        mock_transaction_controller.getresponse.return_value = mock_response

        mock_create_transaction_controller.return_value = mock_transaction_controller
        return mock_transaction_controller

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_makes_transaction_using_authorize_net_processor(self, mock_create_transaction_controller):
        from purchase_client import PurchaseClient
        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        mock_transaction_controller = self._set_default_behavior_for_create_transaction_controller(
            mock_create_transaction_controller=mock_create_transaction_controller,
            success_message=True)

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        test_purchase_client.process_charge_for_licensee_privileges('aslp',
                                                                    {
                                                                        'order': 'information',
                                                                        'amount': 100.00,
                                                                        'card': {
                                                                            'number': "4111111111111112",
                                                                            'expiration': "2035-10",
                                                                            'code': "125"
                                                                        },
                                                                        'billing': {
                                                                            'first_name': "testFirstName",
                                                                            'last_name': "testLastName",
                                                                            'address': "123 Test St",
                                                                            'state': "OH",
                                                                            'zip': "12345",
                                                                        }
                                                                    })

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj  = call_args[0]
        # we check every line of the object to ensure that the correct values are being passed to the authorize.net SDK
        self.assertEqual("authCaptureTransaction", api_contract_v1_obj.transactionRequest.transactionType)
        # authentication fields
        self.assertEqual(MOCK_LOGIN_ID, api_contract_v1_obj.merchantAuthentication.name)
        self.assertEqual(MOCK_TRANSACTION_KEY, api_contract_v1_obj.merchantAuthentication.transactionKey)
        # credit card payment fields
        self.assertEqual("4111111111111112", api_contract_v1_obj.transactionRequest.payment.creditCard.cardNumber)
        self.assertEqual("2035-10", api_contract_v1_obj.transactionRequest.payment.creditCard.expirationDate)
        self.assertEqual("125", api_contract_v1_obj.transactionRequest.payment.creditCard.cardCode)
        # transaction billing fields
        self.assertEqual(100.00, api_contract_v1_obj.transactionRequest.amount)
        self.assertEqual("USD", api_contract_v1_obj.transactionRequest.currencyCode)
        self.assertEqual("OH", api_contract_v1_obj.transactionRequest.billTo.state)
        self.assertEqual("12345", api_contract_v1_obj.transactionRequest.billTo.zip)
        self.assertEqual("123 Test St", api_contract_v1_obj.transactionRequest.billTo.address)
        self.assertEqual("testFirstName", api_contract_v1_obj.transactionRequest.billTo.firstName)
        self.assertEqual("testLastName", api_contract_v1_obj.transactionRequest.billTo.lastName)
        # transaction settings
        self.assertEqual("180", api_contract_v1_obj.transactionRequest.transactionSettings.setting[0].settingValue)
        self.assertEqual("duplicateWindow",
                         api_contract_v1_obj.transactionRequest.transactionSettings.setting[0].settingName)





