import json
from abc import ABC, abstractmethod

from authorizenet import apicontractsv1
from authorizenet.apicontrollers import createTransactionController
from authorizenet.constants import constants

from config import config, logger
from data_model.schema.compact import Compact, CompactFeeType
from data_model.schema.jurisdiction import Jurisdiction, JurisdictionMilitaryDiscountType
from exceptions import CCFailedTransactionException, CCInternalException

AUTHORIZE_DOT_NET_CLIENT_TYPE = "authorize.net"


def _calculate_jurisdiction_fee(jurisdiction: Jurisdiction, user_active_military: bool) -> float:
    """
    Calculate the total cost of a single jurisdiction privilege
    """
    if user_active_military and jurisdiction.militaryDiscount.active:
        if jurisdiction.militaryDiscount.discountType == JurisdictionMilitaryDiscountType.FLAT_RATE:
            total_jurisdiction_fee = jurisdiction.jurisdictionFee - jurisdiction.militaryDiscount.discountAmount
        else:
            raise ValueError(f"Unsupported military discount type: {jurisdiction.militaryDiscount.discountType.value}")
    else:
        total_jurisdiction_fee = jurisdiction.jurisdictionFee

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
    if compact.compactCommissionFee.feeType == CompactFeeType.FLAT_RATE:
        total_compact_fee += compact.compactCommissionFee.feeAmount
    else:
        raise ValueError(f"Unsupported compact fee type: {compact.compactCommissionFee.feeType.value}")

    return total_compact_fee


def _get_total_privilege_cost(compact: Compact, selected_jurisdictions: list[Jurisdiction],
                              user_active_military: bool) -> float:
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
    def process_charge_on_credit_card_for_privilege_purchase(self, order_information: dict,
                                                             compact_configuration: Compact,
                                                             selected_jurisdictions: list[Jurisdiction],
                                                             user_active_military: bool) -> dict:
        """
        Process a charge on a credit card for a list of privileges within a compact.

        :param order_information: A dictionary containing the order information (billing, card, etc.)
        :param compact_configuration: The compact configuration.
        :param selected_jurisdictions: A list of selected jurisdictions to purchase privileges for.
        :param user_active_military: Whether the user is active military.
        """
        pass


class AuthorizeNetPaymentProcessorClient(PaymentProcessorClient):

    def __init__(self, api_login_id: str, transaction_key: str):
        super().__init__(AUTHORIZE_DOT_NET_CLIENT_TYPE)
        self.api_login_id = api_login_id
        self.transaction_key = transaction_key

    def process_charge_on_credit_card_for_privilege_purchase(self, order_information: dict,
                                                             compact_configuration: Compact,
                                                             selected_jurisdictions: list[Jurisdiction],
                                                             user_active_military: bool) -> dict:
        # Create a merchantAuthenticationType object with authentication details
        merchantAuth = apicontractsv1.merchantAuthenticationType()
        merchantAuth.name = self.api_login_id
        merchantAuth.transactionKey = self.transaction_key

        # Create the payment data for a credit card
        creditCard = apicontractsv1.creditCardType()
        creditCard.cardNumber = order_information['card']['number']
        creditCard.expirationDate = order_information['card']['expiration']
        creditCard.cardCode = order_information['card']['code']

        # Add the payment data to a paymentType object
        payment = apicontractsv1.paymentType()
        payment.creditCard = creditCard

        line_items = apicontractsv1.ArrayOfLineItem()
        for jurisdiction in selected_jurisdictions:
            jurisdiction_name_title_case = jurisdiction.jurisdictionName.title()
            privilege_line_item = apicontractsv1.lineItemType()
            privilege_line_item.itemId = f"{compact_configuration.compactName}-{jurisdiction.postalAbbreviation}"
            privilege_line_item.name = f"{jurisdiction_name_title_case} Compact Privilege"
            privilege_line_item.quantity = "1"
            privilege_line_item.unitPrice = _calculate_jurisdiction_fee(jurisdiction, user_active_military)
            if user_active_military and jurisdiction.militaryDiscount.active:
                privilege_line_item.description = (
                        f"Compact Privilege for {jurisdiction_name_title_case} (Military Discount)")
            else:
                privilege_line_item.description = f"Compact Privilege for {jurisdiction_name_title_case}"

            line_items.lineItem.append(privilege_line_item)

        # Add the compact fee to the line items
        compact_fee_line_item = apicontractsv1.lineItemType()
        compact_fee_line_item.itemId = f"{compact_configuration.compactName}-fee"
        compact_fee_line_item.name = f"{compact_configuration.compactName.upper()} Compact Fee"
        compact_fee_line_item.description = "Compact fee applied for each privilege purchased"
        compact_fee_line_item.quantity = len(selected_jurisdictions)
        compact_fee_line_item.unitPrice = _calculate_compact_fee_for_single_jurisdiction(compact_configuration)
        line_items.lineItem.append(compact_fee_line_item)

        # Set the customer's Bill To address
        customerAddress = apicontractsv1.customerAddressType()
        customerAddress.firstName = order_information['billing']['first_name']
        customerAddress.lastName = order_information['billing']['last_name']
        customerAddress.address = \
            f"{order_information['billing']['address']} {order_information['billing'].get('address2', '')}".strip()
        customerAddress.state = order_information['billing']['state']
        customerAddress.zip = order_information['billing']['zip']

        # Add values for transaction settings
        duplicateWindowSetting = apicontractsv1.settingType()
        duplicateWindowSetting.settingName = "duplicateWindow"
        duplicateWindowSetting.settingValue = "180"
        settings = apicontractsv1.ArrayOfSetting()
        settings.setting.append(duplicateWindowSetting)

        # Create a transactionRequestType object and add the previous objects to it.
        transactionrequest = apicontractsv1.transactionRequestType()
        transactionrequest.transactionType = "authCaptureTransaction"
        transactionrequest.amount = _get_total_privilege_cost(compact=compact_configuration,
                                                              selected_jurisdictions=selected_jurisdictions,
                                                              user_active_military=user_active_military)
        transactionrequest.currencyCode = "USD"
        transactionrequest.payment = payment
        transactionrequest.billTo = customerAddress
        transactionrequest.transactionSettings = settings
        transactionrequest.lineItems = line_items
        transactionrequest.taxExempt = True

        # Assemble the complete transaction request
        createtransactionrequest = apicontractsv1.createTransactionRequest()
        createtransactionrequest.merchantAuthentication = merchantAuth
        createtransactionrequest.transactionRequest = transactionrequest
        # Create the controller
        transactionController = createTransactionController(
            createtransactionrequest)

        # set the environment based on the environment we are running in
        if config.environment_name != "prod":
            transactionController.setenvironment(constants.SANDBOX)
        else:
            transactionController.setenvironment(constants.PRODUCTION)

        transactionController.execute()
        response = transactionController.getresponse()

        if response is not None:
            # Check to see if the API request was successfully received and acted upon
            if response.messages.resultCode == "Ok":
                # Since the API request was successful, look for a transaction response
                # and parse it to display the results of authorizing the card
                if hasattr(response.transactionResponse, 'messages'):
                    logger.info('Successfully created transaction',
                                transaction_id=response.transactionResponse.transId,
                                response_code=response.transactionResponse.responseCode,
                                message_code=response.transactionResponse.messages.message[0].code,
                                description=response.transactionResponse.messages.message[0].description
                                )
                else:
                    logger.warning('Failed Transaction.')
                    if hasattr(response.transactionResponse, 'errors'):
                        # Although their API presents this as a list, it seems to only ever have one element
                        # so we only access the first one
                        error_code = response.transactionResponse.errors.error[0].errorCode
                        error_message = response.transactionResponse.errors.error[0].errorText
                        # logging this as a warning, as the transaction itself was likely invalid, but if it occurs
                        # frequently, we may want to investigate further.
                        logger.warning('Authorize.net failed to process transaction.',
                                        error_code=error_code,
                                       error_message=error_message)
                        raise CCFailedTransactionException(
                            f"Failed to process transaction. Error code: {error_code}, Error message: {error_message}")
            # API request wasn't successful
            else:
                if hasattr(response, 'transactionResponse') and hasattr(response.transactionResponse, 'errors'):
                    error_code = response.transactionResponse.errors.error[0].errorCode
                    error_message = response.transactionResponse.errors.error[0].errorText
                    logger.error('API call to authorize.net Failed.',
                                    error_code=error_code,
                                    error_message=error_message)

                else:
                    error_code = response.messages.message[0]['code'].text
                    error_message = response.messages.message[0]['text'].text
                    logger.error('API call to authorize.net Failed.',
                                    error_code=error_code,
                                    error_message=error_message)

                raise CCInternalException("API call to authorize.net failed.")
        else:
            logger.error('No response returned')
            raise CCInternalException("Authorize.net API call failed to return a response.")

        return {"message": "Successfully processed charge"}


class PaymentProcessorClientFactory:
    @staticmethod
    def create_payment_processor_client(credentials: dict) -> PaymentProcessorClient:
        processor_type: str = credentials.get("processor")
        if processor_type.lower() == AUTHORIZE_DOT_NET_CLIENT_TYPE:
            return AuthorizeNetPaymentProcessorClient(
                api_login_id=credentials.get("api_login_id"),
                transaction_key=credentials.get("transaction_key")
            )
        else:
            raise ValueError(f"Unsupported payment processor type: {processor_type}")


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
        self.secrets_manager_client = secrets_manager_client if secrets_manager_client \
            else config.secrets_manager_client


    def _get_compact_payment_processor_client(self, compact_name: str) -> PaymentProcessorClient:
        """
        Get the payment processor credentials for a compact
        """
        secret_name = (f"/compact-connect/env/{config.environment_name}"
                       f"/compact/{compact_name}/credentials/payment-processor")
        secret = self.secrets_manager_client.get_secret_value(SecretId=secret_name)

        return PaymentProcessorClientFactory.create_payment_processor_client(json.loads(secret['SecretString']))


    def process_charge_for_licensee_privileges(self, order_information: dict,
                                               compact_configuration: Compact,
                                               selected_jurisdictions: list[Jurisdiction],
                                               user_active_military: bool) -> dict:
        """
        Process a charge on a credit card for a list of privileges within a compact.

        :param order_information: A dictionary containing the order information (billing, card, etc.)
        :param compact_configuration: The compact configuration.
        :param selected_jurisdictions: A list of selected jurisdictions to purchase privileges for.
        :param user_active_military: Whether the user is active military.
        """
        # get the credentials from secrets_manager for the compact
        payment_processor_client: PaymentProcessorClient = self._get_compact_payment_processor_client(
            compact_configuration.compactName)

        response = payment_processor_client.process_charge_on_credit_card_for_privilege_purchase(
            order_information=order_information,
            compact_configuration=compact_configuration,
            selected_jurisdictions=selected_jurisdictions,
            user_active_military=user_active_military
        )

        return response