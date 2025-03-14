import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.common import CCPermissionsAction
from cc_common.exceptions import CCAccessDeniedException, CCInvalidRequestException
from cc_common.utils import api_handler, authorize_compact, get_event_scopes
from event_batch_writer import EventBatchWriter


@api_handler
@authorize_compact(action=CCPermissionsAction.ADMIN)
def deactivate_privilege(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Deactivate a provider's privilege for a specific jurisdiction.
    This endpoint requires admin permissions for either the compact or the jurisdiction.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact = event['pathParameters']['compact']
    provider_id = event['pathParameters']['providerId']
    jurisdiction = event['pathParameters']['jurisdiction']
    license_type_abbr = event['pathParameters']['licenseType']

    with logger.append_context_keys(
        compact=compact, provider_id=provider_id, jurisdiction=jurisdiction, license_type=license_type_abbr
    ):
        # Get the user's scopes to check for jurisdiction-specific admin permission
        scopes = get_event_scopes(event)
        jurisdiction_admin_scope = f'{jurisdiction}/{compact}.{CCPermissionsAction.ADMIN}'
        compact_admin_scope = f'{compact}/{CCPermissionsAction.ADMIN}'

        # Check if user has admin permission for either the compact or the jurisdiction
        if jurisdiction_admin_scope not in scopes and compact_admin_scope not in scopes:
            logger.warning('Unauthorized deactivation attempt')
            raise CCAccessDeniedException('User does not have admin permission for this jurisdiction')

        # Validate the the license type is a supported abbreviation
        if license_type_abbr not in config.license_type_abbreviations[compact].values():
            logger.warning('Invalid license type abbreviation')
            raise CCInvalidRequestException(f'Invalid license type abbreviation: {license_type_abbr}')

        logger.info('Deactivating privilege')
        config.data_client.deactivate_privilege(
            compact=compact,
            provider_id=provider_id,
            jurisdiction=jurisdiction,
            license_type_abbr=license_type_abbr,
        )
        with EventBatchWriter(config.events_client) as event_writer:
            event_writer.put_event(
                Entry={
                    'Source': 'org.compactconnect.provider-data',
                    'DetailType': 'privilege.deactivation',
                    'Detail': json.dumps(
                        {
                            'eventTime': config.current_standard_datetime.isoformat(),
                            'compact': compact,
                            'jurisdiction': jurisdiction,
                            'providerId': provider_id,
                        }
                    ),
                    'EventBusName': config.event_bus_name,
                }
            )

    return {'message': 'OK'}
