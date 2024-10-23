import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from config import config, logger
from data_model.schema.compact import COMPACT_TYPE, Compact, CompactOptionsApiResponseSchema
from data_model.schema.jurisdiction import JURISDICTION_TYPE, Jurisdiction, JurisdictionOptionsApiResponseSchema
from exceptions import CCFailedTransactionException, CCInvalidRequestException, CCNotFoundException
from purchase_client import PurchaseClient

from handlers.utils import api_handler


def _get_caller_compact_custom_attribute(event: dict) -> str:
    try:
        return event['requestContext']['authorizer']['claims']['custom:compact']
    except KeyError as e:
        logger.error(f'Missing custom provider attribute: {e}')
        raise CCInvalidRequestException('Missing required user profile attribute') from e


def _get_caller_provider_id_custom_attribute(event: dict) -> str:
    try:
        return event['requestContext']['authorizer']['claims']['custom:providerId']
    except KeyError as e:
        logger.error(f'Missing custom provider attribute: {e}')
        raise CCInvalidRequestException('Missing required user profile attribute') from e


@api_handler
def get_purchase_privilege_options(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """This endpoint returns the available privilege options for a provider to purchase.

    The options are defined by the various jurisdictions that have opted into the compact.
    These options include information such as the jurisdiction name, the fee for the compact, etc.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = _get_caller_compact_custom_attribute(event)

    options_response = config.data_client.get_privilege_purchase_options(
        compact=compact,
        pagination=event.get('queryStringParameters', {}),
    )

    # we need to filter out contact information from the response, which is not needed by the client
    serlialized_options = []
    for item in options_response['items']:
        if item['type'] == JURISDICTION_TYPE:
            serlialized_options.append(JurisdictionOptionsApiResponseSchema().load(item))
        elif item['type'] == COMPACT_TYPE:
            serlialized_options.append(CompactOptionsApiResponseSchema().load(item))

    options_response['items'] = serlialized_options

    return options_response


@api_handler
def post_purchase_privileges(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    This endpoint allows a provider to purchase privileges.

    The request body should include the selected jurisdiction privileges to purchase and billing information
    in the following format:
    {
        "selectedJurisdictions": ["<jurisdiction postal code>"],
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

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact_name = _get_caller_compact_custom_attribute(event)

    # load the compact information
    privilege_purchase_options = config.data_client.get_privilege_purchase_options(compact=compact_name)

    compact_configuration = [item for item in privilege_purchase_options['items'] if item['type'] == COMPACT_TYPE]
    if not compact_configuration:
        raise CCInvalidRequestException(f"Compact configuration not found for this caller's compact: {compact_name}")
    compact = Compact(compact_configuration[0])

    body = json.loads(event['body'])
    # ensure the postal codes are all lowercase for string comparison
    selected_jurisdictions_postal_codes = [postal_code.lower() for postal_code in body['selectedJurisdictions']]
    # load the jurisdiction information into a list of Jurisdiction objects
    selected_jurisdictions = [
        Jurisdiction(item)
        for item in privilege_purchase_options['items']
        if item['type'] == JURISDICTION_TYPE
        and item['postalAbbreviation'].lower() in selected_jurisdictions_postal_codes
    ]

    # get the user's profile information to determine if they are active military
    provider_id = _get_caller_provider_id_custom_attribute(event)
    user_provider_data = config.data_client.get_provider(compact=compact_name, provider_id=provider_id)
    provider_record = next((record for record in user_provider_data['items'] if record['type'] == 'provider'), None)
    if provider_record is None:
        raise CCNotFoundException('Provider record not found for this user')

    user_active_military = bool(provider_record.get('militaryWaiver', False))

    try:
        return PurchaseClient().process_charge_for_licensee_privileges(
            order_information=body['orderInformation'],
            compact_configuration=compact,
            selected_jurisdictions=selected_jurisdictions,
            user_active_military=user_active_military,
        )

    except CCFailedTransactionException as e:
        logger.warning(f'Failed transaction: {e}.')
        raise CCInvalidRequestException(f'Error: {e.message}') from e
