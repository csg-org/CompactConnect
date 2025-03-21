import json

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger, metrics
from cc_common.data_model.schema.common import CCPermissionsAction
from cc_common.event_batch_writer import EventBatchWriter
from cc_common.exceptions import CCAccessDeniedException, CCInternalException, CCInvalidRequestException
from cc_common.utils import api_handler, authorize_compact, get_event_scopes, sqs_handler


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

        # Validate the license type is a supported abbreviation
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
    return {'message': 'OK'}


@sqs_handler
def privilege_deactivation_message_handler(message: dict):
    """
    Handle privilege deactivation messages from the event bus.
    This handler is responsible for sending email notifications to both the provider
    and the jurisdiction when a privilege is deactivated.
    
    If notification sending fails, the function will raise a CCInternalException,
    which will cause the SQS handler decorator to report the message as a failure
    and the message will be retried according to the queue's retry policy.
    """
    compact = message.get('compact')
    provider_id = message.get('providerId')
    jurisdiction = message.get('jurisdiction')
    privilege_id = message.get('privilegeId')
    
    with logger.append_context_keys(
        compact=compact, provider_id=provider_id, jurisdiction=jurisdiction, privilege_id=privilege_id
    ):
        logger.info('Processing privilege deactivation notification')
        
        # Get provider information to retrieve email and name
        provider = config.data_client.get_provider(compact=compact, provider_id=provider_id, detail=False)['items'][0]
        
        error_messages = []
        
        # Send notification to the provider
        try:
            provider_email = provider.get('compactConnectRegisteredEmailAddress')
            if not provider_email:
                logger.error('Provider email not found, cannot send provider notification', provider_id=provider_id)
            else:
                logger.info(
                    'Sending privilege deactivation notification to provider',
                    provider_id=provider_id,
                    provider_email=provider_email,
                )
                config.email_service_client.send_provider_privilege_deactivation_email(
                    compact=compact,
                    provider_email=provider_email,
                    privilege_id=privilege_id,
                )
        except CCInternalException as e:
            error_message = f'Failed to send provider privilege deactivation notification: {str(e)}'
            logger.error(error_message, exc_info=e)
            error_messages.append(error_message)

        # Send notification to the jurisdiction
        try:
            logger.info('Sending privilege deactivation notification to jurisdiction', jurisdiction=jurisdiction)
            provider_first_name = provider['givenName']
            provider_last_name = provider['familyName']
            config.email_service_client.send_jurisdiction_privilege_deactivation_email(
                compact=compact,
                jurisdiction=jurisdiction,
                privilege_id=privilege_id,
                provider_first_name=provider_first_name,
                provider_last_name=provider_last_name,
            )
        except CCInternalException as e:
            error_message = f'Failed to send jurisdiction privilege deactivation notification: {str(e)}'
            logger.error(error_message, exc_info=e)
            error_messages.append(error_message)

        # If there were any errors, raise an exception to trigger a retry
        if error_messages:
            raise CCInternalException('; '.join(error_messages))
