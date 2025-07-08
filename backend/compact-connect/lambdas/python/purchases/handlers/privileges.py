import json
from datetime import date

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderUserRecords
from cc_common.data_model.schema.common import (
    ActiveInactiveStatus,
    CompactEligibilityStatus,
    HomeJurisdictionChangeStatusEnum,
    LicenseDeactivatedStatusEnum,
    LicenseEncumberedStatusEnum,
)
from cc_common.data_model.schema.compact import Compact
from cc_common.data_model.schema.compact.api import CompactOptionsResponseSchema
from cc_common.data_model.schema.compact.common import COMPACT_TYPE
from cc_common.data_model.schema.fields import OTHER_JURISDICTION, UNKNOWN_JURISDICTION
from cc_common.data_model.schema.jurisdiction import Jurisdiction
from cc_common.data_model.schema.jurisdiction.api import JurisdictionOptionsResponseSchema
from cc_common.data_model.schema.jurisdiction.common import JURISDICTION_TYPE
from cc_common.data_model.schema.military_affiliation.common import MilitaryAffiliationStatus
from cc_common.exceptions import (
    CCAwsServiceException,
    CCFailedTransactionException,
    CCInternalException,
    CCInvalidRequestException,
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
            # we determine at run-time if the payment processor is running in sandbox mode
            item['isSandbox'] = config.environment_name != 'prod'
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
    provider_user_records: ProviderUserRecords = config.data_client.get_provider_user_records(
        compact=compact_abbr, provider_id=provider_id
    )
    top_level_provider_record = provider_user_records.get_provider_record()

    # first verify that the provider is not encumbered
    if top_level_provider_record.encumberedStatus == LicenseEncumberedStatusEnum.ENCUMBERED:
        logger.info(
            'This practitioner currently has a license or privilege that is encumbered. Cannot purchase privileges',
            compact=compact_abbr,
            provider_id=provider_id,
        )
        raise CCInvalidRequestException(
            'You have a license or privilege that is currently encumbered, and are unable'
            ' to purchase privileges at this time.'
        )

    current_home_jurisdiction = top_level_provider_record.currentHomeJurisdiction
    if (
        current_home_jurisdiction is None
        or current_home_jurisdiction == UNKNOWN_JURISDICTION
        or current_home_jurisdiction == OTHER_JURISDICTION
    ):
        logger.error(
            'API request to purchase privileges for provider that does not have a valid home state selection.',
            provider_id=provider_id,
            compact=compact.compact_abbr,
            current_home_jurisdiction=current_home_jurisdiction,
        )
        raise CCInternalException(
            'Invalid home state selection found for this user. '
            'User should not be able to request privileges in this state.'
        )

    # we now validate that the license type matches one of the license types from the home state license records
    matching_license_records = provider_user_records.get_license_records(
        filter_condition=lambda record: record.licenseType == body['licenseType']
        and record.jurisdiction == current_home_jurisdiction
        and record.compactEligibility == CompactEligibilityStatus.ELIGIBLE,
    )

    if not matching_license_records:
        raise CCInvalidRequestException(
            'Specified license type does not match any eligible licenses in the home state.'
        )

    matching_license_record = matching_license_records[0]

    license_jurisdiction = matching_license_record.jurisdiction
    if license_jurisdiction.lower() in selected_jurisdictions_postal_abbreviations:
        raise CCInvalidRequestException(
            f"Selected privilege jurisdiction '{license_jurisdiction}' matches license jurisdiction"
        )

    existing_privileges_for_license = provider_user_records.get_privilege_records(
        filter_condition=lambda privilege_record: privilege_record.licenseType == matching_license_record.licenseType
    )
    # a licensee can only purchase an existing privilege for a jurisdiction
    # if their existing privilege expiration date does not match their license expiration date
    # this is because the only reason a user should renew an existing privilege is if they have renewed
    # their license and want to extend the expiration date of their privilege to match the new license expiration date.
    for privilege in existing_privileges_for_license:
        if (
            privilege.jurisdiction.lower() in selected_jurisdictions_postal_abbreviations
            # if their latest privilege expiration date matches the license expiration date they will not
            # receive any benefit from purchasing the same privilege, since the expiration date will not change
            and privilege.dateOfExpiration == matching_license_record.dateOfExpiration
            # If an admin previously deactivated this privilege for whatever reason, we allow the provider to
            # renew it even if the expiration dates still match
            and privilege.administratorSetStatus == ActiveInactiveStatus.ACTIVE
            # Similar here, if the user's privilege was deactivated previously due to changing their home jurisdiction
            # to where they had no license, but now they have an eligible license, they can renew their privilege.
            and privilege.homeJurisdictionChangeStatus != HomeJurisdictionChangeStatusEnum.INACTIVE
            # Likewise, if the user's privilege was deactivated previously due to a license deactivation, and then the
            # license was reactivated, they can renew their privilege.
            and privilege.licenseDeactivatedStatus != LicenseDeactivatedStatusEnum.LICENSE_DEACTIVATED
        ):
            raise CCInvalidRequestException(
                f"Selected privilege jurisdiction '{privilege.jurisdiction.lower()}'"
                f' matches existing privilege jurisdiction for license type'
            )

    license_expiration_date: date = matching_license_record.dateOfExpiration
    provider_latest_military_status = provider_user_records.get_latest_military_affiliation_status()
    if provider_latest_military_status == MilitaryAffiliationStatus.INITIALIZING:
        # this only occurs if the user's military document was not processed by S3 as expected
        raise CCInvalidRequestException(
            'Your proof of military affiliation documentation was not successfully processed. '
            'Please return to the Military Status page and re-upload your military affiliation '
            'documentation or end your military affiliation.'
        )

    user_active_military = provider_latest_military_status == MilitaryAffiliationStatus.ACTIVE

    # Validate attestations are the latest versions before proceeding with the purchase
    _validate_attestations(compact_abbr, body.get('attestations', []), user_active_military)

    purchase_client = PurchaseClient()
    transaction_response = None
    try:
        license_type_abbr = config.license_type_abbreviations[compact_abbr][matching_license_record.licenseType]
        transaction_response = purchase_client.process_charge_for_licensee_privileges(
            licensee_id=provider_id,
            order_information=body['orderInformation'],
            compact_configuration=compact,
            selected_jurisdictions=selected_jurisdictions,
            license_type_abbreviation=license_type_abbr,
            user_active_military=user_active_military,
        )

        # transaction was successful, now we create privilege records for the selected jurisdictions
        generated_privileges = config.data_client.create_provider_privileges(
            compact=compact_abbr,
            provider_id=provider_id,
            jurisdiction_postal_abbreviations=selected_jurisdictions_postal_abbreviations,
            license_expiration_date=license_expiration_date,
            compact_transaction_id=transaction_response['transactionId'],
            provider_record=top_level_provider_record,
            existing_privileges_for_license=existing_privileges_for_license,
            license_type=matching_license_record.licenseType,
            attestations=body['attestations'],
        )

        # Filtering the params to a subset that is actually needed
        filtered_privileges = [
            {
                'compact': p.compact,
                'providerId': p.providerId,
                'jurisdiction': p.jurisdiction,
                'licenseTypeAbbrev': config.license_type_abbreviations[compact_abbr][
                    matching_license_record.licenseType
                ],
                'privilegeId': p.privilegeId,
            }
            for p in generated_privileges
        ]

        provider_email = top_level_provider_record.compactConnectRegisteredEmailAddress

        cost_line_items = transaction_response['lineItems']

        # calculate total cost of transaction
        total_cost = 0
        for line_item in cost_line_items:
            total_cost = total_cost + float(line_item['unitPrice']) * int(line_item['quantity'])

        config.event_bus_client.publish_privilege_purchase_event(
            source='org.compactconnect.purchases',
            jurisdiction=license_jurisdiction,
            compact=compact_abbr,
            provider_email=provider_email,
            privileges=filtered_privileges,
            total_cost=str(total_cost),
            cost_line_items=cost_line_items,
        )

        privilege_jurisdictions_renewed = []
        privilege_jurisdictions_issued = []
        existing_privilege_jurisdictions = [
            existing_privilege.jurisdiction for existing_privilege in existing_privileges_for_license
        ]

        for jurisdiction in selected_jurisdictions_postal_abbreviations:
            if jurisdiction in existing_privilege_jurisdictions:
                privilege_jurisdictions_renewed.append(jurisdiction)
            else:
                privilege_jurisdictions_issued.append(jurisdiction)

        for privilege_jurisdiction_issued in privilege_jurisdictions_issued:
            config.event_bus_client.publish_privilege_issued_event(
                source='org.compactconnect.purchases',
                jurisdiction=privilege_jurisdiction_issued,
                compact=compact_abbr,
                provider_email=provider_email,
            )

        for privilege_jurisdiction_renewed in privilege_jurisdictions_renewed:
            config.event_bus_client.publish_privilege_renewed_event(
                source='org.compactconnect.purchases',
                jurisdiction=privilege_jurisdiction_renewed,
                compact=compact_abbr,
                provider_email=provider_email,
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
