import json
from abc import ABC, abstractmethod

from authorizenet import apicontractsv1
from authorizenet.apicontrollers import createTransactionController
from config import config, logger

AUTHORIZE_DOT_NET_CLIENT_TYPE = "authorize.net"


class PaymentProcessorClient(ABC):
    def __init__(self, processor_type: str):
        self.processor_type = processor_type

    @abstractmethod
    def process_charge_on_credit_card_for_privilege_purchase(self, order_information: dict, amount: float):
        pass


class AuthorizeNetPaymentProcessorClient(PaymentProcessorClient):

    def __init__(self, api_login_id: str, transaction_key: str):
        super().__init__(AUTHORIZE_DOT_NET_CLIENT_TYPE)
        self.api_login_id = api_login_id
        self.transaction_key = transaction_key

    def process_charge_on_credit_card_for_privilege_purchase(self, order_information: dict, amount: float):
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

        # Create order information
        # TODO - do we need to track invoice numbers? If so, we need to store this information
        # order = apicontractsv1.orderType()
        # order.invoiceNumber = "10101"
        # order.description = "Golf Shirts"

        # Set the customer's Bill To address
        customerAddress = apicontractsv1.customerAddressType()
        customerAddress.firstName = order_information['billing']['first_name']
        customerAddress.lastName = order_information['billing']['last_name']
        customerAddress.address = order_information['billing']['address']
        customerAddress.state = order_information['billing']['state']
        customerAddress.zip = order_information['billing']['zip']

        # Set the customer's identifying information
        # TODO - Do we need to track customers in authorize.net?
        # customerData = apicontractsv1.customerDataType()
        # customerData.type = "individual"
        # customerData.id = "99999456654"

        # Add values for transaction settings
        duplicateWindowSetting = apicontractsv1.settingType()
        duplicateWindowSetting.settingName = "duplicateWindow"
        duplicateWindowSetting.settingValue = "180"
        settings = apicontractsv1.ArrayOfSetting()
        settings.setting.append(duplicateWindowSetting)

        # Create a transactionRequestType object and add the previous objects to it.
        transactionrequest = apicontractsv1.transactionRequestType()
        transactionrequest.transactionType = "authCaptureTransaction"
        transactionrequest.amount = amount
        transactionrequest.currencyCode = "USD"
        transactionrequest.payment = payment
        transactionrequest.billTo = customerAddress
        transactionrequest.transactionSettings = settings
        # transactionrequest.order = order
        # transactionrequest.customer = customerData

        # Assemble the complete transaction request
        createtransactionrequest = apicontractsv1.createTransactionRequest()
        createtransactionrequest.merchantAuthentication = merchantAuth
        createtransactionrequest.transactionRequest = transactionrequest
        # Create the controller
        transactionController = createTransactionController(
            createtransactionrequest)
        transactionController.execute()

        response = transactionController.getresponse()

        if response is not None:
            # Check to see if the API request was successfully received and acted upon
            if response.messages.resultCode == "Ok":
                # Since the API request was successful, look for a transaction response
                # and parse it to display the results of authorizing the card
                if hasattr(response.transactionResponse, 'messages') is True:
                    logger.info('Successfully created transaction',
                                transaction_id=response.transactionResponse.transId,
                                response_code=response.transactionResponse.responseCode,
                                message_code=response.transactionResponse.messages.message[0].code,
                                description=response.transactionResponse.messages.message[0].description
                                )
                else:
                    logger.warning('Failed Transaction.')
                    if hasattr(response.transactionResponse, 'errors') is True:
                        print('Error Code:  %s' % str(response.transactionResponse.
                                                      errors.error[0].errorCode))
                        print(
                            'Error message: %s' %
                            response.transactionResponse.errors.error[0].errorText)
            # Or, print errors if the API request wasn't successful
            else:
                logger.error('Failed Transaction API Call')
                if hasattr(response, 'transactionResponse') is True and hasattr(
                        response.transactionResponse, 'errors') is True:
                    print('Error Code: %s' % str(
                        response.transactionResponse.errors.error[0].errorCode))
                    print('Error message: %s' %
                          response.transactionResponse.errors.error[0].errorText)
                else:
                    print('Error Code: %s' %
                          response.messages.message[0]['code'].text)
                    print('Error message: %s' %
                          response.messages.message[0]['text'].text)
        else:
            logger.error('No response returned')
            raise ValueError('No response returned')

        return response


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


    def process_charge_for_licensee_privileges(self, user_compact: str, order_information: dict):
        """
        Charge a credit card
        """
        # get the credentials from secrets_manager for the compact
        payment_processor_client: PaymentProcessorClient = self._get_compact_payment_processor_client(user_compact)

        payment_processor_client.process_charge_on_credit_card_for_privilege_purchase(
            order_information=order_information,
            amount=order_information['amount'])



