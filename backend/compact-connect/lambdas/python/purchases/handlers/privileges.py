import json
from datetime import UTC, date, datetime

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderRecordType, ProviderRecordUtility
from cc_common.data_model.schema.common import ActiveInactiveStatus, CompactEligibilityStatus
from cc_common.data_model.schema.compact import COMPACT_TYPE, Compact
from cc_common.data_model.schema.compact.api import CompactOptionsResponseSchema
from cc_common.data_model.schema.jurisdiction import JURISDICTION_TYPE, Jurisdiction
from cc_common.data_model.schema.jurisdiction.api import JurisdictionOptionsResponseSchema
from cc_common.event_bus_client import EventBusClient
from cc_common.exceptions import (
    CCAwsServiceException,
    CCFailedTransactionException,
    CCInternalException,
    CCInvalidRequestException,
    CCNotFoundException,
)
from cc_common.utils import api_handler
from purchase_client import PurchaseClient

# List of attestations that are always required
REQUIRED_ATTESTATION_IDS = [
    'jurisprudence-confirmation',
    'scope-of-practice-attestation',
    'personal-information-home-state-attestation',
    'personal-information-address-attestation',
    'discipline-no-current-encumbrance-attestation',
    'discipline-no-prior-encumbrance-attestation',
    'provision-of-true-information-attestation',
]

# Attestations where exactly one must be provided
INVESTIGATION_ATTESTATION_IDS = [
    'not-under-investigation-attestation',
    'under-investigation-attestation',
]

# Attestation required for users with active military affiliation
MILITARY_ATTESTATION_ID = 'military-affiliation-confirmation-attestation'


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

    options_response = config.compact_configuration_client.get_privilege_purchase_options(
        compact=compact,
        pagination=event.get('queryStringParameters', {}),
    )

    # we need to filter out contact information from the response, which is not needed by the client
    serlialized_options = []
    for item in options_response['items']:
        if item['type'] == JURISDICTION_TYPE:
            serlialized_options.append(JurisdictionOptionsResponseSchema().load(item))
        elif item['type'] == COMPACT_TYPE:
            serlialized_options.append(CompactOptionsResponseSchema().load(item))

    options_response['items'] = serlialized_options

    return options_response


def _validate_attestations(compact: str, attestations: list[dict], has_active_military_affiliation: bool = False):
    """
    Validate that all required attestations are present and are the latest version.

    :param compact: The compact name
    :param attestations: List of attestations from the request body
    :param has_active_military_affiliation: Whether the user has an active military affiliation
    :raises CCInvalidRequestException: If any attestation is not found, not the latest version,
    or validation rules are not met
    """
    # Get all latest attestations for this compact
    latest_attestations = config.compact_configuration_client.get_attestations_by_locale(compact=compact)

    # Build list of required attestations
    required_ids = REQUIRED_ATTESTATION_IDS.copy()
    if has_active_military_affiliation:
        required_ids.append(MILITARY_ATTESTATION_ID)

    # Validate investigation attestations - exactly one must be provided
    investigation_attestations = [a for a in attestations if a['attestationId'] in INVESTIGATION_ATTESTATION_IDS]
    if len(investigation_attestations) != 1:
        raise CCInvalidRequestException(
            'Exactly one investigation attestation must be provided '
            f'(either {INVESTIGATION_ATTESTATION_IDS[0]} or {INVESTIGATION_ATTESTATION_IDS[1]})'
        )
    required_ids.append(investigation_attestations[0]['attestationId'])

    # Check that all required attestations are present
    provided_ids = {a['attestationId'] for a in attestations}
    missing_ids = set(required_ids) - provided_ids
    if missing_ids:
        raise CCInvalidRequestException(f'Missing required attestations: {", ".join(missing_ids)}')

    # Check for any invalid attestation IDs
    invalid_ids = provided_ids - set(required_ids)
    if invalid_ids:
        raise CCInvalidRequestException(f'Invalid attestations provided: {", ".join(invalid_ids)}')

    # Verify all provided attestations are the latest version
    for attestation in attestations:
        attestation_id = attestation['attestationId']
        latest_attestation = latest_attestations.get(attestation_id)
        if not latest_attestation:
            raise CCInvalidRequestException(f'Attestation not found: "{attestation_id}"')
        if latest_attestation['version'] != attestation['version']:
            raise CCInvalidRequestException(
                f'Attestation "{attestation_id}" version {attestation["version"]} '
                f'is not the latest version ({latest_attestation["version"]})'
            )


@api_handler
def post_purchase_privileges(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    This endpoint allows a provider to purchase privileges.

    The request body should include the license type, selected jurisdiction privileges to purchase, billing information,
    and attestations in the following format:
    {
        "licenseType": "<license type>", # must match one of the license types from the provider's home state licenses
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
        },
        "attestations": [{
            "attestationId": "jurisprudence-confirmation",
            "version": "1"
        }]
    }

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact_abbr = _get_caller_compact_custom_attribute(event)
    body = json.loads(event['body'])
    selected_jurisdictions_postal_abbreviations = [
        postal_abbreviation.lower() for postal_abbreviation in body['selectedJurisdictions']
    ]

    # load the compact information
    privilege_purchase_options = config.compact_configuration_client.get_privilege_purchase_options(
        compact=compact_abbr
    )

    compact_configuration = [item for item in privilege_purchase_options['items'] if item['type'] == COMPACT_TYPE]
    if not compact_configuration:
        message = f"Compact configuration not found for this caller's compact: {compact_abbr}"
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

    # get the user's profile information
    provider_id = _get_caller_provider_id_custom_attribute(event)
    user_provider_data = config.data_client.get_provider(compact=compact_abbr, provider_id=provider_id)

    home_state_selection = ProviderRecordUtility.get_provider_home_state_selection(user_provider_data['items'])
    if home_state_selection is None:
        raise CCInternalException('No home state selection found for this user')

    # we now validate that the license type matches one of the license types from the home state license records
    matching_license_records = ProviderRecordUtility.get_records_of_type(
        user_provider_data['items'],
        ProviderRecordType.LICENSE,
        _filter=lambda record: record['licenseType'] == body['licenseType']
        and record['jurisdiction'] == home_state_selection
        and record['compactEligibility'] == CompactEligibilityStatus.ELIGIBLE,
    )

    if not matching_license_records:
        raise CCInvalidRequestException(
            'Specified license type does not match any eligible licenses in the home state.'
        )

    matching_license_record = matching_license_records[0]

    provider_records = ProviderRecordUtility.get_records_of_type(
        user_provider_data['items'],
        ProviderRecordType.PROVIDER,
    )
    # this should never happen, but we check just in case
    if not provider_records:
        raise CCNotFoundException('Provider not found')
    provider_record = provider_records[0]

    license_jurisdiction = matching_license_record['jurisdiction']
    if license_jurisdiction.lower() in selected_jurisdictions_postal_abbreviations:
        raise CCInvalidRequestException(
            f"Selected privilege jurisdiction '{license_jurisdiction}' matches license jurisdiction"
        )

    all_privilege_records = ProviderRecordUtility.get_records_of_type(
        user_provider_data['items'], ProviderRecordType.PRIVILEGE
    )

    existing_privileges_for_license = [
        record for record in all_privilege_records if record['licenseType'] == matching_license_record['licenseType']
    ]
    # a licensee can only purchase an existing privilege for a jurisdiction
    # if their existing privilege expiration date does not match their license expiration date
    # this is because the only reason a user should renew an existing privilege is if they have renewed
    # their license and want to extend the expiration date of their privilege to match the new license expiration date.
    for privilege in existing_privileges_for_license:
        if (
            privilege['jurisdiction'].lower() in selected_jurisdictions_postal_abbreviations
            # if their latest privilege expiration date matches the license expiration date they will not
            # receive any benefit from purchasing the same privilege, since the expiration date will not change
            and privilege['dateOfExpiration'] == matching_license_record['dateOfExpiration']
            and privilege['administratorSetStatus'] == ActiveInactiveStatus.ACTIVE
        ):
            raise CCInvalidRequestException(
                f"Selected privilege jurisdiction '{privilege['jurisdiction'].lower()}'"
                f' matches existing privilege jurisdiction for license type'
            )

    license_expiration_date: date = matching_license_record['dateOfExpiration']
    user_active_military = ProviderRecordUtility.determine_military_affiliation_status(user_provider_data['items'])

    # Validate attestations are the latest versions before proceeding with the purchase
    _validate_attestations(compact_abbr, body.get('attestations', []), user_active_military)

    purchase_client = PurchaseClient()
    transaction_response = None
    try:
        license_type_abbr = config.license_type_abbreviations[compact_abbr][matching_license_record['licenseType']]
        transaction_response = purchase_client.process_charge_for_licensee_privileges(
            licensee_id=provider_id,
            order_information=body['orderInformation'],
            compact_configuration=compact,
            selected_jurisdictions=selected_jurisdictions,
            license_type_abbreviation=license_type_abbr,
            user_active_military=user_active_military,
        )

        # transaction was successful, now we create privilege records for the selected jurisdictions
        #
        generated_privileges = config.data_client.create_provider_privileges(
            compact=compact_abbr,
            provider_id=provider_id,
            jurisdiction_postal_abbreviations=selected_jurisdictions_postal_abbreviations,
            license_expiration_date=license_expiration_date,
            compact_transaction_id=transaction_response['transactionId'],
            provider_record=provider_record,
            existing_privileges_for_license=existing_privileges_for_license,
            license_type=matching_license_record['licenseType'],
            attestations=body['attestations'],
        )

        provider_email = provider_record['emailAddress']
        transaction_date = datetime.now(tz=UTC).date()

        privileges = generated_privileges
        cost_line_items = transaction_response['lineItems']

        # calculate total cost of transaction
        total_cost = 0
        for line_item in cost_line_items:
            total_cost = total_cost + line_item['unitPrice'] * line_item['quantity']

        config.event_bus_client.publish_privilege_purchase_event(
            source='post_purchase_privileges',
            provider_email=provider_email,
            transaction_date=transaction_date,
            privileges=privileges,
            total_cost=total_cost,
            cost_line_items=cost_line_items,
        )

        privileges_renewed = []
        privileges_issued = []

        for jurisdiction in selected_jurisdictions_postal_abbreviations:
            if jurisdiction in existing_privileges_for_license:
                privileges_renewed.append(jurisdiction)
            else:
                privileges_issued.append(jurisdiction)

        for privilege_jurisdiction_issued in privileges_issued:
            config.event_bus_client.publish_privilege_issued_event(
                source='post_purchase_privileges',
                provider_email=provider_email,
                date=transaction_date,
                privilege=privilege_jurisdiction_issued,
            )

        for privilege_jurisdiction_renewed in privileges_renewed:
            config.event_bus_client.publish_privilege_renewed_event(
                source='post_purchase_privileges',
                provider_email=provider_email,
                date=transaction_date,
                privilege=privilege_jurisdiction_renewed,
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
                compact_abbr=compact_abbr, order_information=transaction_response
            )
            raise CCInternalException('Internal Server Error') from e
