import json
from abc import ABC, abstractmethod

from authorizenet import apicontractsv1
from authorizenet.apicontrollers import createTransactionController, getMerchantDetailsController
from authorizenet.constants import constants
from cc_common.config import config, logger
from cc_common.data_model.schema.compact import Compact, CompactFeeType
from cc_common.data_model.schema.jurisdiction import Jurisdiction, JurisdictionMilitaryDiscountType
from cc_common.exceptions import CCFailedTransactionException, CCInternalException, CCInvalidRequestException

AUTHORIZE_DOT_NET_CLIENT_TYPE = 'authorize.net'


def _calculate_jurisdiction_fee(jurisdiction: Jurisdiction, user_active_military: bool) -> float:
    """
    Calculate the total cost of a single jurisdiction privilege
    """
    if user_active_military and jurisdiction.military_discount.active:
        if jurisdiction.military_discount.discount_type == JurisdictionMilitaryDiscountType.FLAT_RATE:
            total_jurisdiction_fee = jurisdiction.jurisdiction_fee - jurisdiction.military_discount.discount_amount
        else:
            raise ValueError(
                'Unsupported military discount type: ' f'{jurisdiction.military_discount.discount_type.value}'
            )
    else:
        total_jurisdiction_fee = jurisdiction.jurisdiction_fee

    return total_jurisdiction_fee


def _calculate_total_compact_fee(compact: Compact, selected_jurisdictions: list[Jurisdiction]) -> float:
    """
    Calculate the total compact fee for all selected jurisdictions

    There is potential that the compact fee may change depending on the jurisdiction (ie percentage based fees),
    but for now we are assuming that the fee is the same for all jurisdictions.
    """
    return _calculate_compact_fee_for_single_jurisdiction(compact) * len(selected_jurisdictions)


def _calculate_compact_fee_for_single_jurisdiction(compact: Compact) -> float:
    total_compact_fee = 0.0
    if compact.compact_commission_fee.fee_type == CompactFeeType.FLAT_RATE:
        total_compact_fee += compact.compact_commission_fee.fee_amount
    else:
        raise ValueError(f'Unsupported compact fee type: {compact.compact_commission_fee.fee_type.value}')

    return total_compact_fee


def _get_total_privilege_cost(
    compact: Compact, selected_jurisdictions: list[Jurisdiction], user_active_military: bool
) -> float:
    """
    Calculate the total cost of all privileges.

    This cost includes the jurisdiction fee for each jurisdiction, as well as the compact fee.
    """
    total_cost = 0.0
    for jurisdiction in selected_jurisdictions:
        total_cost += _calculate_jurisdiction_fee(jurisdiction, user_active_military)

    total_cost += _calculate_total_compact_fee(compact, selected_jurisdictions)

    return total_cost


class PaymentProcessorClient(ABC):
    def __init__(self, processor_type: str):
        self.processor_type = processor_type

    @abstractmethod
    def process_charge_on_credit_card_for_privilege_purchase(
        self,
        licensee_id: str,
        order_information: dict,
        compact_configuration: Compact,
        selected_jurisdictions: list[Jurisdiction],
        user_active_military: bool,
    ) -> dict:
        """
        Process a charge on a credit card for a list of privileges within a compact.

        :param licensee_id: The user ID of the Licensee for whom the privileges are being purchased.
        :param order_information: A dictionary containing the order information (billing, card, etc.)
        :param compact_configuration: The compact configuration.
        :param selected_jurisdictions: A list of selected jurisdictions to purchase privileges for.
        :param user_active_military: Whether the user is active military.
        """

    @abstractmethod
    def void_unsettled_charge_on_credit_card(
        self,
        order_information: dict,
    ) -> dict:
        """
        Void a charge on a credit card for an unsettled transaction.

        :param order_information: A dictionary containing the order information (transactionId, etc.)
        """

    @abstractmethod
    def validate_credentials(self) -> dict:
        """
        Verify that the provided credentials are valid.
        """


class AuthorizeNetPaymentProcessorClient(PaymentProcessorClient):
    def __init__(self, api_login_id: str, transaction_key: str):
        super().__init__(AUTHORIZE_DOT_NET_CLIENT_TYPE)
        self.api_login_id = api_login_id
        self.transaction_key = transaction_key

    def _handle_api_error(self, response: apicontractsv1.transactionResponse) -> None:
        logger_message = 'API call to authorize.net Failed.'
        if hasattr(response, 'transactionResponse') and hasattr(response.transactionResponse, 'errors'):
            error_code = response.transactionResponse.errors.error[0].errorCode
            error_message = response.transactionResponse.errors.error[0].errorText
            logger.error(logger_message, error_code=error_code, error_message=error_message)

        else:
            error_code = response.messages.message[0]['code'].text
            error_message = response.messages.message[0]['text'].text
            logger.error(logger_message, error_code=error_code, error_message=error_message)

        raise CCInternalException(logger_message)

    def void_unsettled_charge_on_credit_card(
        self,
        order_information: dict,
    ) -> dict:
        merchant_auth = apicontractsv1.merchantAuthenticationType()
        merchant_auth.name = self.api_login_id
        merchant_auth.transactionKey = self.transaction_key

        transaction_request = apicontractsv1.transactionRequestType()
        transaction_request.transactionType = 'voidTransaction'
        # set refTransId to transId of an unsettled transaction
        transaction_request.refTransId = order_information['transactionId']

        create_transaction_request = apicontractsv1.createTransactionRequest()
        create_transaction_request.merchantAuthentication = merchant_auth

        create_transaction_request.transactionRequest = transaction_request
        transaction_controller = createTransactionController(create_transaction_request)

        # set the environment based on the environment we are running in
        if config.environment_name != 'prod':
            transaction_controller.setenvironment(constants.SANDBOX)
        else:
            transaction_controller.setenvironment(constants.PRODUCTION)

        transaction_controller.execute()
        response = transaction_controller.getresponse()

        if response is not None:
            if response.messages.resultCode == 'Ok':
                if hasattr(response.transactionResponse, 'messages'):
                    logger.info(
                        'Successfully voided transaction',
                        transaction_id=response.transactionResponse.transId,
                        response_code=response.transactionResponse.responseCode,
                        message_code=response.transactionResponse.messages.message[0].code,
                        description=response.transactionResponse.messages.message[0].description,
                    )
                    return {
                        'message': 'Successfully voided transaction',
                        # their SDK returns the transaction id as an internal IntElement type, so we need to cast it
                        # or this will cause an error when we try to serialize it to JSON
                        'transactionId': str(response.transactionResponse.transId),
                    }
                error_code = response.transactionResponse.errors.error[0].errorCode
                error_message = response.transactionResponse.errors.error[0].errorText
                # logging this as an error, since we control the transaction id that is passed in, so this should
                # raise an alert if it occurs.
                logger.error(
                    'Failed to void transaction.',
                    transaction_id=order_information['transactionId'],
                    error_code=error_code,
                    error_message=error_message,
                )

                raise CCFailedTransactionException(
                    f'Failed to void transaction. Error code: {error_code}, Error message: {error_message}'
                )

        self._handle_api_error(response)  # noqa: RET503 this branch raises an exception

    def process_charge_on_credit_card_for_privilege_purchase(
        self,
        licensee_id: str,
        order_information: dict,
        compact_configuration: Compact,
        selected_jurisdictions: list[Jurisdiction],
        user_active_military: bool,
    ) -> dict:
        # Create a merchantAuthenticationType object with authentication details
        merchant_auth = apicontractsv1.merchantAuthenticationType()
        merchant_auth.name = self.api_login_id
        merchant_auth.transactionKey = self.transaction_key

        # Create the payment data for a credit card
        credit_card = apicontractsv1.creditCardType()
        credit_card.cardNumber = order_information['card']['number']
        credit_card.expirationDate = order_information['card']['expiration']
        credit_card.cardCode = order_information['card']['cvv']

        # Add the payment data to a paymentType object
        payment = apicontractsv1.paymentType()
        payment.creditCard = credit_card

        # Create order information
        order = apicontractsv1.orderType()
        # We store the LICENSEE ID in the description field, since the ID is a UUID that is 36 characters long
        # and this is the only field that can store that length of data. The description field can hold up to 255
        # characters.
        order.description = json.dumps({'LICENSEE': licensee_id})

        line_items = apicontractsv1.ArrayOfLineItem()
        for jurisdiction in selected_jurisdictions:
            jurisdiction_name_title_case = jurisdiction.jurisdiction_name.title()
            privilege_line_item = apicontractsv1.lineItemType()
            privilege_line_item.itemId = f'{compact_configuration.compact_name}-{jurisdiction.postal_abbreviation}'
            privilege_line_item.name = f'{jurisdiction_name_title_case} Compact Privilege'
            privilege_line_item.quantity = '1'
            privilege_line_item.unitPrice = _calculate_jurisdiction_fee(jurisdiction, user_active_military)
            if user_active_military and jurisdiction.military_discount.active:
                privilege_line_item.description = (
                    f'Compact Privilege for {jurisdiction_name_title_case} (Military Discount)'
                )
            else:
                privilege_line_item.description = f'Compact Privilege for {jurisdiction_name_title_case}'

            line_items.lineItem.append(privilege_line_item)

        # Add the compact fee to the line items
        compact_fee_line_item = apicontractsv1.lineItemType()
        compact_fee_line_item.itemId = f'{compact_configuration.compact_name}-compact-fee'
        compact_fee_line_item.name = f'{compact_configuration.compact_name.upper()} Compact Fee'
        compact_fee_line_item.description = 'Compact fee applied for each privilege purchased'
        compact_fee_line_item.quantity = len(selected_jurisdictions)
        compact_fee_line_item.unitPrice = _calculate_compact_fee_for_single_jurisdiction(compact_configuration)
        line_items.lineItem.append(compact_fee_line_item)

        # Set the customer's Bill To address
        customer_address = apicontractsv1.customerAddressType()
        customer_address.firstName = order_information['billing']['firstName']
        customer_address.lastName = order_information['billing']['lastName']
        customer_address.address = (
            f"{order_information['billing']['streetAddress']}"
            f" {order_information['billing'].get('streetAddress2', '')}"
        ).strip()
        customer_address.state = order_information['billing']['state']
        customer_address.zip = order_information['billing']['zip']

        # Add values for transaction settings
        duplicate_window_setting = apicontractsv1.settingType()
        duplicate_window_setting.settingName = 'duplicateWindow'
        duplicate_window_setting.settingValue = '180'
        settings = apicontractsv1.ArrayOfSetting()
        settings.setting.append(duplicate_window_setting)

        # Create a transactionRequestType object and add the previous objects to it.
        transaction_request = apicontractsv1.transactionRequestType()
        transaction_request.transactionType = 'authCaptureTransaction'
        transaction_request.amount = _get_total_privilege_cost(
            compact=compact_configuration,
            selected_jurisdictions=selected_jurisdictions,
            user_active_military=user_active_military,
        )
        transaction_request.currencyCode = 'USD'
        transaction_request.payment = payment
        transaction_request.billTo = customer_address
        transaction_request.transactionSettings = settings
        transaction_request.order = order
        transaction_request.lineItems = line_items
        transaction_request.taxExempt = True

        # Assemble the complete transaction request
        create_transaction_request = apicontractsv1.createTransactionRequest()
        create_transaction_request.merchantAuthentication = merchant_auth
        create_transaction_request.transactionRequest = transaction_request
        # Create the controller
        transaction_controller = createTransactionController(create_transaction_request)

        # set the environment based on the environment we are running in
        if config.environment_name != 'prod':
            transaction_controller.setenvironment(constants.SANDBOX)
        else:
            transaction_controller.setenvironment(constants.PRODUCTION)

        transaction_controller.execute()
        response = transaction_controller.getresponse()

        if response is not None:
            # Check to see if the API request was successfully received and acted upon
            if response.messages.resultCode == 'Ok':
                # Since the API request was successful, look for a transaction response
                # and parse it to display the results of authorizing the card
                if hasattr(response.transactionResponse, 'messages'):
                    logger.info(
                        'Successfully created transaction',
                        transaction_id=response.transactionResponse.transId,
                        response_code=response.transactionResponse.responseCode,
                        message_code=response.transactionResponse.messages.message[0].code,
                        description=response.transactionResponse.messages.message[0].description,
                    )
                    return {
                        'message': 'Successfully processed charge',
                        # their SDK returns the transaction id as an internal IntElement type, so we need to cast it
                        # or this will cause an error when we try to serialize it to JSON
                        'transactionId': str(response.transactionResponse.transId),
                    }
                logger.warning('Failed Transaction.')
                if hasattr(response.transactionResponse, 'errors'):  # noqa: RET503 this branch raises an exception
                    # Although their API presents this as a list, it seems to only ever have one element
                    # so we only access the first one
                    error_code = response.transactionResponse.errors.error[0].errorCode
                    error_message = response.transactionResponse.errors.error[0].errorText
                    # logging this as a warning, as the transaction itself was likely invalid, but if it occurs
                    # frequently, we may want to investigate further.
                    logger.warning(
                        'Authorize.net failed to process transaction.',
                        error_code=error_code,
                        error_message=error_message,
                    )
                    raise CCFailedTransactionException(
                        f'Failed to process transaction. Error code: {error_code}, Error message: {error_message}'
                    )
        # API request wasn't successful
        self._handle_api_error(response)  # noqa: RET503 this branch raises an exception

    def validate_credentials(self) -> dict:
        """
        Verify that the credentials the client was constructed with are valid.

        :raises CCInvalidRequestException: If the credentials are invalid.
        """
        merchant_auth = apicontractsv1.merchantAuthenticationType()
        merchant_auth.name = self.api_login_id
        merchant_auth.transactionKey = self.transaction_key

        # Assemble the get merchant details request
        get_merchant_detail_request = apicontractsv1.getMerchantDetailsRequest()
        get_merchant_detail_request.merchantAuthentication = merchant_auth

        # Create the controller
        get_merchant_details_controller = getMerchantDetailsController(get_merchant_detail_request)

        # set the environment based on the environment we are running in
        if config.environment_name != 'prod':
            get_merchant_details_controller.setenvironment(constants.SANDBOX)
        else:
            get_merchant_details_controller.setenvironment(constants.PRODUCTION)

        get_merchant_details_controller.execute()
        response = get_merchant_details_controller.getresponse()

        if response is None:
            raise CCInvalidRequestException('Failed to verify credentials')

        if response.messages.resultCode == 'Ok' and hasattr(response.messages, 'message'):
            logger.info(
                'Successfully verified credentials',
                message_code=response.messages.message[0].code,
                message_text=response.messages.message[0].text,
            )
            return {'message': 'Successfully verified credentials'}

        logger_message = 'Failed to verify credentials.'
        error_code = response.messages.message[0]['code'].text
        error_message = response.messages.message[0]['text'].text
        # logging this as a warning, as the credentials were likely invalid, but if it occurs
        # frequently, we may want to investigate further.
        logger.warning(logger_message, error_code=error_code, error_message=error_message)

        raise CCInvalidRequestException(f'{logger_message} Error code: {error_code}, Error message: {error_message}')


class PaymentProcessorClientFactory:
    @staticmethod
    def create_payment_processor_client(credentials: dict) -> PaymentProcessorClient:
        processor_type: str = credentials.get('processor')
        if processor_type.lower() == AUTHORIZE_DOT_NET_CLIENT_TYPE:
            return AuthorizeNetPaymentProcessorClient(
                api_login_id=credentials.get('api_login_id'), transaction_key=credentials.get('transaction_key')
            )
        raise ValueError(f'Unsupported payment processor type: {processor_type}')


class PurchaseClient:
    """
    This class abstracts the logic for purchase transactions.

    Each compact is responsible for storing its own payment processor credentials.
    The credentials are stored by a separate endpoint that Compact Admins can call.
    The credentials are stored in AWS secrets manager, under the following namespace:

    /compact-connect/env/<env>/compact/<compact>/credentials/payment-processor

    The secret is a JSON string that contains the following fields:
    {
        "processor": "authorize.net", # The payment processor to use, only authorize.net is supported
        "api_login_id": "<api_login_id>", # required for authorize.net transactions
        "transaction_key": "<transaction_key>", # required for authorize.net transactions
    }

    This class uses the payment processor credentials to create a transaction with the payment processor.
    """

    def __init__(self, secrets_manager_client=None):
        """
        Initialize the PurchaseClient with a secrets manager client to allow IOC for testing
        """
        self.secrets_manager_client = (
            secrets_manager_client if secrets_manager_client else config.secrets_manager_client
        )
        # this will be initialized when a transaction is processed
        self.payment_processor_client = None

    def _get_payment_processor_secret_name_for_compact(self, compact_name: str) -> str:
        return f'compact-connect/env/{config.environment_name}/compact/{compact_name}/credentials/payment-processor'

    def _get_compact_payment_processor_client(self, compact_name: str) -> PaymentProcessorClient:
        """
        Get the payment processor credentials for a compact
        """
        secret_name = self._get_payment_processor_secret_name_for_compact(compact_name)
        secret = self.secrets_manager_client.get_secret_value(SecretId=secret_name)

        return PaymentProcessorClientFactory.create_payment_processor_client(json.loads(secret['SecretString']))

    def process_charge_for_licensee_privileges(
        self,
        licensee_id: str,
        order_information: dict,
        compact_configuration: Compact,
        selected_jurisdictions: list[Jurisdiction],
        user_active_military: bool,
    ) -> dict:
        """
        Process a charge on a credit card for a list of privileges within a compact.

        :param licensee_id: The Licensee user ID.
        :param order_information: A dictionary containing the order information (billing, card, etc.)
        :param compact_configuration: The compact configuration.
        :param selected_jurisdictions: A list of selected jurisdictions to purchase privileges for.
        :param user_active_military: Whether the user is active military.
        """
        if not self.payment_processor_client:
            # get the credentials from secrets_manager for the compact
            self.payment_processor_client: PaymentProcessorClient = self._get_compact_payment_processor_client(
                compact_configuration.compact_name
            )

        return self.payment_processor_client.process_charge_on_credit_card_for_privilege_purchase(
            licensee_id=licensee_id,
            order_information=order_information,
            compact_configuration=compact_configuration,
            selected_jurisdictions=selected_jurisdictions,
            user_active_military=user_active_military,
        )

    def void_privilege_purchase_transaction(self, compact_name: str, order_information: dict) -> dict:
        """
        Void a charge on an unsettled credit card.

        :param compact_name: The name of the compact
        :param order_information: A dictionary containing the order information (billing, card, etc.)
        """
        if not self.payment_processor_client:
            # get the credentials from secrets_manager for the compact
            self.payment_processor_client: PaymentProcessorClient = self._get_compact_payment_processor_client(
                compact_name
            )

        return self.payment_processor_client.void_unsettled_charge_on_credit_card(order_information=order_information)

    def validate_and_store_credentials(self, compact_name: str, credentials: dict) -> dict:
        """
        Validate the provided payment credentials and store them in secrets manager.

        :param compact_name: The name of the compact
        :param credentials: The payment processor credentials
        :return: A response indicating the credentials were validated and stored successfully
        :raises CCInvalidRequestException: If the credentials are invalid
        """
        if credentials['processor'] != AUTHORIZE_DOT_NET_CLIENT_TYPE:
            raise CCInvalidRequestException('Invalid payment processor')

        # call payment processor test endpoint to validate the credentials
        # if the credentials are invalid, authorize.net will return an error response
        secret_value = {
            'processor': credentials['processor'],
            'api_login_id': credentials['apiLoginId'],
            'transaction_key': credentials['transactionKey'],
        }
        # this will raise an exception if the credentials are invalid
        response = PaymentProcessorClientFactory().create_payment_processor_client(secret_value).validate_credentials()

        # no exceptions were raised, so the credentials are valid
        # first check to see if secret already exists
        try:
            self.secrets_manager_client.describe_secret(
                SecretId=self._get_payment_processor_secret_name_for_compact(compact_name)
            )

            # secret exists, update its value to whatever the admin sent us
            logger.info('Existing secret found, updating secret for compact', compact_name=compact_name)
            self.secrets_manager_client.put_secret_value(
                SecretId=self._get_payment_processor_secret_name_for_compact(compact_name),
                SecretString=json.dumps(secret_value),
            )
        except self.secrets_manager_client.exceptions.ResourceNotFoundException:
            # secret does not exist, so we can create it
            logger.info('Existing secret not found, creating new secret for compact', compact_name=compact_name)
            self.secrets_manager_client.create_secret(
                Name=self._get_payment_processor_secret_name_for_compact(compact_name),
                SecretString=json.dumps(secret_value),
            )

        return response
