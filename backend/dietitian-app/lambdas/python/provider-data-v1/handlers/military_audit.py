import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.common import CCPermissionsAction
from cc_common.data_model.schema.military_affiliation.api import MilitaryAuditRequestSchema, MilitaryAuditStatus
from cc_common.exceptions import CCInvalidRequestException
from cc_common.utils import api_handler, authorize_compact_level_only_action, to_uuid
from marshmallow import ValidationError

MILITARY_AUDIT_ENDPOINT_RESOURCE = '/v1/compacts/{compact}/providers/{providerId}/militaryAudit'


@api_handler
@authorize_compact_level_only_action(action=CCPermissionsAction.ADMIN)
def military_audit_handler(event: dict, context: LambdaContext) -> dict:
    """
    Handle military audit requests from compact admins.

    This endpoint allows compact admins to approve or decline military documentation
    uploaded by providers. The audit result is stored in the provider record.

    :param event: API Gateway event
    :param context: Lambda context
    :return: Success message
    """
    with logger.append_context_keys(aws_request=context.aws_request_id):
        logger.info('Processing military audit request')

        # Extract path parameters
        compact = event['pathParameters']['compact']
        provider_id = to_uuid(event['pathParameters']['providerId'], 'Invalid providerId provided')

        # Get the cognito sub of the caller for tracing
        cognito_sub = event['requestContext']['authorizer']['claims']['sub']

        with logger.append_context_keys(compact=compact, provider_id=str(provider_id), cognito_sub=cognito_sub):
            # Parse and validate request body
            try:
                body = json.loads(event['body'])
                validated_body = MilitaryAuditRequestSchema().load(body)
            except json.JSONDecodeError as e:
                raise CCInvalidRequestException('Invalid JSON in request body') from e
            except ValidationError as e:
                raise CCInvalidRequestException(f'Invalid request body: {e.messages}') from e

            military_status_str = validated_body['militaryStatus']
            military_status_note = validated_body.get('militaryStatusNote')

            # Convert string to enum
            military_status = MilitaryAuditStatus(military_status_str)

            logger.info(
                'Processing military audit',
                military_status=military_status_str,
            )

            # Update provider and military affiliation records
            config.data_client.process_military_audit(
                compact=compact,
                provider_id=provider_id,
                military_status=military_status,
                military_status_note=military_status_note,
            )

            # Publish event for notification
            config.event_bus_client.publish_military_audit_event(
                source='org.compactconnect.provider-data',
                compact=compact,
                provider_id=provider_id,
                audit_result=military_status_str,
                audit_note=military_status_note,
            )

            logger.info('Military audit processed successfully')

            return {'message': 'OK'}
