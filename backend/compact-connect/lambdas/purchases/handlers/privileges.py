import json
from datetime import date

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.compact import COMPACT_TYPE, Compact, CompactOptionsApiResponseSchema
from cc_common.data_model.schema.jurisdiction import (
    JURISDICTION_TYPE,
    Jurisdiction,
    JurisdictionOptionsApiResponseSchema,
)
from cc_common.exceptions import (
    CCAwsServiceException,
    CCFailedTransactionException,
    CCInternalException,
    CCInvalidRequestException,
    CCNotFoundException,
)
from cc_common.utils import api_handler
from purchase_client import PurchaseClient


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


def _find_latest_active_license(all_licenses: list[dict]) -> dict | None:
    """
    In this scenario, we are looking for the most recent active license record for the user.
    """
    if len(all_licenses) == 0:
        return None

    # Last issued active license, if there are any active licenses
    latest_active_licenses = sorted(
        [license_data for license_data in all_licenses if license_data['status'] == 'active'],
        key=lambda x: x['dateOfIssuance'],
        reverse=True,
    )
    if latest_active_licenses:
        return latest_active_licenses[0]

    return None


@api_handler
def post_purchase_privileges(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    This endpoint allows a provider to purchase privileges.

    The request body should include the selected jurisdiction privileges to purchase and billing information
    in the following format:
    {
        "selectedJurisdictions": ["<jurisdiction postal abbreviations>"],
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
    body = json.loads(event['body'])
    selected_jurisdictions_postal_abbreviations = [
        postal_abbreviation.lower() for postal_abbreviation in body['selectedJurisdictions']
    ]

    # load the compact information
    privilege_purchase_options = config.data_client.get_privilege_purchase_options(compact=compact_name)

    compact_configuration = [item for item in privilege_purchase_options['items'] if item['type'] == COMPACT_TYPE]
    if not compact_configuration:
        message = f"Compact configuration not found for this caller's compact: {compact_name}"
        logger.error(message)
        raise CCInternalException(message)
    compact = Compact(compact_configuration[0])

    # load the jurisdiction information into a list of Jurisdiction objects
    selected_jurisdictions = [
        Jurisdiction(item)
        for item in privilege_purchase_options['items']
        if item['type'] == JURISDICTION_TYPE
        and item['postalAbbreviation'].lower() in selected_jurisdictions_postal_abbreviations
    ]
    # assert the selected jurisdictions map to the expected number of jurisdictions
    if len(selected_jurisdictions) != len(selected_jurisdictions_postal_abbreviations):
        # this could only happen if the jurisdiction configuration was not uploaded or was deleted somehow
        logger.error(
            'Jurisdiction configuration missing. Requested jurisdiction not found.',
            existing_jurisdiction_configuration=[
                selected_jurisdiction.postal_abbreviation for selected_jurisdiction in selected_jurisdictions
            ],
            selected_jurisdictions_postal_abbreviations=selected_jurisdictions_postal_abbreviations,
        )
        raise CCInvalidRequestException('Invalid jurisdiction postal abbreviation')

    # get the user's profile information to determine if they are active military
    provider_id = _get_caller_provider_id_custom_attribute(event)
    user_provider_data = config.data_client.get_provider(compact=compact_name, provider_id=provider_id)
    provider_record = next((record for record in user_provider_data['items'] if record['type'] == 'provider'), None)
    license_record = _find_latest_active_license(
        [record for record in user_provider_data['items'] if record['type'] == 'license']
    )

    # this should never happen, but we check just in case
    if provider_record is None:
        raise CCNotFoundException('Provider not found')
    if license_record is None:
        raise CCInvalidRequestException('No active license found for this user')

    license_jurisdiction = license_record['jurisdiction']
    if license_jurisdiction.lower() in selected_jurisdictions_postal_abbreviations:
        raise CCInvalidRequestException(
            f"Selected privilege jurisdiction '{license_jurisdiction}'" f' matches license jurisdiction'
        )

    existing_privileges = [record for record in user_provider_data['items'] if record['type'] == 'privilege']
    # a licensee can only purchase an existing privilege for a jurisdiction
    # if their existing privilege expiration date does not match their license expiration date
    for privilege in existing_privileges:
        if (
            privilege['jurisdiction'].lower() in selected_jurisdictions_postal_abbreviations
            and privilege['dateOfExpiration'] == license_record['dateOfExpiration']
        ):
            raise CCInvalidRequestException(
                f"Selected privilege jurisdiction '{privilege['jurisdiction'].lower()}'"
                f' matches existing privilege jurisdiction'
            )

    license_expiration_date: date = license_record['dateOfExpiration']
    user_active_military = bool(provider_record.get('militaryWaiver', False))

    purchase_client = PurchaseClient()
    transaction_response = None
    try:
        transaction_response = purchase_client.process_charge_for_licensee_privileges(
            order_information=body['orderInformation'],
            compact_configuration=compact,
            selected_jurisdictions=selected_jurisdictions,
            user_active_military=user_active_military,
        )

        # transaction was successful, now we create privilege records for the selected jurisdictions
        config.data_client.create_provider_privileges(
            compact_name=compact_name,
            provider_id=provider_id,
            jurisdiction_postal_abbreviations=selected_jurisdictions_postal_abbreviations,
            license_expiration_date=license_expiration_date,
            compact_transaction_id=transaction_response['transactionId'],
            existing_privileges=existing_privileges,
        )

        return transaction_response

    except CCFailedTransactionException as e:
        logger.warning(f'Failed transaction: {e}.')
        raise CCInvalidRequestException(f'Error: {e.message}') from e
    except CCAwsServiceException as e:
        logger.error(f'Error creating privilege records: {e.message}. Voiding transaction.')
        if transaction_response:
            # void the transaction if it was successful
            purchase_client.void_privilege_purchase_transaction(
                compact_name=compact_name, order_information=transaction_response
            )
            raise CCInternalException('Internal Server Error') from e
