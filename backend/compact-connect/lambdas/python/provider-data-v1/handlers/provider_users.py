import json
import uuid

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.fields import OTHER_JURISDICTION
from cc_common.data_model.schema.military_affiliation.api import PostMilitaryAffiliationResponseSchema
from cc_common.data_model.schema.military_affiliation.common import (
    MILITARY_AFFILIATIONS_DOCUMENT_TYPE_KEY_NAME,
    SUPPORTED_MILITARY_AFFILIATION_FILE_EXTENSIONS,
    MilitaryAffiliationType,
)
from cc_common.data_model.schema.military_affiliation.record import MilitaryAffiliationRecordSchema
from cc_common.exceptions import CCInternalException, CCInvalidRequestException, CCNotFoundException
from cc_common.utils import api_handler

from . import get_provider_information


@api_handler
def provider_users_api_handler(event: dict, context: LambdaContext):
    """
    Main entry point for provider users API.
    Routes to the appropriate handler based on the HTTP method and resource path.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param context: Lambda context
    """
    # Extract the HTTP method and resource path
    http_method = event.get('httpMethod')
    resource_path = event.get('resource')

    # Route to the appropriate handler
    api_method = (http_method, resource_path)
    match api_method:
        case ('GET', '/v1/provider-users/me'):
            return get_provider_user_me(event, context)
        case ('POST', '/v1/provider-users/me/military-affiliation'):
            return _post_provider_military_affiliation(event, context)
        case ('PATCH', '/v1/provider-users/me/military-affiliation'):
            return _patch_provider_military_affiliation(event, context)
        case ('PUT', '/v1/provider-users/me/home-jurisdiction'):
            return _put_provider_home_jurisdiction(event, context)

    # If we get here, the method/resource combination is not supported
    raise CCInvalidRequestException(f'Unsupported method or resource: {http_method} {resource_path}')


def _check_provider_user_attributes(event: dict) -> tuple[str, str]:
    try:
        # the two values for compact and providerId are stored as custom attributes in the user's cognito claims
        # so we can access them directly from the event object
        compact = event['requestContext']['authorizer']['claims']['custom:compact']
        provider_id = event['requestContext']['authorizer']['claims']['custom:providerId']
    except (KeyError, TypeError) as e:
        # This shouldn't happen unless a provider user was created without these custom attributes.
        logger.error(f'Missing custom provider attribute: {e}')
        raise CCInvalidRequestException('Missing required user profile attribute') from e

    return compact, provider_id


def get_provider_user_me(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Endpoint for a provider user to fetch their personal provider data.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    compact, provider_id = _check_provider_user_attributes(event)

    try:
        return get_provider_information(compact=compact, provider_id=provider_id)
    except CCNotFoundException as e:
        message = 'Failed to find provider using provided claims'
        logger.error(message, compact=compact, provider_id=provider_id)
        raise CCInternalException(message) from e


def _put_provider_home_jurisdiction(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """
    Handle the PUT method for updating a provider's home jurisdiction.

    :param event: API Gateway event
    :param context: Lambda context
    :return: Success message
    """
    # Parse the request body
    event_body = json.loads(event['body'])

    selected_jurisdiction = event_body['jurisdiction'].lower()

    # ensure selected_jurisdiction is one of the known jurisdictions or the word 'other':
    if selected_jurisdiction not in config.jurisdictions and selected_jurisdiction != OTHER_JURISDICTION:
        raise CCInvalidRequestException('Invalid jurisdiction selected.')

    compact, provider_id = _check_provider_user_attributes(event)

    # Log the request
    logger.info(
        'Handling request to update provider home jurisdiction',
        compact=compact,
        provider_id=provider_id,
        new_jurisdiction=selected_jurisdiction,
    )

    try:
        config.data_client.update_provider_home_state_jurisdiction(
            compact=compact, provider_id=provider_id, selected_jurisdiction=selected_jurisdiction
        )
    except CCInternalException as e:
        logger.error(
            'Failed to update provider home jurisdiction',
            compact=compact,
            provider_id=provider_id,
            new_jurisdiction=selected_jurisdiction,
            error=str(e),
        )
        raise

    return {'message': 'ok'}


def _post_provider_military_affiliation(event, context):  # noqa: ARG001 unused-argument
    """
    Handle the POST method for updating a provider's military affiliation.
    Creates a new military affiliation record and generates a S3 pre-signed URL for the user to upload their document.
    """
    compact, provider_id = _check_provider_user_attributes(event)

    s3_document_prefix = (
        f'compact/{compact}/provider/{provider_id}/document-type/'
        f'{MILITARY_AFFILIATIONS_DOCUMENT_TYPE_KEY_NAME}/{config.current_standard_datetime.date().isoformat()}/'
    )

    event_body = json.loads(event['body'])
    file_names: list[str] = event_body['fileNames']
    document_keys = []
    document_upload_fields = []
    # verify all files use supported file extensions
    for file_name in file_names:
        file_name_without_extension, file_extension = file_name.rsplit('.', 1)
        if file_extension.lower() not in [ext.lower() for ext in SUPPORTED_MILITARY_AFFILIATION_FILE_EXTENSIONS]:
            raise CCInvalidRequestException(
                f'Invalid file type "{file_extension}" The following file types '
                f'are supported: {SUPPORTED_MILITARY_AFFILIATION_FILE_EXTENSIONS}'
            )

        # generate a UUID for the document key, which includes a random UUID followed by the filename
        # and the file extension
        document_uuid = f'{uuid.uuid4()}#{file_name_without_extension}.{file_extension.lower()}'
        document_key = s3_document_prefix + document_uuid
        document_keys.append(document_key)

        # generate a pre-signed url to allow the client to upload all the files in fileNames
        pre_signed_post_response = config.s3_client.generate_presigned_post(
            Bucket=config.provider_user_bucket_name,
            Key=document_key,
            Conditions=[
                # max file size is 10MB
                ['content-length-range', 0, 10485760],
            ],
            # the pre-signed URL will expire in 10 minutes
            ExpiresIn=600,
        )
        document_upload_fields.append(pre_signed_post_response)

    # save the military affiliation record to the database
    military_affiliation_record = config.data_client.create_military_affiliation(
        compact=compact,
        provider_id=provider_id,
        affiliation_type=MilitaryAffiliationType(event_body['affiliationType']),
        file_names=file_names,
        document_keys=document_keys,
    )
    # serialize the response
    serialized_record = MilitaryAffiliationRecordSchema().dump(military_affiliation_record)
    # In the case of post, we need to return the pre-signed post response to the client
    serialized_record['documentUploadFields'] = document_upload_fields

    return PostMilitaryAffiliationResponseSchema().load(serialized_record)


def _patch_provider_military_affiliation(event, context):  # noqa: ARG001 unused-argument
    """
    Handle the PATCH method for updating a provider's military affiliation.
    Updates the status of the user's military affiliation.
    """
    compact, provider_id = _check_provider_user_attributes(event)

    event_body = json.loads(event['body'])
    # we only accept the status field with the value of 'inactive'
    if event_body.get('status') != 'inactive':
        raise CCInvalidRequestException('Invalid status value. Only "inactive" is allowed.')

    config.data_client.inactivate_military_affiliation_status(compact=compact, provider_id=provider_id)

    return {'message': 'Military affiliation updated successfully'}
