# ruff: noqa: ARG001 unused-argument
import json
import os
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import boto3
from cc_common.config import config
from cc_common.exceptions import CCFailedTransactionException, CCInternalException, CCInvalidRequestException
from moto import mock_aws

from tests import TstLambdas

MOCK_LOGIN_ID = 'mock_login_id'
MOCK_TRANSACTION_KEY = 'R2d237rZu59q123'
MOCK_ASLP_SECRET = {
    'processor': 'authorize.net',
    'api_login_id': MOCK_LOGIN_ID,
    'transaction_key': MOCK_TRANSACTION_KEY,
}

MOCK_CURRENT_DATETIME = '2024-11-08T23:59:59+00:00'

MOCK_TRANSACTION_ID = '123456'

MOCK_LICENSEE_ID = '89a6377e-c3a5-40e5-bca5-317ec854c570'

MOCK_LICENSEE_TRANSACTION_FEE_AMOUNT = 5

MOCK_LICENSE_TYPE_ABBR = 'slp'

# Test constants for transaction history tests
MOCK_BATCH_ID = '12345'
MOCK_BATCH_ID_2 = '12346'
MOCK_PROCESSED_BATCH_ID = '12344'
MOCK_PREVIOUS_TRANSACTION_ID = '67889'
MOCK_ITEM_ID = 'ITEM001'
MOCK_ITEM_NAME = 'Test Item'
MOCK_ITEM_DESCRIPTION = 'Test Description'
MOCK_ITEM_QUANTITY = '1'
MOCK_ITEM_PRICE = '10.00'

# these transaction ids must be numeric to match the authorize.net SDK response
MOCK_TRANSACTION_ID_1_BATCH_1 = '11'
MOCK_TRANSACTION_ID_1_BATCH_2 = '12'
MOCK_TRANSACTION_ID_2_BATCH_2 = '22'

# Test constants for transaction states and types
SUCCESSFUL_RESULT_CODE = 'Ok'
SUCCESSFUL_SETTLED_STATE = 'settledSuccessfully'
SETTLEMENT_ERROR_STATE = 'settlementError'
AUTH_CAPTURE_TRANSACTION_TYPE = 'authCaptureTransaction'

# Test timestamps
MOCK_SETTLEMENT_TIME_UTC = '2024-12-27T17:49:20.757Z'
MOCK_SETTLEMENT_TIME_LOCAL = '2024-12-27T13:49:20.757'
MOCK_SETTLEMENT_TIME_UTC_2 = '2024-12-26T15:15:20.007Z'
MOCK_SETTLEMENT_TIME_LOCAL_2 = '2024-12-26T11:15:20.007Z'

# mock order information
# common descriptor returned by authorize.net
MOCK_DATA_DESCRIPTOR = 'COMMON.ACCEPT.INAPP.PAYMENT'
MOCK_DATA_VALUE = 'eyJjbMockDataValue'

# mock public key for getMerchantsDetails call
MOCK_PUBLIC_CLIENT_KEY = 'mockPublicClientKey'


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
    return {'opaqueData': {'dataDescriptor': MOCK_DATA_DESCRIPTOR, 'dataValue': MOCK_DATA_VALUE}}


def _generate_aslp_compact_configuration(include_licensee_charges: bool = False):
    from cc_common.data_model.schema.compact import Compact

    with open('../common/tests/resources/dynamo/compact.json') as f:
        # setting fixed fee amount for tests
        compact = json.load(f)
        # DynamoDB loads this as a Decimal
        compact['compactCommissionFee']['feeAmount'] = Decimal(50.50)
        # the compact.json file includes licensee charges by default,
        # so we need to set this to False if we don't want them
        if not include_licensee_charges:
            compact['transactionFeeConfiguration']['licenseeCharges']['active'] = False
        # setting the fee amount explicitly here to make calculation easy to check
        compact['transactionFeeConfiguration']['licenseeCharges']['chargeAmount'] = Decimal(
            MOCK_LICENSEE_TRANSACTION_FEE_AMOUNT
        )
        return Compact(compact)


def _generate_selected_jurisdictions(jurisdiction_items: list[dict] = None):
    from cc_common.data_model.schema.jurisdiction import Jurisdiction

    if jurisdiction_items is None:
        jurisdiction_items = [
            {'postalCode': 'oh', 'jurisdictionName': 'ohio', 'privilegeFee': 100.00},
        ]

    jurisdiction_configurations = []

    for jurisdiction_test_item in jurisdiction_items:
        with open('../common/tests/resources/dynamo/jurisdiction.json') as f:
            jurisdiction = json.load(f)
            for licensee_fee in jurisdiction['privilegeFees']:
                # DynamoDB loads this as a decimal
                licensee_fee['amount'] = Decimal(jurisdiction_test_item['privilegeFee'])
                # Add military rate to each fee
                licensee_fee['militaryRate'] = Decimal(40.00)

            jurisdiction['postalAbbreviation'] = jurisdiction_test_item['postalCode']
            jurisdiction['jurisdictionName'] = jurisdiction_test_item['jurisdictionName']
            jurisdiction_configurations.append(Jurisdiction(jurisdiction))

    return jurisdiction_configurations


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_DATETIME))
class TestAuthorizeDotNetPurchaseClient(TstLambdas):
    """Testing that the purchase client works with authorize.net SDK as expected."""

    def setUp(self):  # noqa: N801 invalid-name
        super().setUp()

        self.create_compact_configuration_table()
        self.addCleanup(self.delete_resources)

        import cc_common.config
        from common_test.test_data_generator import TestDataGenerator

        cc_common.config.config = cc_common.config._Config()  # noqa: SLF001 protected-access
        self.config = cc_common.config.config
        self.test_data_generator = TestDataGenerator

    def create_compact_configuration_table(self):
        self._compact_configuration_table = boto3.resource('dynamodb').create_table(
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            TableName=os.environ['COMPACT_CONFIGURATION_TABLE_NAME'],
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}, {'AttributeName': 'sk', 'KeyType': 'RANGE'}],
            BillingMode='PAY_PER_REQUEST',
        )

    def delete_resources(self):
        self._compact_configuration_table.delete()

        waiter = self._compact_configuration_table.meta.client.get_waiter('table_not_exists')
        waiter.wait(TableName=self._compact_configuration_table.name)

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

    def _when_authorize_dot_net_has_api_error_code(self, mock_create_transaction_controller, error_code, error_text):
        # Create a specific mock for the E00114 error that handles the SDK's inconsistent access patterns
        mock_response_data = {
            'messages': {
                'resultCode': 'Error',
                'message': [
                    {
                        'code': error_code,
                        'text': error_text,
                    }
                ],
            }
        }
        mock_response = json_to_magic_mock(mock_response_data)

        # Create a message mock that supports both attribute and dictionary access
        message_mock = MagicMock()

        # Set up the 'code' field to support message['code']
        code_mock = MagicMock()
        code_mock.text = error_code

        # Set up the 'text' field
        text_mock = MagicMock()
        text_mock.text = error_text

        # Add dictionary-style access for message['text']
        def message_getitem_with_text_attribute(self, key):
            if key == 'code':
                return code_mock
            if key == 'text':
                return text_mock
            raise KeyError(key)

        message_mock.__getitem__ = message_getitem_with_text_attribute

        mock_response.messages.message = [message_mock]

        mock_transaction_controller = MagicMock()
        mock_transaction_controller.getresponse.return_value = mock_response

        mock_create_transaction_controller.return_value = mock_transaction_controller
        return mock_transaction_controller

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_returns_expected_response(self, mock_create_transaction_controller):
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
            license_type_abbreviation=MOCK_LICENSE_TYPE_ABBR,
            user_active_military=False,
        )

        self.assertEqual(
            {
                'transactionId': MOCK_TRANSACTION_ID,
                'lineItems': [
                    {
                        'description': 'Compact Privilege for Ohio',
                        'itemId': 'priv:aslp-oh-slp',
                        'name': 'Ohio Compact Privilege',
                        'quantity': '1',
                        'taxable': 'None',
                        'unitPrice': '100',
                    },
                    {
                        'description': 'Compact fee applied for each privilege purchased',
                        'itemId': 'aslp-compact-fee',
                        'name': 'ASLP Compact Fee',
                        'quantity': '1',
                        'taxable': 'None',
                        'unitPrice': '50.5',
                    },
                ],
                'message': 'Successfully processed charge',
                'submitTimeUTC': MOCK_CURRENT_DATETIME,
            },
            response,
        )

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_returns_expected_line_items_in_response(self, mock_create_transaction_controller):
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
            license_type_abbreviation=MOCK_LICENSE_TYPE_ABBR,
            user_active_military=False,
        )

        # we check every line item of the object to ensure that the correct values are being set
        self.assertEqual(2, len(response['lineItems']))
        # first line item is the jurisdiction fee
        self.assertEqual(
            response['lineItems'],
            [
                {
                    'itemId': 'priv:aslp-oh-slp',
                    'name': 'Ohio Compact Privilege',
                    'unitPrice': '100',
                    'quantity': '1',
                    'description': 'Compact Privilege for Ohio',
                    'taxable': 'None',
                },
                {
                    'itemId': 'aslp-compact-fee',
                    'name': 'ASLP Compact Fee',
                    'unitPrice': '50.5',
                    'quantity': '1',
                    'description': 'Compact fee applied for each privilege purchased',
                    'taxable': 'None',
                },
            ],
        )

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
            license_type_abbreviation=MOCK_LICENSE_TYPE_ABBR,
            user_active_military=False,
        )

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj = call_args[0]
        # we check every line of the object to ensure that the correct values are being passed to the authorize.net SDK
        self.assertEqual('authCaptureTransaction', api_contract_v1_obj.transactionRequest.transactionType)
        # authentication fields
        self.assertEqual(MOCK_LOGIN_ID, api_contract_v1_obj.merchantAuthentication.name)
        self.assertEqual(MOCK_TRANSACTION_KEY, api_contract_v1_obj.merchantAuthentication.transactionKey)
        # opaque data fields
        self.assertEqual(MOCK_DATA_DESCRIPTOR, api_contract_v1_obj.transactionRequest.payment.opaqueData.dataDescriptor)
        self.assertEqual(MOCK_DATA_VALUE, api_contract_v1_obj.transactionRequest.payment.opaqueData.dataValue)
        # transaction billing fields
        expected_total_fee_amount = 150.50
        self.assertEqual(expected_total_fee_amount, api_contract_v1_obj.transactionRequest.amount)
        self.assertEqual('USD', api_contract_v1_obj.transactionRequest.currencyCode)
        # transaction settings
        self.assertEqual('35', api_contract_v1_obj.transactionRequest.transactionSettings.setting[0].settingValue)
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
            license_type_abbreviation=MOCK_LICENSE_TYPE_ABBR,
            user_active_military=False,
        )

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj = call_args[0]

        # we check every line item of the object to ensure that the correct values are being set
        self.assertEqual(2, len(api_contract_v1_obj.transactionRequest.lineItems.lineItem))
        # first line item is the jurisdiction fee
        self.assertEqual('priv:aslp-oh-slp', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].itemId)
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
    def test_purchase_client_sends_expected_line_items_when_licensee_charges_are_active(
        self, mock_create_transaction_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_transaction_is_successful(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        test_jurisdictions = [
            {'postalCode': 'oh', 'jurisdictionName': 'ohio', 'privilegeFee': 50.00},
            {'postalCode': 'ky', 'jurisdictionName': 'kentucky', 'privilegeFee': 200.00},
        ]

        test_purchase_client.process_charge_for_licensee_privileges(
            licensee_id=MOCK_LICENSEE_ID,
            order_information=_generate_default_order_information(),
            compact_configuration=_generate_aslp_compact_configuration(include_licensee_charges=True),
            selected_jurisdictions=_generate_selected_jurisdictions(test_jurisdictions),
            license_type_abbreviation=MOCK_LICENSE_TYPE_ABBR,
            user_active_military=False,
        )

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj = call_args[0]

        # we check every line item of the object to ensure that the correct values are being set
        self.assertEqual(4, len(api_contract_v1_obj.transactionRequest.lineItems.lineItem))
        # first line item is the jurisdiction fee
        self.assertEqual('priv:aslp-oh-slp', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].itemId)
        self.assertEqual('Ohio Compact Privilege', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].name)
        self.assertEqual(50.00, api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].unitPrice)
        self.assertEqual(1, api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].quantity)
        self.assertEqual(
            'Compact Privilege for Ohio', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].description
        )
        # the second line item is the jurisdiction fee for kentucky
        self.assertEqual('priv:aslp-ky-slp', api_contract_v1_obj.transactionRequest.lineItems.lineItem[1].itemId)
        self.assertEqual(
            'Kentucky Compact Privilege', api_contract_v1_obj.transactionRequest.lineItems.lineItem[1].name
        )
        self.assertEqual(200.00, api_contract_v1_obj.transactionRequest.lineItems.lineItem[1].unitPrice)
        self.assertEqual(1, api_contract_v1_obj.transactionRequest.lineItems.lineItem[1].quantity)
        self.assertEqual(
            'Compact Privilege for Kentucky', api_contract_v1_obj.transactionRequest.lineItems.lineItem[1].description
        )

        # third line item is the compact fee
        self.assertEqual('aslp-compact-fee', api_contract_v1_obj.transactionRequest.lineItems.lineItem[2].itemId)
        self.assertEqual(2, api_contract_v1_obj.transactionRequest.lineItems.lineItem[2].quantity)
        self.assertEqual(50.50, api_contract_v1_obj.transactionRequest.lineItems.lineItem[2].unitPrice)
        # fourth line item is the licensee charge
        self.assertEqual(
            'credit-card-transaction-fee', api_contract_v1_obj.transactionRequest.lineItems.lineItem[3].itemId
        )
        self.assertEqual(2, api_contract_v1_obj.transactionRequest.lineItems.lineItem[3].quantity)
        self.assertEqual(
            'Credit Card Transaction Fee', api_contract_v1_obj.transactionRequest.lineItems.lineItem[3].name
        )
        self.assertEqual(
            'Transaction fee for credit card processing',
            api_contract_v1_obj.transactionRequest.lineItems.lineItem[3].description,
        )
        self.assertEqual(
            MOCK_LICENSEE_TRANSACTION_FEE_AMOUNT, api_contract_v1_obj.transactionRequest.lineItems.lineItem[3].unitPrice
        )

        # ensure the total amount is the sum of the four line items
        # 50 + 200 + (50.50 * 2) + (5 * 2) = 361
        self.assertEqual(361.00, api_contract_v1_obj.transactionRequest.amount)

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_sets_licensee_id_in_order_description(self, mock_create_transaction_controller):
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
            license_type_abbreviation=MOCK_LICENSE_TYPE_ABBR,
            user_active_military=False,
        )

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj = call_args[0]

        self.assertEqual(f'LICENSEE#{MOCK_LICENSEE_ID}#', api_contract_v1_obj.transactionRequest.order.description)

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_sends_expected_line_items_when_purchasing_privileges_with_military_rate(
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
            license_type_abbreviation=MOCK_LICENSE_TYPE_ABBR,
            user_active_military=True,
        )

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj = call_args[0]
        # we check every line item of the object to ensure that the correct values are being set
        self.assertEqual(2, len(api_contract_v1_obj.transactionRequest.lineItems.lineItem))
        # verify jurisdiction fee line item with military rate
        self.assertEqual('priv:aslp-oh-slp', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].itemId)
        self.assertEqual('Ohio Compact Privilege', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].name)
        self.assertEqual(40.00, api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].unitPrice)
        self.assertEqual(1, api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].quantity)
        self.assertEqual(
            'Compact Privilege for Ohio (Military Rate)',
            api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].description,
        )

        # ensure the total amount is the sum of the two line items (military rate + compact fee)
        self.assertEqual(90.50, api_contract_v1_obj.transactionRequest.amount)

    @patch('purchase_client.createTransactionController')
    def test_standard_fee_used_when_military_rate_not_present(self, mock_create_transaction_controller):
        from cc_common.data_model.schema.jurisdiction import Jurisdiction
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_transaction_is_successful(
            mock_create_transaction_controller=mock_create_transaction_controller
        )

        # Create jurisdictions with no military rate
        jurisdiction_configurations = []
        with open('../common/tests/resources/dynamo/jurisdiction.json') as f:
            jurisdiction = json.load(f)
            for licensee_fee in jurisdiction['privilegeFees']:
                licensee_fee['amount'] = Decimal(100.00)
                # Remove military rate if present
                if 'militaryRate' in licensee_fee:
                    del licensee_fee['militaryRate']

            jurisdiction['postalAbbreviation'] = 'oh'
            jurisdiction['jurisdictionName'] = 'ohio'
            jurisdiction_configurations.append(Jurisdiction(jurisdiction))

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        test_purchase_client.process_charge_for_licensee_privileges(
            licensee_id=MOCK_LICENSEE_ID,
            order_information=_generate_default_order_information(),
            compact_configuration=_generate_aslp_compact_configuration(),
            selected_jurisdictions=jurisdiction_configurations,
            license_type_abbreviation=MOCK_LICENSE_TYPE_ABBR,
            user_active_military=True,
        )

        call_args = mock_create_transaction_controller.call_args.args
        api_contract_v1_obj = call_args[0]

        # verify jurisdiction fee line item uses standard rate when no military rate present
        self.assertEqual('priv:aslp-oh-slp', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].itemId)
        self.assertEqual('Ohio Compact Privilege', api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].name)
        self.assertEqual(100.00, api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].unitPrice)
        self.assertEqual(
            'Compact Privilege for Ohio',
            api_contract_v1_obj.transactionRequest.lineItems.lineItem[0].description,
        )

        # ensure the total amount is the sum of standard fee + compact fee
        self.assertEqual(150.50, api_contract_v1_obj.transactionRequest.amount)

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
                license_type_abbreviation=MOCK_LICENSE_TYPE_ABBR,
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
                license_type_abbreviation=MOCK_LICENSE_TYPE_ABBR,
                user_active_military=False,
            )

    @patch('purchase_client.createTransactionController')
    def test_purchase_client_raises_invalid_request_exception_when_suspicious_activity_filter_triggers(
        self, mock_create_transaction_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_has_api_error_code(
            mock_create_transaction_controller=mock_create_transaction_controller,
            error_code='E00114',
            error_text='Invalid OTS Token.',
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        with self.assertRaises(CCInvalidRequestException) as context:
            test_purchase_client.process_charge_for_licensee_privileges(
                licensee_id=MOCK_LICENSEE_ID,
                order_information=_generate_default_order_information(),
                compact_configuration=_generate_aslp_compact_configuration(),
                selected_jurisdictions=_generate_selected_jurisdictions(),
                license_type_abbreviation=MOCK_LICENSE_TYPE_ABBR,
                user_active_military=False,
            )

        # Verify that the specific user-friendly message is returned
        self.assertEqual(
            "The transaction was declined by the payment processor's security filters. "
            'Please wait a moment and try your transaction again.',
            str(context.exception.message),
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
            compact_abbr='aslp',
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
                compact_abbr='aslp',
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
                compact_abbr='aslp',
                order_information={'transactionId': MOCK_TRANSACTION_ID},
            )

    @staticmethod
    def _generate_test_credentials_object():
        return {
            'processor': 'authorize.net',
            'apiLoginId': MOCK_LOGIN_ID,
            'transactionKey': MOCK_TRANSACTION_KEY,
        }

    def _when_compact_configuration_exists(self, value_overrides: dict | None = None):
        self.test_data_generator.put_default_compact_configuration_in_configuration_table(value_overrides)

    def _when_authorize_dot_net_credentials_are_valid(self, mock_create_transaction_controller):
        mock_success_response = {
            'messages': {
                'resultCode': 'Ok',
                'message': [{'code': 'I00001', 'text': 'Successful.'}],
            },
            'publicClientKey': MOCK_PUBLIC_CLIENT_KEY,
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
        self._when_compact_configuration_exists()

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        result = test_purchase_client.validate_and_store_credentials(
            compact_abbr='aslp', credentials=self._generate_test_credentials_object()
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
        self._when_compact_configuration_exists(
            value_overrides={
                'compactAbbr': 'octp',
            }
        )

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        result = test_purchase_client.validate_and_store_credentials(
            compact_abbr='octp', credentials=self._generate_test_credentials_object()
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
        self._when_compact_configuration_exists()

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        # In this case, the 'aslp' compact has an existing secret in place
        # so if a compact admin uploads new credentials, the existing secret should be updated
        result = test_purchase_client.validate_and_store_credentials(
            compact_abbr='aslp', credentials=self._generate_test_credentials_object()
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
    def test_purchase_client_raises_exception_when_validating_credentials_and_compact_configuration_does_not_exist(
        self, mock_get_merchant_details_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_credentials_are_valid(
            mock_create_transaction_controller=mock_get_merchant_details_controller
        )
        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)

        # In this case, the 'aslp' compact has not configured their compact configuration, which is a pre-requisite to
        # setting the payment processor public values, as we store these fields in that object.
        # The exception message should give them clear instructions to set that configuration up and then try
        # to upload the credentials again.
        with self.assertRaises(CCInvalidRequestException) as context:
            test_purchase_client.validate_and_store_credentials(
                compact_abbr='aslp', credentials=self._generate_test_credentials_object()
            )

        self.assertEqual(
            'Compact Fee configuration has not been configured yet. '
            'Please configure the compact fee values and then upload your '
            'credentials again.',
            str(context.exception.message),
        )

        mock_secrets_manager_client.put_secret_value.assert_not_called()

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
                compact_abbr='aslp',
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
                compact_abbr='aslp', credentials=self._generate_test_credentials_object()
            )

        self.assertIn('Failed to verify credentials', str(context.exception.message))

    def _when_authorize_dot_net_batch_list_is_successful(self, mock_controller):
        mock_response = {
            'messages': {
                'resultCode': SUCCESSFUL_RESULT_CODE,
            },
            'batchList': {
                'batch': [
                    {
                        'batchId': MOCK_BATCH_ID,
                        'settlementTimeUTC': MOCK_SETTLEMENT_TIME_UTC,
                        'settlementTimeLocal': MOCK_SETTLEMENT_TIME_LOCAL,
                        'settlementState': SUCCESSFUL_SETTLED_STATE,
                    }
                ]
            },
        }
        return self._setup_mock_transaction_controller(mock_controller, mock_response)

    def _generate_mock_transaction_list_response(
        self, transaction_ids: list[str], transaction_status: str = SUCCESSFUL_SETTLED_STATE
    ):
        return {
            'messages': {
                'resultCode': SUCCESSFUL_RESULT_CODE,
            },
            'transactions': {
                'transaction': [
                    {
                        'transId': transaction_id,
                        'transactionStatus': transaction_status,
                    }
                    for transaction_id in transaction_ids
                ]
            },
            'totalNumInResultSet': 1,
        }

    def _when_authorize_dot_net_transaction_list_is_successful(self, mock_controller):
        mock_response = self._generate_mock_transaction_list_response([MOCK_TRANSACTION_ID], SUCCESSFUL_SETTLED_STATE)
        return self._setup_mock_transaction_controller(mock_controller, mock_response)

    def _when_authorize_dot_net_transaction_list_is_failed(self, mock_controller):
        mock_response = self._generate_mock_transaction_list_response([MOCK_TRANSACTION_ID], SETTLEMENT_ERROR_STATE)
        return self._setup_mock_transaction_controller(mock_controller, mock_response)

    def _generate_mock_transaction_detail_response(
        self, transaction_id: str, transaction_status: str = SUCCESSFUL_SETTLED_STATE
    ):
        return {
            'messages': {
                'resultCode': SUCCESSFUL_RESULT_CODE,
            },
            'transaction': {
                'transId': transaction_id,
                'submitTimeUTC': MOCK_SETTLEMENT_TIME_UTC,
                'transactionType': AUTH_CAPTURE_TRANSACTION_TYPE,
                'transactionStatus': transaction_status,
                'responseCode': '1',
                'settleAmount': MOCK_ITEM_PRICE,
                'order': {'description': f'LICENSEE#{MOCK_LICENSEE_ID}#'},
                'lineItems': {
                    'lineItem': [
                        {
                            'itemId': MOCK_ITEM_ID,
                            'name': MOCK_ITEM_NAME,
                            'description': MOCK_ITEM_DESCRIPTION,
                            'quantity': MOCK_ITEM_QUANTITY,
                            'unitPrice': MOCK_ITEM_PRICE,
                            'taxable': 'false',
                        }
                    ]
                },
            },
        }

    def _when_authorize_dot_net_transaction_details_are_successful(self, mock_controller):
        mock_response = self._generate_mock_transaction_detail_response(MOCK_TRANSACTION_ID)
        return self._setup_mock_transaction_controller(mock_controller, mock_response)

    def _when_authorize_dot_net_transaction_details_are_failed(self, mock_controller):
        mock_response = self._generate_mock_transaction_detail_response(MOCK_TRANSACTION_ID, SETTLEMENT_ERROR_STATE)
        return self._setup_mock_transaction_controller(mock_controller, mock_response)

    @patch('purchase_client.getSettledBatchListController')
    @patch('purchase_client.getTransactionListController')
    @patch('purchase_client.getTransactionDetailsController')
    def test_purchase_client_gets_settled_transactions_successfully(
        self,
        mock_details_controller,
        mock_transaction_controller,
        mock_batch_controller,
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()
        self._when_authorize_dot_net_batch_list_is_successful(mock_batch_controller)
        self._when_authorize_dot_net_transaction_list_is_successful(mock_transaction_controller)
        self._when_authorize_dot_net_transaction_details_are_successful(mock_details_controller)

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)
        response = test_purchase_client.get_settled_transactions(
            compact='aslp',
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-02T00:00:00Z',
            transaction_limit=500,
        )

        # Verify response structure
        self.assertIn('transactions', response)
        self.assertEqual(len(response['transactions']), 1)
        self.assertIn('processedBatchIds', response)
        self.assertEqual(len(response['processedBatchIds']), 1)
        self.assertEqual([], response['settlementErrorTransactionIds'])

        # Verify transaction data
        transaction = response['transactions'][0]

        self.assertEqual(transaction.transactionId, MOCK_TRANSACTION_ID)
        self.assertEqual(transaction.compact, 'aslp')
        self.assertEqual(transaction.licenseeId, MOCK_LICENSEE_ID)
        self.assertEqual(transaction.batch['batchId'], MOCK_BATCH_ID)
        self.assertEqual(len(transaction.lineItems), 1)

    @patch('purchase_client.getSettledBatchListController')
    @patch('purchase_client.getTransactionListController')
    @patch('purchase_client.getTransactionDetailsController')
    def test_purchase_client_handles_pagination_for_settled_transactions(
        self,
        mock_details_controller,
        mock_transaction_controller,
        mock_batch_controller,
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()

        # Setup multiple batches
        mock_batch_response = json_to_magic_mock(
            {
                'messages': {
                    'resultCode': SUCCESSFUL_RESULT_CODE,
                },
                'batchList': {
                    'batch': [
                        {
                            'batchId': MOCK_BATCH_ID,
                            'settlementTimeUTC': MOCK_SETTLEMENT_TIME_UTC,
                            'settlementTimeLocal': MOCK_SETTLEMENT_TIME_LOCAL,
                            'settlementState': SUCCESSFUL_SETTLED_STATE,
                        },
                        {
                            'batchId': MOCK_BATCH_ID_2,
                            'settlementTimeUTC': MOCK_SETTLEMENT_TIME_UTC_2,
                            'settlementTimeLocal': MOCK_SETTLEMENT_TIME_LOCAL_2,
                            'settlementState': SUCCESSFUL_SETTLED_STATE,
                        },
                    ]
                },
            }
        )
        mock_batch_controller.return_value.getresponse.return_value = mock_batch_response

        mock_transaction_list_responses = [
            # first batch returns one transaction
            json_to_magic_mock(self._generate_mock_transaction_list_response([MOCK_TRANSACTION_ID_1_BATCH_1])),
            # second api call returns two transactions from second call
            json_to_magic_mock(
                self._generate_mock_transaction_list_response(
                    [MOCK_TRANSACTION_ID_1_BATCH_2, MOCK_TRANSACTION_ID_2_BATCH_2]
                )
            ),
            # third api call should be called for second batch again to process remaining transactions,
            # with same transaction list returned
            json_to_magic_mock(
                self._generate_mock_transaction_list_response(
                    [MOCK_TRANSACTION_ID_1_BATCH_2, MOCK_TRANSACTION_ID_2_BATCH_2]
                )
            ),
        ]
        mock_transaction_controller.return_value.getresponse.side_effect = mock_transaction_list_responses

        mock_details_responses = [
            json_to_magic_mock(self._generate_mock_transaction_detail_response(MOCK_TRANSACTION_ID_1_BATCH_1)),
            json_to_magic_mock(self._generate_mock_transaction_detail_response(MOCK_TRANSACTION_ID_1_BATCH_2)),
            json_to_magic_mock(self._generate_mock_transaction_detail_response(MOCK_TRANSACTION_ID_2_BATCH_2)),
        ]
        mock_details_controller.return_value.getresponse.side_effect = mock_details_responses

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)
        response = test_purchase_client.get_settled_transactions(
            compact='aslp',
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-02T00:00:00Z',
            transaction_limit=2,
        )

        # Verify pagination info is returned
        self.assertEqual(MOCK_TRANSACTION_ID_1_BATCH_2, response['lastProcessedTransactionId'])
        self.assertEqual(MOCK_BATCH_ID_2, response['currentBatchId'])
        self.assertEqual([MOCK_BATCH_ID], response['processedBatchIds'])
        # Verify transaction data
        self.assertEqual(2, len(response['transactions']))
        self.assertEqual(response['transactions'][0].transactionId, MOCK_TRANSACTION_ID_1_BATCH_1)
        self.assertEqual(response['transactions'][1].transactionId, MOCK_TRANSACTION_ID_1_BATCH_2)

        # now fetch the remaining results
        response = test_purchase_client.get_settled_transactions(
            compact='aslp',
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-02T00:00:00Z',
            transaction_limit=2,
            last_processed_transaction_id=response['lastProcessedTransactionId'],
            current_batch_id=response['currentBatchId'],
            processed_batch_ids=response['processedBatchIds'],
        )

        # Verify no pagination info is returned
        self.assertNotIn('lastProcessedTransactionId', response)
        self.assertNotIn('currentBatchId', response)

        # assert that the second transaction is returned, the first being skipped
        self.assertEqual([MOCK_BATCH_ID, MOCK_BATCH_ID_2], response['processedBatchIds'])
        self.assertEqual(1, len(response['transactions']))
        self.assertEqual(MOCK_TRANSACTION_ID_2_BATCH_2, response['transactions'][0].transactionId)

    @patch('purchase_client.getSettledBatchListController')
    def test_purchase_client_handles_no_batches_for_settled_transactions(self, mock_batch_controller):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()

        # Return empty batch list
        mock_response = json_to_magic_mock(
            {
                'messages': {
                    'resultCode': SUCCESSFUL_RESULT_CODE,
                },
                'batchList': {'batch': []},
            }
        )
        mock_batch_controller.return_value.getresponse.return_value = mock_response

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)
        response = test_purchase_client.get_settled_transactions(
            compact='aslp',
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-02T00:00:00Z',
            transaction_limit=500,
        )

        # Verify empty response is returned when no batches exist
        self.assertEqual(len(response['transactions']), 0)
        self.assertEqual(len(response['processedBatchIds']), 0)

    @patch('purchase_client.getSettledBatchListController')
    @patch('purchase_client.getTransactionListController')
    @patch('purchase_client.getTransactionDetailsController')
    def test_purchase_client_handles_settlement_errors_for_settled_transactions(
        self, mock_details_controller, mock_transaction_controller, mock_batch_controller
    ):
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()

        mock_response = json_to_magic_mock(
            {
                'messages': {
                    'resultCode': SUCCESSFUL_RESULT_CODE,
                },
                'batchList': {
                    'batch': [
                        {
                            'batchId': MOCK_BATCH_ID,
                            'settlementTimeUTC': MOCK_SETTLEMENT_TIME_UTC,
                            'settlementTimeLocal': MOCK_SETTLEMENT_TIME_LOCAL,
                            'settlementState': 'settlementError',
                        }
                    ]
                },
            }
        )
        mock_batch_controller.return_value.getresponse.return_value = mock_response
        self._when_authorize_dot_net_transaction_list_is_failed(mock_transaction_controller)
        self._when_authorize_dot_net_transaction_details_are_failed(mock_details_controller)

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)
        response = test_purchase_client.get_settled_transactions(
            compact='aslp',
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-02T00:00:00Z',
            transaction_limit=500,
        )

        # assert that we return the transaction with the settlement error
        self.assertEqual(1, len(response['transactions']))
        self.assertEqual(MOCK_TRANSACTION_ID, response['transactions'][0].transactionId)
        self.assertEqual(SETTLEMENT_ERROR_STATE, response['transactions'][0].transactionStatus)
        # assert we return a list of failed transaction ids
        self.assertEqual([MOCK_TRANSACTION_ID], response['settlementErrorTransactionIds'])

    @patch('purchase_client.getSettledBatchListController')
    @patch('purchase_client.getTransactionListController')
    @patch('purchase_client.getTransactionDetailsController')
    def test_purchase_client_skips_declined_transactions(
        self, mock_details_controller, mock_transaction_controller, mock_batch_controller
    ):
        """Test that declined transactions are skipped and not included in the results."""
        from purchase_client import PurchaseClient

        mock_secrets_manager_client = self._generate_mock_secrets_manager_client()

        # Set up batch with one batch
        mock_batch_response = json_to_magic_mock(
            {
                'messages': {
                    'resultCode': SUCCESSFUL_RESULT_CODE,
                },
                'batchList': {
                    'batch': [
                        {
                            'batchId': MOCK_BATCH_ID,
                            'settlementTimeUTC': MOCK_SETTLEMENT_TIME_UTC,
                            'settlementTimeLocal': MOCK_SETTLEMENT_TIME_LOCAL,
                            'settlementState': SUCCESSFUL_SETTLED_STATE,
                        }
                    ]
                },
            }
        )
        mock_batch_controller.return_value.getresponse.return_value = mock_batch_response

        # Set up transaction list with two transactions: one declined, one successful
        declined_transaction_id = '999'
        successful_transaction_id = MOCK_TRANSACTION_ID
        mock_transaction_list_response = json_to_magic_mock(
            {
                'messages': {
                    'resultCode': SUCCESSFUL_RESULT_CODE,
                },
                'transactions': {
                    'transaction': [
                        {'transId': declined_transaction_id, 'transactionStatus': 'declined'},
                        {'transId': successful_transaction_id, 'transactionStatus': SUCCESSFUL_SETTLED_STATE},
                    ]
                },
                'totalNumInResultSet': 2,
            }
        )
        mock_transaction_controller.return_value.getresponse.return_value = mock_transaction_list_response

        # Set up transaction details responses: declined first, then successful
        declined_details_response = json_to_magic_mock(
            self._generate_mock_transaction_detail_response(declined_transaction_id, 'declined')
        )
        successful_details_response = json_to_magic_mock(
            self._generate_mock_transaction_detail_response(successful_transaction_id, SUCCESSFUL_SETTLED_STATE)
        )
        mock_details_controller.return_value.getresponse.side_effect = [
            declined_details_response,
            successful_details_response,
        ]

        test_purchase_client = PurchaseClient(secrets_manager_client=mock_secrets_manager_client)
        response = test_purchase_client.get_settled_transactions(
            compact='aslp',
            start_time='2024-01-01T00:00:00Z',
            end_time='2024-01-02T00:00:00Z',
            transaction_limit=500,
        )

        # Verify only the successful transaction is returned (declined one is skipped)
        self.assertEqual(1, len(response['transactions']))
        self.assertEqual(successful_transaction_id, response['transactions'][0].transactionId)
        self.assertEqual(SUCCESSFUL_SETTLED_STATE, response['transactions'][0].transactionStatus)
        # Verify declined transaction is not in the results
        transaction_ids = [tx.transactionId for tx in response['transactions']]
        self.assertNotIn(declined_transaction_id, transaction_ids)
        self.assertIn(successful_transaction_id, transaction_ids)
