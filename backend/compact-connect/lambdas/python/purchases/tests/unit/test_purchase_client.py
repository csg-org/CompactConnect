# ruff: noqa: ARG001 unused-argument
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

from cc_common.config import config
from cc_common.exceptions import CCFailedTransactionException, CCInternalException, CCInvalidRequestException

from tests import TstLambdas

MOCK_LOGIN_ID = 'mock_login_id'
MOCK_TRANSACTION_KEY = 'R2d237rZu59q123'
MOCK_ASLP_SECRET = {
    'processor': 'authorize.net',
    'api_login_id': MOCK_LOGIN_ID,
    'transaction_key': MOCK_TRANSACTION_KEY,
}

MOCK_TRANSACTION_ID = '123456'

MOCK_LICENSEE_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'

EXPECTED_TOTAL_FEE_AMOUNT = 150.50


def json_to_magic_mock(json_obj):
    """
    Create a MagicMock object from a JSON object. This is useful for mocking the authorize.net SDK response object.

    Unfortunately, the authorize.net SDK response object uses attributes for all the values, which are not easily
    mocked. We create MagicMock objects that have the necessary attributes for each nested object
    """
    if isinstance(json_obj, dict):
        # set to the spec of the object so that extra attributes do not return True for hasattr
        mock = MagicMock(spec=json_obj)
        for key, value in json_obj.items():
            setattr(mock, key, json_to_magic_mock(value))
        return mock
    if isinstance(json_obj, list):
        return [json_to_magic_mock(item) for item in json_obj]
    return json_obj


def _generate_default_order_information():
    return {
        'card': {'number': '4111111111111112', 'expiration': '2035-10', 'cvv': '125'},
        'billing': {
            'firstName': 'testFirstName',
            'lastName': 'testLastName',
            'streetAddress': '123 Test St',
            'state': 'OH',
            'zip': '12345',
        },
    }


def _generate_aslp_compact_configuration():
    from cc_common.data_model.schema.compact import Compact

    with open('../common/tests/resources/dynamo/compact.json') as f:
        # setting fixed fee amount for tests
        compact = json.load(f)
        # DynamoDB loads this as a Decimal
        compact['compactCommissionFee']['feeAmount'] = Decimal(50.50)

        return Compact(compact)


def _generate_selected_jurisdictions():
    from cc_common.data_model.schema.jurisdiction import Jurisdiction

    with open('../common/tests/resources/dynamo/jurisdiction.json') as f:
        jurisdiction = json.load(f)
        jurisdiction['jurisdictionFee'] = Decimal(100.00)
        # set military discount to fixed amount for tests
        jurisdiction['militaryDiscount']['discountAmount'] = Decimal(25.00)
        jurisdiction['militaryDiscount']['active'] = True
        jurisdiction['militaryDiscount']['discountType'] = 'FLAT_RATE'

        return [Jurisdiction(jurisdiction)]


class TestAuthorizeDotNetPurchaseClient(TstLambdas):
    """Testing that the purchase client works with authorize.net SDK as expected."""

    def _generate_mock_secrets_manager_client(self):
        mock_secrets_manager_client = MagicMock()
        mock_secrets_manager_client.exceptions.ResourceNotFoundException = (
            config.secrets_manager_client.exceptions.ResourceNotFoundException
        )

        def get_secret_value_side_effect(SecretId):  # noqa: N803 invalid-name required for mock
            if SecretId == 'compact-connect/env/test/compact/aslp/credentials/payment-processor':
                return {'SecretString': json.dumps(MOCK_ASLP_SECRET)}
            raise config.secrets_manager_client.exceptions.ResourceNotFoundException(
                {'Error': {'Code': 'ResourceNotFoundException'}},
                operation_name='get_secret_value',
            )

        def describe_secret_side_effect(SecretId):  # noqa: N803 invalid-name required for mock
            if SecretId == 'compact-connect/env/test/compact/aslp/credentials/payment-processor':
                # add other fields here if needed
                return {'Name': 'compact-connect/env/test/compact/aslp/credentials/payment-processor'}
            raise config.secrets_manager_client.exceptions.ResourceNotFoundException(
                {'Error': {'Code': 'ResourceNotFoundException'}},
                operation_name='describe_secret',
            )

        mock_secrets_manager_client.get_secret_value.side_effect = get_secret_value_side_effect
        mock_secrets_manager_client.describe_secret.side_effect = describe_secret_side_effect

        return mock_secrets_manager_client

    def _setup_mock_transaction_controller(self, mock_create_transaction_controller, response_body: dict):
        mock_response = json_to_magic_mock(response_body)
        mock_transaction_controller = MagicMock()
        mock_transaction_controller.getresponse.return_value = mock_response

        mock_create_transaction_controller.return_value = mock_transaction_controller
        return mock_transaction_controller

    def _when_authorize_dot_net_transaction_is_successful(self, mock_create_transaction_controller):
        mock_success_response = {
            'messages': {
                'resultCode': 'Ok',
            },
            'transactionResponse': {
                'transId': MOCK_TRANSACTION_ID,
                'responseCode': '1',
                'messages': {'message': [{'code': 'I00001', 'description': 'Successful.'}]},
            },
        }

        return self._setup_mock_transaction_controller(mock_create_transaction_controller, mock_success_response)

    def _when_authorize_dot_net_transaction_fails(self, mock_create_transaction_controller):
        mock_response = {
            'messages': {'resultCode': 'Ok'},
            'transactionResponse': {
                'transId': MOCK_TRANSACTION_ID,
                'responseCode': '1',
                'errors': {'error': [{'errorCode': 'E00001', 'errorText': 'Insufficient funds.'}]},
            },
        }
        return self._setup_mock_transaction_controller(mock_create_transaction_controller, mock_response)

    def _when_authorize_dot_net_api_call_fails(self, mock_create_transaction_controller):
        mock_response = {
            'messages': {
                'resultCode': 'Error',
                'message': [
                    {
                        'code': 'E00003',
                        'text': "The element 'creditCard' in namespace 'AnetApi/xml/v1/schema/AnetApiSchema.xsd' "
                        "has incomplete content. List of possible elements expected: 'expirationDate' "
                        "in namespace 'AnetApi/xml/v1/schema/AnetApiSchema.xsd'.",
                    }
                ],
            }
        }
        return self._setup_mock_transaction_controller(mock_create_transaction_controller, mock_response)

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_returns_transaction_id_in_response(self, mock_create_transaction_controller):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_transaction_is_successful(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        response = test_purchase_client.process_charge_for_licensee_privileges(
            licensee_id=MOCK_LICENSEE_ID,
            order_information=_generate_default_order_information(),
            compact_configuration=_generate_aslp_compact_configuration(),
            selected_jurisdictions=_generate_selected_jurisdictions(),
            user_active_military=False,
        )

        self.assertEqual(MOCK_TRANSACTION_ID, response['transactionId'])

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_makes_successful_transaction_using_authorize_net_processor(
        self, mock_create_transaction_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_transaction_is_successful(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        test_purchase_client.process_charge_for_licensee_privileges(
            licensee_id=MOCK_LICENSEE_ID,
            order_information=_generate_default_order_information(),
            compact_configuration=_generate_aslp_compact_configuration(),
            selected_jurisdictions=_generate_selected_jurisdictions(),
            user_active_military=False,
        )

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj = call_args[0]
        # we check every line of the object to ensure that the correct values are being passed to the authorize.net SDK
        self.assertEqual('authCaptureTransaction', api_contract_v1_obj.transactionRequest.transactionType)
        # authentication fields
        self.assertEqual(MOCK_LOGIN_ID, api_contract_v1_obj.merchantAuthentication.name)
        self.assertEqual(MOCK_TRANSACTION_KEY, api_contract_v1_obj.merchantAuthentication.transactionKey)
        # credit card payment fields
        self.assertEqual('4111111111111112', api_contract_v1_obj.transactionRequest.payment.creditCard.cardNumber)
        self.assertEqual('2035-10', api_contract_v1_obj.transactionRequest.payment.creditCard.expirationDate)
        self.assertEqual('125', api_contract_v1_obj.transactionRequest.payment.creditCard.cardCode)
        # transaction billing fields
        self.assertEqual(EXPECTED_TOTAL_FEE_AMOUNT, api_contract_v1_obj.transactionRequest.amount)
        self.assertEqual('USD', api_contract_v1_obj.transactionRequest.currencyCode)
        self.assertEqual('OH', api_contract_v1_obj.transactionRequest.billTo.state)
        self.assertEqual('12345', api_contract_v1_obj.transactionRequest.billTo.zip)
        self.assertEqual('123 Test St', api_contract_v1_obj.transactionRequest.billTo.address)
        self.assertEqual('testFirstName', api_contract_v1_obj.transactionRequest.billTo.firstName)
        self.assertEqual('testLastName', api_contract_v1_obj.transactionRequest.billTo.lastName)
        # transaction settings
        self.assertEqual('180', api_contract_v1_obj.transactionRequest.transactionSettings.setting[0].settingValue)
        self.assertEqual(
            'duplicateWindow', api_contract_v1_obj.transactionRequest.transactionSettings.setting[0].settingName
        )
        # ensure tax exempt is set to true
        self.assertEqual(True, api_contract_v1_obj.transactionRequest.taxExempt)

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_sends_expected_line_items_when_purchasing_privileges_with_authorize_net_processor(
        self, mock_create_transaction_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_transaction_is_successful(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        test_purchase_client.process_charge_for_licensee_privileges(
            licensee_id=MOCK_LICENSEE_ID,
            order_information=_generate_default_order_information(),
            compact_configuration=_generate_aslp_compact_configuration(),
            selected_jurisdictions=_generate_selected_jurisdictions(),
            user_active_military=False,
        )

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj = call_args[0]

        # we check every line item of the object to ensure that the correct values are being set
        self.assertEqual(2, len(api_contract_v1_obj.transactionRequest.lineItems.lineItem))
        # first line item is the jurisdiction fee
        self.assertEqual('aslp-oh', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].itemId)
        self.assertEqual('Ohio Compact Privilege', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].name)
        self.assertEqual(100.00, api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].unitPrice)
        self.assertEqual(1, api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].quantity)
        self.assertEqual(
            'Compact Privilege for Ohio', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].description
        )
        # second line item is the compact fee
        self.assertEqual('aslp-compact-fee', api_contract_v1_obj.transactionRequest.lineItems.lineItem[1].itemId)
        self.assertEqual('ASLP Compact Fee', api_contract_v1_obj.transactionRequest.lineItems.lineItem[1].name)
        self.assertEqual(50.50, api_contract_v1_obj.transactionRequest.lineItems.lineItem[1].unitPrice)
        self.assertEqual(1, api_contract_v1_obj.transactionRequest.lineItems.lineItem[1].quantity)
        self.assertEqual(
            'Compact fee applied for each privilege purchased',
            api_contract_v1_obj.transactionRequest.lineItems.lineItem[1].description,
        )

        # ensure the total amount is the sum of the two line items
        self.assertEqual(150.50, api_contract_v1_obj.transactionRequest.amount)

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_sets_licensee_id_in_order_description(
            self, mock_create_transaction_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_transaction_is_successful(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        test_purchase_client.process_charge_for_licensee_privileges(
            licensee_id=MOCK_LICENSEE_ID,
            order_information=_generate_default_order_information(),
            compact_configuration=_generate_aslp_compact_configuration(),
            selected_jurisdictions=_generate_selected_jurisdictions(),
            user_active_military=False,
        )

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj = call_args[0]

        self.assertEqual(f'LICENSEE#{MOCK_LICENSEE_ID}#', api_contract_v1_obj.transactionRequest.order.description)

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_sends_expected_line_items_when_purchasing_privileges_with_military_discount(
        self, mock_create_transaction_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_transaction_is_successful(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        test_purchase_client.process_charge_for_licensee_privileges(
            licensee_id=MOCK_LICENSEE_ID,
            order_information=_generate_default_order_information(),
            compact_configuration=_generate_aslp_compact_configuration(),
            selected_jurisdictions=_generate_selected_jurisdictions(),
            user_active_military=True,
        )

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj = call_args[0]
        # we check every line item of the object to ensure that the correct values are being set
        self.assertEqual(2, len(api_contract_v1_obj.transactionRequest.lineItems.lineItem))
        # verify jurisdiction fee line item with military discount
        self.assertEqual('aslp-oh', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].itemId)
        self.assertEqual('Ohio Compact Privilege', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].name)
        self.assertEqual(75.00, api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].unitPrice)
        self.assertEqual(1, api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].quantity)
        self.assertEqual(
            'Compact Privilege for Ohio (Military Discount)',
            api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].description,
        )

        # ensure the total amount is the sum of the two line items
        self.assertEqual(125.50, api_contract_v1_obj.transactionRequest.amount)

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_raises_failed_transaction_exception_when_transaction_fails(
        self, mock_create_transaction_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_transaction_fails(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        with self.assertRaises(CCFailedTransactionException):
            test_purchase_client.process_charge_for_licensee_privileges(
                licensee_id=MOCK_LICENSEE_ID,
                order_information=_generate_default_order_information(),
                compact_configuration=_generate_aslp_compact_configuration(),
                selected_jurisdictions=_generate_selected_jurisdictions(),
                user_active_military=False,
            )

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_raises_internal_exception_when_api_fails(self, mock_create_transaction_controller):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_api_call_fails(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        with self.assertRaises(CCInternalException):
            test_purchase_client.process_charge_for_licensee_privileges(
                licensee_id=MOCK_LICENSEE_ID,
                order_information=_generate_default_order_information(),
                compact_configuration=_generate_aslp_compact_configuration(),
                selected_jurisdictions=_generate_selected_jurisdictions(),
                user_active_military=False,
            )

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_voids_transaction_using_authorize_net_processor(self, mock_create_transaction_controller):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_transaction_is_successful(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        result = test_purchase_client.void_privilege_purchase_transaction(
            compact_name='aslp',
            order_information={'transactionId': MOCK_TRANSACTION_ID},
        )

        self.assertEqual({'message': 'Successfully voided transaction', 'transactionId': MOCK_TRANSACTION_ID}, result)

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj = call_args[0]
        # we check every line of the object to ensure that the correct values are being passed to the authorize.net SDK
        self.assertEqual('voidTransaction', api_contract_v1_obj.transactionRequest.transactionType)
        # authentication fields
        self.assertEqual(MOCK_LOGIN_ID, api_contract_v1_obj.merchantAuthentication.name)
        self.assertEqual(MOCK_TRANSACTION_KEY, api_contract_v1_obj.merchantAuthentication.transactionKey)
        # transaction billing fields
        self.assertEqual(MOCK_TRANSACTION_ID, api_contract_v1_obj.transactionRequest.refTransId)

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_raises_internal_exception_when_void_transction_api_fails(
        self, mock_create_transaction_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_api_call_fails(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        with self.assertRaises(CCInternalException):
            test_purchase_client.void_privilege_purchase_transaction(
                compact_name='aslp',
                order_information={'transactionId': MOCK_TRANSACTION_ID},
            )

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_raises_failed_transaction_exception_when_void_transaction_fails(
        self, mock_create_transaction_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_transaction_fails(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        with self.assertRaises(CCFailedTransactionException):
            test_purchase_client.void_privilege_purchase_transaction(
                compact_name='aslp',
                order_information={'transactionId': MOCK_TRANSACTION_ID},
            )

    @staticmethod
    def _generate_test_credentials_object():
        return {
            'processor': 'authorize.net',
            'apiLoginId': MOCK_LOGIN_ID,
            'transactionKey': MOCK_TRANSACTION_KEY,
        }

    def _when_authorize_dot_net_credentials_are_valid(self, mock_create_transaction_controller):
        mock_success_response = {
            'messages': {'resultCode': 'Ok', 'message': [{'code': 'I00001', 'text': 'Successful.'}]}
        }

        return self._setup_mock_transaction_controller(mock_create_transaction_controller, mock_success_response)

    def _when_authorize_dot_net_credentials_are_not_valid(self, mock_create_transaction_controller):
        mock_success_response = {
            'messages': {
                'resultCode': 'Error',
                'message': [{'code': 'E00124', 'text': 'The provided access token is invalid'}],
            }
        }

        return self._setup_mock_transaction_controller(mock_create_transaction_controller, mock_success_response)

    @patch('purchase_client.getMerchantDetailsController')
    def test_purchase_client_validates_credentials_using_authorize_net_processor(
        self, mock_get_merchant_details_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_credentials_are_valid(
            mock_create_transaction_controller=mock_get_merchant_details_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        result = test_purchase_client.validate_and_store_credentials(
            compact_name='aslp', credentials=self._generate_test_credentials_object()
        )

        self.assertEqual({'message': 'Successfully verified credentials'}, result)

        call_args = mock_get_merchant_details_controller.call_args.args
        api_contract_v1_obj = call_args[0]
        # authentication fields
        self.assertEqual(MOCK_LOGIN_ID, api_contract_v1_obj.merchantAuthentication.name)
        self.assertEqual(MOCK_TRANSACTION_KEY, api_contract_v1_obj.merchantAuthentication.transactionKey)

    @patch('purchase_client.getMerchantDetailsController')
    def test_purchase_client_creates_secret_when_secret_does_not_exist(self, mock_get_merchant_details_controller):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_credentials_are_valid(
            mock_create_transaction_controller=mock_get_merchant_details_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        result = test_purchase_client.validate_and_store_credentials(
            compact_name='octp', credentials=self._generate_test_credentials_object()
        )

        self.assertEqual({'message': 'Successfully verified credentials'}, result)

        mock_secrets_manager_client.create_secret.assert_called_once_with(
            Name='compact-connect/env/test/compact/octp/credentials/payment-processor',
            SecretString=json.dumps(
                {
                    'processor': 'authorize.net',
                    'api_login_id': MOCK_LOGIN_ID,
                    'transaction_key': MOCK_TRANSACTION_KEY,
                }
            ),
        )

    @patch('purchase_client.getMerchantDetailsController')
    def test_purchase_client_updates_secret_when_secret_exists(self, mock_get_merchant_details_controller):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_credentials_are_valid(
            mock_create_transaction_controller=mock_get_merchant_details_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        # In this case, the 'aslp' compact has an existing secret in place
        # so if a compact admin uploads new credentials, the existing secret should be updated
        result = test_purchase_client.validate_and_store_credentials(
            compact_name='aslp', credentials=self._generate_test_credentials_object()
        )

        self.assertEqual({'message': 'Successfully verified credentials'}, result)

        mock_secrets_manager_client.put_secret_value.assert_called_once_with(
            SecretId='compact-connect/env/test/compact/aslp/credentials/payment-processor',
            SecretString=json.dumps(
                {
                    'processor': 'authorize.net',
                    'api_login_id': MOCK_LOGIN_ID,
                    'transaction_key': MOCK_TRANSACTION_KEY,
                }
            ),
        )

    @patch('purchase_client.getMerchantDetailsController')
    def test_purchase_client_raises_exception_if_invalid_processor(self, mock_get_merchant_details_controller):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_credentials_are_valid(
            mock_create_transaction_controller=mock_get_merchant_details_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        with self.assertRaises(CCInvalidRequestException):
            test_purchase_client.validate_and_store_credentials(
                compact_name='aslp',
                credentials={
                    'processor': 'stripe',
                    'apiLoginId': 'mock_login_id',
                    'transactionKey': MOCK_TRANSACTION_KEY,
                },
            )

    @patch('purchase_client.getMerchantDetailsController')
    def test_purchase_client_raises_exception_if_invalid_credentials(self, mock_get_merchant_details_controller):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_credentials_are_not_valid(
            mock_create_transaction_controller=mock_get_merchant_details_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        with self.assertRaises(CCInvalidRequestException) as context:
            test_purchase_client.validate_and_store_credentials(
                compact_name='aslp', credentials=self._generate_test_credentials_object()
            )

        self.assertIn('Failed to verify credentials', str(context.exception.message))
