import json
import logging
from abc import ABC, abstractmethod
from decimal import Decimal

from authorizenet import apicontractsv1
from authorizenet.apicontrollers import (
    createTransactionController,
    getMerchantDetailsController,
    getSettledBatchListController,
    getTransactionDetailsController,
    getTransactionListController,
)
from authorizenet.constants import constants
from cc_common.config import config, logger
from cc_common.data_model.schema.compact import Compact
from cc_common.data_model.schema.compact.common import CompactFeeType, PaymentProcessorType, TransactionFeeChargeType
from cc_common.data_model.schema.jurisdiction import Jurisdiction
from cc_common.exceptions import (
    CCFailedTransactionException,
    CCInternalException,
    CCInvalidRequestException,
    CCNotFoundException,
)

OK_TRANSACTION_MESSAGE_RESULT_CODE = 'Ok'
MAXIMUM_TRANSACTION_API_LIMIT = 1000

# Authorize.net does not have a clear way to distinguish between an error that is caused by an issue with the card
# information passed in by the user, and an internal issue caused by the API itself. To account for this, we
# pulled the list of known issues from their transaction response code lookup and put the list of error codes that are
# likely caused by the user. These include issues such as an invalid or unsupported card number, the expiration date
# being expired, or the card being declined. You can review the description of these codes by searching for them at
# https://developer.authorize.net/api/reference/responseCodes.html
AUTHORIZE_NET_CARD_USER_ERROR_CODES = ['2', '5', '6', '7', '8', '11', '17', '65']

# The authorizenet SDK emits many warnings due to a Pyxb issue that they will not address,
# see https://github.com/AuthorizeNet/sdk-python/issues/133,
# so we are ignoring warnings to reduce noise in our logging
logging.getLogger('pyxb.binding.content').setLevel(logging.ERROR)


# We also want to ignore a specific 'error' message from them that does not actually impact the system
# see https://github.com/AuthorizeNet/sdk-python/issues/109
class IgnoreContentNondeterminismFilter(logging.Filter):
    def filter(self, record):
        return 'ContentNondeterminismExceededError' not in record.getMessage()


logging.getLogger('authorizenet.sdk').addFilter(IgnoreContentNondeterminismFilter())


def _calculate_jurisdiction_fee(
    jurisdiction: Jurisdiction, license_type_abbr: str, user_active_military: bool
) -> Decimal:
    """
    Calculate the total cost of a single jurisdiction privilege

    :param jurisdiction: The jurisdiction to calculate the fee for
    :param license_type_abbr: The abbreviation of the license type
    :param user_active_military: Whether the user has an active military affiliation

    :return: The calculated fee amount for the given license type and jurisdiction
    """

    # Find the fee for the specified license type
    license_fee = next(
        (fee for fee in jurisdiction.privilege_fees if fee.license_type_abbreviation == license_type_abbr), None
    )

    if not license_fee:
        logger.info(
            'Unable to find license fee for specified license type',
            jurisdiction=jurisdiction.postal_abbreviation,
            license_type=license_type_abbr,
            compact=jurisdiction.compact,
        )
        raise ValueError(f'No license fee found for license type: {license_type_abbr}')

    # If user is active military and the license fee has a military rate, use that rate
    if user_active_military and license_fee.military_rate is not None:
        return license_fee.military_rate

    # Otherwise use the standard fee
    return license_fee.amount


def _calculate_total_compact_fee(compact: Compact, selected_jurisdictions: list[Jurisdiction]) -> Decimal:
    """
    Calculate the total compact fee for all selected jurisdictions

    There is potential that the compact fee may change depending on the jurisdiction (ie percentage based fees),
    but for now we are assuming that the fee is the same for all jurisdictions.
    """
    return _calculate_compact_fee_for_single_jurisdiction(compact) * len(selected_jurisdictions)


def _compact_is_charging_licensee_for_transaction_fees(compact: Compact) -> bool:
    return (
        compact.transaction_fee_configuration is not None
        and compact.transaction_fee_configuration.licensee_charges is not None
        and compact.transaction_fee_configuration.licensee_charges.active
    )


def _calculate_transaction_fee(compact: Compact, num_privileges: int) -> Decimal:
    """
    Calculate the transaction fee based on the compact's licensee charges configuration.
    Returns 0 if licensee charges are not configured or not active.
    """
    if _compact_is_charging_licensee_for_transaction_fees(compact):
        if (
            compact.transaction_fee_configuration.licensee_charges.charge_type
            == TransactionFeeChargeType.FLAT_FEE_PER_PRIVILEGE
        ):
            return compact.transaction_fee_configuration.licensee_charges.charge_amount * Decimal(num_privileges)
        raise ValueError(
            f'Unsupported transaction fee charge type: '
            f'{compact.transaction_fee_configuration.licensee_charges.charge_type.value}'
        )
    return Decimal(0)


def _calculate_compact_fee_for_single_jurisdiction(compact: Compact) -> Decimal:
    total_compact_fee = Decimal(0)
    if compact.compact_commission_fee.fee_type == CompactFeeType.FLAT_RATE:
        total_compact_fee += compact.compact_commission_fee.fee_amount
    else:
        raise ValueError(f'Unsupported compact fee type: {compact.compact_commission_fee.fee_type.value}')

    return total_compact_fee


def _get_total_privilege_cost(
    compact: Compact,
    selected_jurisdictions: list[Jurisdiction],
    user_active_military: bool,
    license_type_abbreviation: str,
) -> Decimal:
    """
    Calculate the total cost of all privileges.

    This cost includes the jurisdiction fee for each jurisdiction, the compact fee, and any transaction fees.

    :param compact: The compact configuration
    :param selected_jurisdictions: List of jurisdictions to calculate costs for
    :param user_active_military: Whether the user has an active military affiliation
    :param license_type_abbreviation: The abbreviation of the license type

    :return: The total cost for all privileges
    """
    total_cost = Decimal(0.0)
    for jurisdiction in selected_jurisdictions:
        total_cost += _calculate_jurisdiction_fee(
            jurisdiction=jurisdiction,
            license_type_abbr=license_type_abbreviation,
            user_active_military=user_active_military,
        )

    total_cost += _calculate_total_compact_fee(compact, selected_jurisdictions)
    total_cost += _calculate_transaction_fee(compact, len(selected_jurisdictions))

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
        license_type_abbreviation: str,
        user_active_military: bool,
    ) -> dict:
        """
        Process a charge on a credit card for a list of privileges within a compact.

        :param licensee_id: The user ID of the Licensee for whom the privileges are being purchased.
        :param order_information: A dictionary containing the order information (billing, card, etc.)
        :param compact_configuration: The compact configuration.
        :param selected_jurisdictions: A list of selected jurisdictions to purchase privileges for.
        :param license_type_abbreviation: The license type abbreviation used to generate line item id.
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

    @abstractmethod
    def get_settled_transactions(
        self,
        start_time: str,
        end_time: str,
        transaction_limit: int,
        last_processed_transaction_id: str = None,
        current_batch_id: str = None,
        processed_batch_ids: list[str] = None,
    ) -> dict:
        """
        Get settled transactions from the payment processor.

        :param start_time: UTC timestamp string for start of range
        :param end_time: UTC timestamp string for end of range
        :param transaction_limit: Maximum number of transactions to return
        :param last_processed_transaction_id: Optional last processed transaction ID for pagination
        :param current_batch_id: Optional current batch ID being processed
        :param processed_batch_ids: Optional list of batch IDs that have already been processed
        :return: Dictionary containing transaction details and optional pagination info
        """


class AuthorizeNetPaymentProcessorClient(PaymentProcessorClient):
    def __init__(self, api_login_id: str, transaction_key: str):
        super().__init__(PaymentProcessorType.AUTHORIZE_DOT_NET_TYPE)
        self.api_login_id = api_login_id
        self.transaction_key = transaction_key

    def _handle_api_error(self, response: apicontractsv1.transactionResponse) -> None:
        logger_message = 'API call to authorize.net Failed.'
        if hasattr(response, 'transactionResponse') and hasattr(response.transactionResponse, 'errors'):
            error_code = response.transactionResponse.errors.error[0].errorCode
            error_message = response.transactionResponse.errors.error[0].errorText
            if str(error_code) in AUTHORIZE_NET_CARD_USER_ERROR_CODES:
                logger.warning(
                    logger_message, transaction_error_code=error_code, transaction_error_message=error_message
                )
                raise CCInvalidRequestException(
                    f'Failed to process transaction. Error code: {error_code}, Error message: {error_message}'
                )
            logger.error(logger_message, transaction_error_code=error_code, transaction_error_message=error_message)

        else:
            error_code = response.messages.message[0]['code'].text
            error_message = response.messages.message[0]['text'].text
            if error_code in AUTHORIZE_NET_CARD_USER_ERROR_CODES:
                logger.warning(
                    logger_message, transaction_error_code=error_code, transaction_error_message=error_message
                )
                raise CCInvalidRequestException(
                    f'Failed to process transaction. Error code: {error_code}, Error message: {error_message}'
                )

            logger.error(logger_message, error_code=error_code, error_message=error_message)
            raise CCInternalException(logger_message)

    def void_unsettled_charge_on_credit_card(  # noqa: RET503 this branch raises an exception
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

        self._handle_api_error(response)

    def process_charge_on_credit_card_for_privilege_purchase(  # noqa: RET503 this branch raises an exception
        self,
        licensee_id: str,
        order_information: dict,
        compact_configuration: Compact,
        selected_jurisdictions: list[Jurisdiction],
        license_type_abbreviation: str,
        user_active_military: bool,
    ) -> dict:
        # Create a merchantAuthenticationType object with authentication details
        merchant_auth = apicontractsv1.merchantAuthenticationType()
        merchant_auth.name = self.api_login_id
        merchant_auth.transactionKey = self.transaction_key

        # Create the payment data using opaqueData (Accept.js payment nonce)
        opaque_data = apicontractsv1.opaqueDataType()
        opaque_data.dataDescriptor = order_information['opaqueData']['dataDescriptor']
        opaque_data.dataValue = order_information['opaqueData']['dataValue']

        # Add the payment data to a paymentType object
        payment = apicontractsv1.paymentType()
        payment.opaqueData = opaque_data

        # Create order information
        order = apicontractsv1.orderType()
        # We store the LICENSEE ID in the description field, since the ID is a UUID that is 36 characters long
        # and this is the only field that can store that length of data. The description field can hold up to 255
        # characters.
        # We initially debated storing this as a JSON serialized string, but the authorize.net api strips the {} from
        # the object, so we are using this format.
        order.description = f'LICENSEE#{licensee_id}#'

        line_items = apicontractsv1.ArrayOfLineItem()
        for jurisdiction in selected_jurisdictions:
            jurisdiction_name_title_case = jurisdiction.jurisdiction_name.title()
            privilege_line_item = apicontractsv1.lineItemType()
            privilege_line_item.itemId = f'priv:{compact_configuration.compact_abbr}-{jurisdiction.postal_abbreviation}-{license_type_abbreviation}'  # noqa: E501
            privilege_line_item.name = f'{jurisdiction_name_title_case} Compact Privilege'
            privilege_line_item.quantity = '1'
            privilege_line_item.unitPrice = _calculate_jurisdiction_fee(
                jurisdiction=jurisdiction,
                license_type_abbr=license_type_abbreviation,
                user_active_military=user_active_military,
            )

            # Set the description based on whether the user is active military and has a military rate
            if (
                user_active_military
                and (
                    license_fee := next(
                        (
                            fee
                            for fee in jurisdiction.privilege_fees
                            if fee.license_type_abbreviation == license_type_abbreviation
                        ),
                        None,
                    )
                )
                and license_fee.military_rate is not None
            ):
                privilege_line_item.description = (
                    f'Compact Privilege for {jurisdiction_name_title_case} (Military Rate)'
                )
            else:
                privilege_line_item.description = f'Compact Privilege for {jurisdiction_name_title_case}'

            line_items.lineItem.append(privilege_line_item)

        # Add the compact fee to the line items
        compact_fee_line_item = apicontractsv1.lineItemType()
        compact_fee_line_item.itemId = f'{compact_configuration.compact_abbr}-compact-fee'
        compact_fee_line_item.name = f'{compact_configuration.compact_abbr.upper()} Compact Fee'
        compact_fee_line_item.description = 'Compact fee applied for each privilege purchased'
        compact_fee_line_item.quantity = len(selected_jurisdictions)
        compact_fee_line_item.unitPrice = _calculate_compact_fee_for_single_jurisdiction(compact_configuration)
        line_items.lineItem.append(compact_fee_line_item)

        # Add the transaction fee line item if licensee charges are configured and active
        if _compact_is_charging_licensee_for_transaction_fees(compact_configuration):
            transaction_fee_line_item = apicontractsv1.lineItemType()
            transaction_fee_line_item.itemId = 'credit-card-transaction-fee'
            transaction_fee_line_item.name = 'Credit Card Transaction Fee'
            transaction_fee_line_item.description = 'Transaction fee for credit card processing'
            transaction_fee_line_item.quantity = len(selected_jurisdictions)
            # determine the unit price by calculating for a single privilege
            transaction_fee_line_item.unitPrice = _calculate_transaction_fee(compact_configuration, 1)
            line_items.lineItem.append(transaction_fee_line_item)

        # Add values for transaction settings
        duplicate_window_setting = apicontractsv1.settingType()
        duplicate_window_setting.settingName = 'duplicateWindow'
        duplicate_window_setting.settingValue = '35'
        settings = apicontractsv1.ArrayOfSetting()
        settings.setting.append(duplicate_window_setting)

        # Create a transactionRequestType object and add the previous objects to it.
        transaction_request = apicontractsv1.transactionRequestType()
        transaction_request.transactionType = 'authCaptureTransaction'
        transaction_request.amount = _get_total_privilege_cost(
            compact=compact_configuration,
            selected_jurisdictions=selected_jurisdictions,
            user_active_military=user_active_military,
            license_type_abbreviation=license_type_abbreviation,
        )
        transaction_request.currencyCode = 'USD'
        transaction_request.payment = payment
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

                    line_items_list = []
                    if hasattr(line_items, 'lineItem'):
                        for item in line_items.lineItem:
                            line_items_list.append(
                                {
                                    # we must cast these to strings, or they will cause an error when we
                                    # try to serialize in other parts of the system
                                    'itemId': str(item.itemId),
                                    'name': str(item.name),
                                    'description': str(item.description),
                                    'quantity': str(item.quantity),
                                    'unitPrice': str(item.unitPrice),
                                    'taxable': str(item.taxable),
                                }
                            )
                    return {
                        'message': 'Successfully processed charge',
                        'lineItems': line_items_list,
                        # their SDK returns the transaction id as an internal IntElement type, so we need to cast it
                        # or this will cause an error when we try to serialize it to JSON
                        'transactionId': str(response.transactionResponse.transId),
                    }
                logger.warning('Failed Transaction.')
                if hasattr(response.transactionResponse, 'errors'):
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
                    # Provide specific error message for CVV validation failures
                    if str(error_code) == '65':
                        error_message += (
                            ' Please verify that you have entered a valid CVV (security code) for your credit card.'  # noqa: E501
                        )
                    raise CCFailedTransactionException(
                        f'Failed to process transaction. Error code: {error_code}, Error message: {error_message}'
                    )
        # API request wasn't successful
        self._handle_api_error(response)

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
            return {
                'message': 'Successfully verified credentials',
                'publicClientKey': str(response.publicClientKey),
                'apiLoginId': self.api_login_id,
            }

        logger_message = 'Failed to verify credentials.'
        error_code = response.messages.message[0]['code'].text
        error_message = response.messages.message[0]['text'].text
        # logging this as a warning, as the credentials were likely invalid, but if it occurs
        # frequently, we may want to investigate further.
        logger.warning(logger_message, error_code=error_code, error_message=error_message)

        raise CCInvalidRequestException(f'{logger_message} Error code: {error_code}, Error message: {error_message}')

    def _get_settled_batch_list(self, start_time: str, end_time: str) -> apicontractsv1.getSettledBatchListResponse:
        """
        Get the list of settled batches from the payment processor.

        :param start_time: UTC timestamp string for start of range
        :param end_time: UTC timestamp string for end of range
        :return: Response containing the list of settled batches
        :raises CCInternalException: If the API call fails
        :raises TransactionBatchSettlementFailureException: If any batch has a settlement error
        """
        merchant_auth = apicontractsv1.merchantAuthenticationType()
        merchant_auth.name = self.api_login_id
        merchant_auth.transactionKey = self.transaction_key

        batch_request = apicontractsv1.getSettledBatchListRequest()
        batch_request.merchantAuthentication = merchant_auth
        batch_request.includeStatistics = True
        batch_request.firstSettlementDate = start_time
        batch_request.lastSettlementDate = end_time

        batch_controller = getSettledBatchListController(batch_request)
        if config.environment_name != 'prod':
            batch_controller.setenvironment(constants.SANDBOX)
        else:
            batch_controller.setenvironment(constants.PRODUCTION)

        logger.info('Getting settled batch list for timeframe', start_time=start_time, end_time=end_time)
        batch_controller.execute()
        batch_response = batch_controller.getresponse()

        if batch_response is None or batch_response.messages.resultCode != OK_TRANSACTION_MESSAGE_RESULT_CODE:
            logger.error('Failed to get settled batch list')
            raise CCInternalException('Failed to get settled batch list')

        # Check for settlement errors in any batch
        if hasattr(batch_response, 'batchList'):
            batch_ids = [str(batch.batchId) for batch in batch_response.batchList.batch]
            logger.info('Found settled batches', batch_ids=batch_ids)
            for batch in batch_response.batchList.batch:
                if batch.settlementState == 'settlementError':
                    logger.warning(
                        'Settlement error found in batch.',
                        batch_id=batch.batchId,
                    )

        return batch_response

    def _get_transaction_list(self, batch_id: str, page_offset: int = 1) -> apicontractsv1.getTransactionListResponse:
        """
        Get the list of transactions for a specific batch.

        :param batch_id: The batch ID to get transactions for
        :param page_offset: The page offset for pagination (1-based)
        :return: Response containing the list of transactions
        :raises CCInternalException: If the API call fails
        """
        merchant_auth = apicontractsv1.merchantAuthenticationType()
        merchant_auth.name = self.api_login_id
        merchant_auth.transactionKey = self.transaction_key

        transaction_request = apicontractsv1.getTransactionListRequest()
        transaction_request.merchantAuthentication = merchant_auth
        transaction_request.batchId = batch_id

        # Set sorting
        sorting = apicontractsv1.TransactionListSorting()
        sorting.orderBy = apicontractsv1.TransactionListOrderFieldEnum.submitTimeUTC
        sorting.orderDescending = True
        transaction_request.sorting = sorting

        # Set paging
        paging = apicontractsv1.Paging()
        paging.limit = MAXIMUM_TRANSACTION_API_LIMIT  # Maximum allowed by API
        paging.offset = page_offset
        transaction_request.paging = paging

        transaction_controller = getTransactionListController(transaction_request)
        if config.environment_name != 'prod':
            transaction_controller.setenvironment(constants.SANDBOX)
        else:
            transaction_controller.setenvironment(constants.PRODUCTION)

        logger.info('Getting transaction list for batch', batch_id=batch_id, page_offset=page_offset)
        transaction_controller.execute()
        transaction_response = transaction_controller.getresponse()

        if (
            transaction_response is None
            or transaction_response.messages.resultCode != OK_TRANSACTION_MESSAGE_RESULT_CODE
        ):
            logger.error(
                'Failed to get transaction list',
                batch_id=batch_id,
                page_offset=page_offset,
                response=transaction_response,
            )
            raise CCInternalException('Failed to get transaction list')

        transaction_ids = [str(tx.transId) for tx in transaction_response.transactions.transaction]
        logger.info('Found transactions in batch', batch_id=batch_id, transaction_ids=transaction_ids)

        return transaction_response

    def _get_transaction_details(self, transaction_id: str) -> apicontractsv1.getTransactionDetailsResponse:
        """
        Get detailed information for a specific transaction.

        :param transaction_id: The transaction ID to get details for
        :return: Response containing the transaction details
        :raises CCInternalException: If the API call fails
        """
        merchant_auth = apicontractsv1.merchantAuthenticationType()
        merchant_auth.name = self.api_login_id
        merchant_auth.transactionKey = self.transaction_key

        details_request = apicontractsv1.getTransactionDetailsRequest()
        details_request.merchantAuthentication = merchant_auth
        details_request.transId = transaction_id

        details_controller = getTransactionDetailsController(details_request)
        if config.environment_name != 'prod':
            details_controller.setenvironment(constants.SANDBOX)
        else:
            details_controller.setenvironment(constants.PRODUCTION)

        logger.info('Getting transaction details', transaction_id=transaction_id)
        details_controller.execute()
        details_response = details_controller.getresponse()

        if details_response is None or details_response.messages.resultCode != OK_TRANSACTION_MESSAGE_RESULT_CODE:
            logger.error('Failed to get transaction details', transaction_id=transaction_id, response=details_response)
            raise CCInternalException('Failed to get transaction details')

        return details_response

    def get_settled_transactions(
        self,
        start_time: str,
        end_time: str,
        transaction_limit: int,
        last_processed_transaction_id: str = None,
        current_batch_id: str = None,
        processed_batch_ids: list[str] = None,
    ) -> dict:
        """
        Get settled transactions from the payment processor.

        :param start_time: UTC timestamp string for start of range
        :param end_time: UTC timestamp string for end of range
        :param transaction_limit: Maximum number of transactions to return
        :param last_processed_transaction_id: Optional last processed transaction ID for pagination
        :param current_batch_id: Optional current batch ID being processed
        :param processed_batch_ids: Optional list of batch IDs that have already been processed
        :return: Dictionary containing transaction details and optional pagination info
        """
        # Get settled batch list
        batch_response = self._get_settled_batch_list(start_time, end_time)

        transactions = []
        last_batch_id = None
        last_transaction_id = None
        processed_transaction_count = 0
        found_last_processed = last_processed_transaction_id is None
        processed_batch_ids = processed_batch_ids or []
        found_current_batch = current_batch_id is None
        settlement_error_transaction_ids = []

        if hasattr(batch_response, 'batchList'):
            for batch in batch_response.batchList.batch:
                batch_id = str(batch.batchId)

                # Skip batches we've already processed
                if batch_id in processed_batch_ids:
                    continue

                # Skip batches until we find the current batch we were processing
                if not found_current_batch:
                    if batch_id == current_batch_id:
                        logger.info('Found current batch to process', batch_id=current_batch_id)
                        found_current_batch = True
                    else:
                        continue

                if processed_transaction_count >= transaction_limit:
                    last_batch_id = batch_id
                    break

                # Get transaction list for batch with pagination
                page_offset = 1
                transactions_in_page = 0
                while page_offset == 1 or transactions_in_page >= MAXIMUM_TRANSACTION_API_LIMIT:
                    transaction_response = self._get_transaction_list(batch_id, page_offset)
                    transactions_in_page = int(transaction_response.totalNumInResultSet)

                    if hasattr(transaction_response, 'transactions'):
                        for transaction in transaction_response.transactions.transaction:
                            # Skip transactions until we find the last processed one
                            if not found_last_processed:
                                if str(transaction.transId) == last_processed_transaction_id:
                                    logger.info(
                                        'Found last processed transaction',
                                        transaction_id=last_processed_transaction_id,
                                        batch_id=batch_id,
                                    )
                                    found_last_processed = True
                                continue

                            # Get detailed transaction information
                            details_response = self._get_transaction_details(str(transaction.transId))
                            logger.debug(
                                'Received transaction details',
                                batch_id=batch_id,
                                transaction_id=str(transaction.transId),
                            )
                            tx = details_response.transaction

                            # Check if this transaction has a settlement error
                            if str(tx.transactionStatus) == 'settlementError':
                                settlement_error_transaction_ids.append(str(transaction.transId))
                                logger.warning(
                                    'Transaction was not in settledSuccessfully state',
                                    batch_id=batch_id,
                                    transaction_id=str(transaction.transId),
                                    transaction_status=str(tx.transactionStatus),
                                )

                            licensee_id = None
                            if hasattr(tx, 'order') and tx.order.description:
                                # Extract licensee ID from order description (format: "LICENSEE#uuid#")
                                parts = str(tx.order.description).split('#')
                                if len(parts) >= 3 and parts[0] == 'LICENSEE':
                                    licensee_id = parts[1]

                            line_items = []
                            if hasattr(tx, 'lineItems') and hasattr(tx.lineItems, 'lineItem'):
                                for item in tx.lineItems.lineItem:
                                    line_items.append(
                                        {
                                            # we must cast these to strings, or they will cause an error when we
                                            # try to serialize in other parts of the system
                                            'itemId': str(item.itemId),
                                            'name': str(item.name),
                                            'description': str(item.description),
                                            'quantity': str(item.quantity),
                                            'unitPrice': str(item.unitPrice),
                                            'taxable': str(item.taxable),
                                        }
                                    )

                            transaction_data = {
                                # we must cast these to strings, or they will cause an error when we try to serialize
                                # in other parts of the system
                                'transactionId': str(tx.transId),
                                'submitTimeUTC': str(tx.submitTimeUTC),
                                'transactionType': str(tx.transactionType),
                                'transactionStatus': str(tx.transactionStatus),
                                'responseCode': str(tx.responseCode),
                                'settleAmount': str(tx.settleAmount),
                                'licenseeId': licensee_id,
                                'batch': {
                                    'batchId': str(batch.batchId),
                                    'settlementTimeUTC': str(batch.settlementTimeUTC),
                                    'settlementTimeLocal': str(batch.settlementTimeLocal),
                                    'settlementState': str(batch.settlementState),
                                },
                                'lineItems': line_items,
                                # this defines the type of transaction processor that processed the transaction
                                'transactionProcessor': PaymentProcessorType.AUTHORIZE_DOT_NET_TYPE,
                            }
                            transactions.append(transaction_data)
                            processed_transaction_count += 1
                            if processed_transaction_count >= transaction_limit:
                                last_transaction_id = str(tx.transId)
                                break

                    # Check if we need to get the next page of transactions
                    page_offset += 1

                if processed_transaction_count >= transaction_limit:
                    last_batch_id = batch_id
                    logger.info(
                        'Transaction limit reached. Returning last processed transaction',
                        last_processed_transaction_id=last_transaction_id,
                        current_batch_id=batch_id,
                    )
                    break

                # If we've processed all transactions in this batch, add it to the processed list
                logger.info('Finished processing batch', batch_id=batch_id)
                processed_batch_ids.append(batch_id)

        response = {
            'transactions': transactions,
            'processedBatchIds': processed_batch_ids,
            'settlementErrorTransactionIds': settlement_error_transaction_ids,
        }

        if last_transaction_id and last_batch_id:
            response['lastProcessedTransactionId'] = last_transaction_id
            response['currentBatchId'] = last_batch_id

        return response


class PaymentProcessorClientFactory:
    @staticmethod
    def create_payment_processor_client(credentials: dict) -> PaymentProcessorClient:
        processor_type: str = credentials.get('processor')
        if processor_type.lower() == PaymentProcessorType.AUTHORIZE_DOT_NET_TYPE.lower():
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

    def _get_payment_processor_secret_name_for_compact(self, compact_abbr: str) -> str:
        return f'compact-connect/env/{config.environment_name}/compact/{compact_abbr}/credentials/payment-processor'

    def _get_compact_payment_processor_client(self, compact_abbr: str) -> PaymentProcessorClient:
        """
        Get the payment processor credentials for a compact
        """
        secret_name = self._get_payment_processor_secret_name_for_compact(compact_abbr)
        logger.info('Getting payment processor credentials for compact', compact_abbr=compact_abbr)
        secret = self.secrets_manager_client.get_secret_value(SecretId=secret_name)

        return PaymentProcessorClientFactory.create_payment_processor_client(json.loads(secret['SecretString']))

    def process_charge_for_licensee_privileges(
        self,
        licensee_id: str,
        order_information: dict,
        compact_configuration: Compact,
        selected_jurisdictions: list[Jurisdiction],
        license_type_abbreviation: str,
        user_active_military: bool,
    ) -> dict:
        """
        Process a charge on a credit card for a list of privileges within a compact.

        :param licensee_id: The Licensee user ID.
        :param order_information: A dictionary containing the order information (payment nonce, etc.)
        :param compact_configuration: The compact configuration.
        :param selected_jurisdictions: A list of selected jurisdictions to purchase privileges for.
        :param license_type_abbreviation: The license type abbreviation used to generate line item id.
        :param user_active_military: Whether the user is active military.
        """
        if not self.payment_processor_client:
            # get the credentials from secrets_manager for the compact
            self.payment_processor_client: PaymentProcessorClient = self._get_compact_payment_processor_client(
                compact_configuration.compact_abbr
            )

        return self.payment_processor_client.process_charge_on_credit_card_for_privilege_purchase(
            licensee_id=licensee_id,
            order_information=order_information,
            compact_configuration=compact_configuration,
            selected_jurisdictions=selected_jurisdictions,
            license_type_abbreviation=license_type_abbreviation,
            user_active_military=user_active_military,
        )

    def void_privilege_purchase_transaction(self, compact_abbr: str, order_information: dict) -> dict:
        """
        Void a charge on an unsettled credit card.

        :param compact_abbr: The name of the compact
        :param order_information: A dictionary containing the order information (billing, card, etc.)
        """
        if not self.payment_processor_client:
            # get the credentials from secrets_manager for the compact
            self.payment_processor_client: PaymentProcessorClient = self._get_compact_payment_processor_client(
                compact_abbr
            )

        return self.payment_processor_client.void_unsettled_charge_on_credit_card(order_information=order_information)

    def validate_and_store_credentials(self, compact_abbr: str, credentials: dict) -> dict:
        """
        Validate the provided payment credentials and store them in secrets manager.

        :param compact_abbr: The abbreviation of the compact
        :param credentials: The payment processor credentials
        :return: A response indicating the credentials were validated and stored successfully
        :raises CCInvalidRequestException: If the credentials are invalid
        """
        if credentials['processor'] != PaymentProcessorType.AUTHORIZE_DOT_NET_TYPE:
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

        # No exceptions were raised, so the credentials are valid
        # Store the public fields in the compact configuration for frontend use
        if credentials['processor'] == PaymentProcessorType.AUTHORIZE_DOT_NET_TYPE:
            logger.info('Storing payment processor public fields in compact configuration', compact_abbr=compact_abbr)
            try:
                config.compact_configuration_client.set_compact_authorize_net_public_values(
                    compact=compact_abbr,
                    api_login_id=response['apiLoginId'],
                    public_client_key=response['publicClientKey'],
                )
            except CCNotFoundException as e:
                logger.info('Compact configuration has not been configured yet', compact_abbr=compact_abbr)
                raise CCInvalidRequestException(
                    'Compact Fee configuration has not been configured yet. '
                    'Please configure the compact fee values and then upload your '
                    'credentials again.'
                ) from e

        # first check to see if secret already exists
        try:
            self.secrets_manager_client.describe_secret(
                SecretId=self._get_payment_processor_secret_name_for_compact(compact_abbr)
            )

            # secret exists, update its value to whatever the admin sent us
            logger.info('Existing secret found, updating secret for compact', compact_abbr=compact_abbr)
            self.secrets_manager_client.put_secret_value(
                SecretId=self._get_payment_processor_secret_name_for_compact(compact_abbr),
                SecretString=json.dumps(secret_value),
            )
        except self.secrets_manager_client.exceptions.ResourceNotFoundException:
            # secret does not exist, so we can create it
            logger.info('Existing secret not found, creating new secret for compact', compact_abbr=compact_abbr)
            self.secrets_manager_client.create_secret(
                Name=self._get_payment_processor_secret_name_for_compact(compact_abbr),
                SecretString=json.dumps(secret_value),
            )

        return {'message': 'Successfully verified credentials'}

    def get_settled_transactions(
        self,
        compact: str,
        start_time: str,
        end_time: str,
        transaction_limit: int,
        last_processed_transaction_id: str = None,
        current_batch_id: str = None,
        processed_batch_ids: list[str] = None,
    ) -> dict:
        """
        Get settled transactions from the payment processor.

        :param compact: The compact name
        :param start_time: UTC timestamp string for start of range
        :param end_time: UTC timestamp string for end of range
        :param transaction_limit: Maximum number of transactions to return
        :param last_processed_transaction_id: Optional last processed transaction ID for pagination
        :param current_batch_id: Optional current batch ID being processed
        :param processed_batch_ids: Optional list of batch IDs that have already been processed
        :return: Dictionary containing transaction details and optional pagination info
        """
        if not self.payment_processor_client:
            self.payment_processor_client = self._get_compact_payment_processor_client(compact)

        response = self.payment_processor_client.get_settled_transactions(
            start_time=start_time,
            end_time=end_time,
            transaction_limit=transaction_limit,
            last_processed_transaction_id=last_processed_transaction_id,
            current_batch_id=current_batch_id,
            processed_batch_ids=processed_batch_ids,
        )

        # Add compact to each transaction for serialization
        for transaction in response['transactions']:
            transaction['compact'] = compact

        return response
