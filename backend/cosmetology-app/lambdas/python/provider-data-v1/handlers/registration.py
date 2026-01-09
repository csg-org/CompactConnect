from datetime import timedelta

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from cc_common.config import config, logger, metrics
from cc_common.data_model.schema.license import LicenseData
from cc_common.data_model.schema.provider import ProviderData
from cc_common.data_model.schema.provider.api import ProviderRegistrationRequestSchema
from cc_common.exceptions import (
    CCAccessDeniedException,
    CCAwsServiceException,
    CCInternalException,
    CCInvalidRequestException,
    CCNotFoundException,
    CCRateLimitingException,
)
from cc_common.utils import api_handler, delayed_function, verify_recaptcha
from marshmallow import ValidationError

RECAPTCHA_ATTEMPT_METRIC_NAME = 'recaptcha-attempt'
REGISTRATION_ATTEMPT_METRIC_NAME = 'registration-attempt'


def _rate_limit_exceeded(ip_address: str) -> bool:
    """Check if the IP address has exceeded the rate limit.

    :return: True if rate limit is exceeded, False otherwise
    """
    now = config.current_standard_datetime
    window_start = now - timedelta(minutes=15)
    window_start_str = window_start.isoformat()

    try:
        # Query for count of requests in the last 15 minutes
        response = config.rate_limiting_table.query(
            KeyConditionExpression='pk = :pk AND sk BETWEEN :start_sk AND :end_sk',
            ExpressionAttributeValues={
                ':pk': f'IP#{ip_address}',
                ':start_sk': f'REGISTRATION#{window_start_str}',
                ':end_sk': f'REGISTRATION#{now.isoformat()}',
            },
            Select='COUNT',
            ConsistentRead=True,
        )

        # If there are 3 or more requests in the window, rate limit is exceeded
        if response['Count'] >= 3:
            logger.warning('Rate limit exceeded', ip_address=ip_address)
            return True

        # Add the current request
        config.rate_limiting_table.put_item(
            Item={
                'pk': f'IP#{ip_address}',
                'sk': f'REGISTRATION#{now.isoformat()}',
                'ttl': int(now.timestamp()) + 900,  # 15 minutes in seconds
            }
        )
        return False
    except ClientError as e:
        logger.error('Failed to check rate limit', error=str(e))
        raise CCAwsServiceException('Failed to check rate limit') from e


def _should_allow_reregistration(cognito_user: dict) -> bool:
    """Check if a user should be allowed to re-register based on their Cognito status.

    :param cognito_user: Cognito user response from admin_get_user
    :return: True if re-registration should be allowed
    """
    user_last_modified_date = cognito_user['UserLastModifiedDate']
    user_status = cognito_user['UserStatus']

    updated_over_one_day_ago = (config.current_standard_datetime - user_last_modified_date) > timedelta(days=1)
    in_force_change_password = user_status == 'FORCE_CHANGE_PASSWORD'

    return updated_over_one_day_ago and in_force_change_password


def _resend_invitation_and_complete(email: str) -> dict:
    """Resend invitation to existing user with same email and return response.

    :param email: Email address to resend invitation to
    :return: Response dictionary
    """
    logger.info('User re-registering with same email address. Resending invite.')
    config.cognito_client.admin_create_user(
        UserPoolId=config.provider_user_pool_id, Username=email, MessageAction='RESEND'
    )
    metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=1)
    return {'message': 'request processed'}


def _cleanup_old_registration(old_email: str, cognito_user: dict) -> None:
    """Delete old Cognito user to allow new registration.

    :param old_email: Email of the old registration to clean up
    :param cognito_user: Cognito user data for logging
    """
    try:
        logger.info(
            'User never completed registration flow for previous email and has provided new email for registration, '
            'deleting old Cognito user associated with previous email.',
            previous_email=old_email,
            user_create_date=cognito_user['UserCreateDate'].isoformat(),
            user_last_modified_date=cognito_user['UserLastModifiedDate'].isoformat(),
            user_status=cognito_user['UserStatus'],
        )
        config.cognito_client.admin_delete_user(UserPoolId=config.provider_user_pool_id, Username=old_email)
    except ClientError as delete_e:
        logger.error(
            'Failed to delete old Cognito user during re-registration', error=str(delete_e), old_email=old_email
        )
        # Continue with registration anyway


def _send_registration_attempt_notification_and_complete(registered_email: str, compact: str) -> dict:
    """Send registration attempt notification email and return completed response.

    :param registered_email: Email address registered in system
    :param compact: Compact name
    :return: Response dictionary
    """
    config.email_service_client.send_provider_multiple_registration_attempt_email(
        compact=compact, provider_email=registered_email
    )
    metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
    return {'message': 'request processed'}


@api_handler
@delayed_function(delay_seconds=2.0)
def register_provider(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Endpoint for a practitioner to register an account with the system.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    # Get IP address from the request context
    source_ip = event['requestContext']['identity']['sourceIp']

    # Parse and validate the request body using the schema
    try:
        schema = ProviderRegistrationRequestSchema()
        body = schema.loads(event['body'])
    except ValidationError as e:
        logger.warning('Invalid request body', errors=e.messages)
        raise CCInvalidRequestException(f'Invalid request: {e.messages}') from e

    # Check rate limit before proceeding
    if _rate_limit_exceeded(source_ip):
        # log the minimal request data
        logger.warning(
            'Rate limit exceeded for ip address',
            compact=body['compact'],
            jurisdiction=body['jurisdiction'],
            given_name=body['givenName'],
            family_name=body['familyName'],
            license_type=body['licenseType'],
            ip_address=source_ip,
        )
        metrics.add_metric(name='registration-rate-limit-throttles', unit=MetricUnit.Count, value=1)
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCRateLimitingException('Rate limit exceeded. Please try again later.')

    # Verify reCAPTCHA token
    if not verify_recaptcha(body['token']):
        logger.info(
            'Invalid reCAPTCHA token',
            token=body['token'],
            compact=body['compact'],
            jurisdiction=body['jurisdiction'],
            given_name=body['givenName'],
            family_name=body['familyName'],
            license_type=body['licenseType'],
            ip_address=source_ip,
        )
        metrics.add_metric(name=RECAPTCHA_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCAccessDeniedException('Invalid request')

    metrics.add_metric(name=RECAPTCHA_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=1)

    # Get configuration for compact and jurisdiction
    try:
        compact_config = config.compact_configuration_client.get_compact_configuration(body['compact'])
    except CCNotFoundException as e:
        # In theory, this should never happen, since we should only specify license types that are supported in the
        # specific environment. But an end user might pass in invalid data through an api call.
        logger.error('Specified compact not configured', compact=body['compact'], environment=config.environment_name)
        raise CCInvalidRequestException(
            'Registration is not currently available for the specified license type.'
        ) from e

    # Check if registration is enabled for both compact and jurisdiction
    # If registration is not enabled for either the compact or jurisdiction, return an error
    if not compact_config.licenseeRegistrationEnabled:
        logger.info(
            'Registration is not enabled for this compact', compact=body['compact'], environment=config.environment_name
        )
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException(
            f'Registration is not currently available for the {compact_config.compactName} compact.'
        )

    try:
        jurisdiction_config = config.compact_configuration_client.get_jurisdiction_configuration(
            body['compact'], body['jurisdiction']
        )
    except CCNotFoundException as e:
        logger.info(
            'Specified state not found in configured jurisdictions for compact',
            compact=body['compact'],
            jurisdiction=body['jurisdiction'],
            environment=config.environment_name,
        )
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException('Registration is not currently available for the specified state.') from e

    # Check if the jurisdiction is configured and live in the compact's configuredStates
    configured_state = next(
        (
            configured_state
            for configured_state in compact_config.configuredStates
            if configured_state['postalAbbreviation'].lower() == body['jurisdiction'].lower()
        ),
        None,
    )

    if not configured_state:
        logger.info(
            'Jurisdiction not found in compact configured states',
            compact=body['compact'],
            jurisdiction=body['jurisdiction'],
            environment=config.environment_name,
        )
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException(
            f'Registration is not currently available for {jurisdiction_config.jurisdictionName}.'
        )

    if not configured_state['isLive']:
        logger.info(
            'Jurisdiction is not live for registration',
            compact=body['compact'],
            jurisdiction=body['jurisdiction'],
            is_live=configured_state['isLive'],
            environment=config.environment_name,
        )
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException(
            f'Registration is not currently available for {jurisdiction_config.jurisdictionName}.'
        )

    # Query license records for one matching on all provided fields
    matching_record: LicenseData = config.data_client.find_matching_license_record(
        compact=body['compact'],
        jurisdiction=body['jurisdiction'],
        family_name=body['familyName'],
        given_name=body['givenName'],
        partial_ssn=body['partialSocial'],
        dob=body['dob'],
        license_type=body['licenseType'],
    )

    if not matching_record:
        logger.info(
            'No matching license record found for request',
            compact=body['compact'],
            jurisdiction=body['jurisdiction'],
            given_name=body['givenName'],
            family_name=body['familyName'],
            license_type=body['licenseType'],
        )
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        return {'message': 'request processed'}

    # Check if provider already has registered email
    try:
        provider_record: ProviderData = config.data_client.get_provider_top_level_record(
            compact=matching_record.compact, provider_id=matching_record.providerId
        )

        if provider_record.compactConnectRegisteredEmailAddress is not None:
            registered_email = provider_record.compactConnectRegisteredEmailAddress

            # Get Cognito user to check status
            try:
                cognito_user = config.cognito_client.admin_get_user(
                    UserPoolId=config.provider_user_pool_id, Username=registered_email
                )

                if _should_allow_reregistration(cognito_user):
                    # Same email: resend invitation and complete
                    if registered_email == body['email']:
                        return _resend_invitation_and_complete(body['email'])

                    # Different email: cleanup account and then proceed with registration for provided email
                    _cleanup_old_registration(registered_email, cognito_user)
                else:
                    logger.warning(
                        'User attempted to register for account with existing registered email.',
                        compact=matching_record.compact,
                        provider_id=matching_record.providerId,
                        user_create_date=cognito_user['UserCreateDate'].isoformat(),
                        user_last_modified_date=cognito_user['UserLastModifiedDate'].isoformat(),
                        user_status=cognito_user['UserStatus'],
                        in_force_change_password=cognito_user['UserStatus'] == 'FORCE_CHANGE_PASSWORD',
                    )
                    return _send_registration_attempt_notification_and_complete(registered_email, body['compact'])

            except ClientError as cognito_e:
                if cognito_e.response['Error']['Code'] == 'UserNotFoundException':
                    logger.error(
                        'Provider record shows registered email but Cognito user not found, '
                        'continuing with registration.',
                        compact=matching_record.compact,
                        provider_id=matching_record.providerId,
                    )
                    # Continue with normal registration flow
                else:
                    logger.error('Failed to check Cognito user status', error=str(cognito_e))
                    raise CCInternalException('Failed to check user registration status') from cognito_e

    except CCNotFoundException as e:
        logger.error(
            'Provider license record was found, but no provider record was found.',
            compact=matching_record.compact,
            provider_id=matching_record.providerId,
        )
        raise CCInternalException('Failed to check if provider is registered') from e
    except Exception as e:
        logger.error('Failed to check if provider is registered', error=str(e))
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInternalException('Failed to check if provider is registered') from e

    # Create Cognito user
    try:
        config.cognito_client.admin_create_user(
            UserPoolId=config.provider_user_pool_id,
            Username=body['email'],
            UserAttributes=[
                {'Name': 'custom:compact', 'Value': matching_record.compact.lower()},
                {'Name': 'custom:providerId', 'Value': str(matching_record.providerId)},
                {'Name': 'email', 'Value': body['email']},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'UsernameExistsException':
            logger.info(
                'User attempted to register with existing Cognito email for different license.',
                compact=body['compact'],
                provider_id=matching_record.providerId,
                license_type=body['licenseType'],
            )
            return _send_registration_attempt_notification_and_complete(
                registered_email=body['email'], compact=body['compact']
            )

        logger.error('Failed to create Cognito user', error=str(e))
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInternalException('Failed to create user account') from e
    except Exception as e:
        logger.error('Failed to create Cognito user', error=str(e))
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInternalException('Failed to create user account') from e

    # Set registration values and create home jurisdiction selection in a transaction
    try:
        config.data_client.process_registration_values(
            current_provider_record=provider_record,
            matched_license_record=matching_record,
            email_address=body['email'],
        )
    except Exception as e:
        logger.error('Failed to set registration values, rolling back cognito user creation', error=str(e))
        # Roll back Cognito user creation
        try:
            config.cognito_client.admin_delete_user(
                UserPoolId=config.provider_user_pool_id,
                Username=body['email'],
            )
        except ClientError as cognito_e:
            logger.error('Failed to roll back Cognito user creation', error=str(cognito_e))
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInternalException('Failed to set registration values') from e

    logger.info('Registered user successfully', compact=body['compact'], provider_id=matching_record.providerId)
    metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=1)
    return {'message': 'request processed'}
