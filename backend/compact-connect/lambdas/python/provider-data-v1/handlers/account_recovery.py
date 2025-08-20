import secrets
from datetime import timedelta

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from cc_common.config import config, logger, metrics
from cc_common.data_model.schema.provider.api import (
    ProviderAccountRecoveryInitiateRequestSchema,
    ProviderAccountRecoveryVerifyRequestSchema,
)
from cc_common.exceptions import (
    CCAccessDeniedException,
    CCInternalException,
    CCInvalidRequestException,
    CCNotFoundException,
    CCRateLimitingException,
)
from cc_common.utils import api_handler, verify_recaptcha
from marshmallow import ValidationError

MFA_RECOVERY_INITIATE_ATTEMPT_METRIC = 'mfa-recovery-initiate'
MFA_RECOVERY_VERIFY_ATTEMPT_METRIC = 'mfa-recovery-verify'

GENERIC_REQUEST_PROCESSED_RESPONSE = {'message': 'request processed'}
GENERIC_INVALID_REQUEST_MESSAGE = 'Invalid or expired recovery link'


def _provider_rate_limit_exceeded(*, compact: str, provider_id: str) -> bool:
    """Limit to 3 requests per provider within the last hour."""
    now = config.current_standard_datetime
    window_start = now - timedelta(hours=1)
    try:
        response = config.rate_limiting_table.query(
            KeyConditionExpression='pk = :pk AND sk BETWEEN :start_sk AND :end_sk',
            ExpressionAttributeValues={
                ':pk': f'PROVIDER#{compact.lower()}#{provider_id}',
                ':start_sk': f'MFARECOVERY#{window_start.isoformat()}',
                ':end_sk': f'MFARECOVERY#{now.isoformat()}',
            },
            Select='COUNT',
            ConsistentRead=True,
        )
        return response['Count'] > 3
    except ClientError as e:
        logger.error('Failed to query provider rate limit', error=str(e))
        # Fail closed to protect endpoint
        return True


def _record_provider_rate_limit_event(*, compact: str, provider_id: str) -> None:
    now = config.current_standard_datetime
    try:
        config.rate_limiting_table.put_item(
            Item={
                'pk': f'PROVIDER#{compact.lower()}#{provider_id}',
                'sk': f'MFARECOVERY#{now.isoformat()}',
                'ttl': int(now.timestamp()) + 3600,
            }
        )
    except ClientError as e:
        logger.error('Failed to record provider rate limit event', error=str(e))
        # we will fail here, since we don't want rate-limiting to silently fail
        raise CCInternalException('Internal Server Error') from e


def _attempt_admin_password_auth(username: str, password: str) -> bool:
    try:
        response = config.cognito_client.admin_initiate_auth(
            UserPoolId=config.provider_user_pool_id,
            ClientId=config.provider_user_pool_ui_client_id,
            AuthFlow='ADMIN_USER_PASSWORD_AUTH',
            AuthParameters={'USERNAME': username, 'PASSWORD': password},
        )
        # Successful auth yields AuthenticationResult or a challenge (we only care that password was correct)
        return 'ChallengeName' in response or 'AuthenticationResult' in response
    except ClientError as e:
        error_code = e.response['Error'].get('Code')
        logger.info('Cognito admin_initiate_auth failed', username=username, error_code=error_code)
        return False


@api_handler
def initiate_account_recovery(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    source_ip = event['requestContext']['identity']['sourceIp']

    try:
        body = ProviderAccountRecoveryInitiateRequestSchema().loads(event['body'])
    except ValidationError as e:
        logger.info('Invalid request body for account recovery initiate', errors=e.messages)
        # Always return generic success
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return GENERIC_REQUEST_PROCESSED_RESPONSE

    # Verify reCAPTCHA
    if not verify_recaptcha(body['recaptchaToken']):
        logger.info('Invalid reCAPTCHA token for account recovery initiate', ip_address=source_ip)
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return GENERIC_REQUEST_PROCESSED_RESPONSE

    logger.info('reCaptcha token verified, checking for matching license record.', ip_address=source_ip)

    username = body['username']
    password = body['password']

    # Find matching license record
    matching_record = config.data_client.find_matching_license_record(
        compact=body['compact'],
        jurisdiction=body['jurisdiction'],
        family_name=body['familyName'],
        given_name=body['givenName'],
        partial_ssn=body['partialSocial'],
        dob=body['dob'],
        license_type=body['licenseType'],
    )

    if not matching_record:
        logger.info('No matching license for account recovery initiate')
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return GENERIC_REQUEST_PROCESSED_RESPONSE

    # license matched, record attempt against this particular provider for rate-limiting
    # Provider-based rate limiting (3 per hour)
    _record_provider_rate_limit_event(compact=matching_record.compact, provider_id=str(matching_record.providerId))
    if _provider_rate_limit_exceeded(compact=matching_record.compact, provider_id=str(matching_record.providerId)):
        logger.warning(
            'MFA recovery initiate provider rate limit exceeded',
            compact=matching_record.compact,
            provider_id=matching_record.providerId,
        )
        metrics.add_metric(name='mfa-recovery-rate-limit-throttles', unit=MetricUnit.Count, value=1)
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return GENERIC_REQUEST_PROCESSED_RESPONSE



    # Resolve provider record and validate email
    provider_record = config.data_client.get_provider_top_level_record(
        compact=matching_record.compact, provider_id=matching_record.providerId
    )
    registered_email = provider_record.compactConnectRegisteredEmailAddress
    if registered_email is None:
        logger.info(
            'Provided has no registered email address. '
            'Provider must be registered before attempting to recover account',
            provider_id=matching_record.providerId,
        )
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return GENERIC_REQUEST_PROCESSED_RESPONSE
    if registered_email.lower() != username.lower():
        logger.info(
            'Provided email does not match registered email for provider', provider_id=matching_record.providerId
        )
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return GENERIC_REQUEST_PROCESSED_RESPONSE

    # Validate password against Cognito
    if not _attempt_admin_password_auth(username=username, password=password):
        logger.info('Password validation failed for account recovery initiate')
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return GENERIC_REQUEST_PROCESSED_RESPONSE

    logger.info('Password authentication verified. Generating temporary recovery token.')

    # Create cryptographically secure, URL-safe recovery token and store on provider record
    # 32 bytes ~ 43 URL-safe chars; sufficient entropy for email deep links
    recovery_token = secrets.token_urlsafe(32)
    expiry_time = config.current_standard_datetime + timedelta(minutes=15)
    try:
        config.data_client.update_provider_account_recovery_data(
            compact=matching_record.compact,
            provider_id=matching_record.providerId,
            recovery_token=recovery_token,
            recovery_expiry=expiry_time,
        )
    except Exception as e:  # noqa: BLE001
        logger.error('Failed to update provider recovery data', error=str(e))
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCInternalException('Internal server error') from e

    # Send email with confirmation link
    try:
        config.email_service_client.send_provider_account_recovery_confirmation_email(
            compact=matching_record.compact,
            provider_email=registered_email,
            provider_id=str(matching_record.providerId),
            recovery_token=recovery_token,
        )
    except Exception as e:  # noqa: BLE001
        logger.error('Failed to send account recovery confirmation email', error=str(e))
        raise CCInternalException('Internal server error') from e

    metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=1)
    return GENERIC_REQUEST_PROCESSED_RESPONSE


def _provider_verify_rate_limit_exceeded(*, compact: str, provider_id: str) -> bool:
    """Limit to 2 verification requests per provider within the last 15 minutes."""
    now = config.current_standard_datetime
    window_start = now - timedelta(minutes=15)
    try:
        response = config.rate_limiting_table.query(
            KeyConditionExpression='pk = :pk AND sk BETWEEN :start_sk AND :end_sk',
            ExpressionAttributeValues={
                ':pk': f'PROVIDER#{compact.lower()}#{provider_id}',
                ':start_sk': f'MFARECOVERYVERIFY#{window_start.isoformat()}',
                ':end_sk': f'MFARECOVERYVERIFY#{now.isoformat()}',
            },
            Select='COUNT',
            ConsistentRead=True,
        )
        return response['Count'] > 2
    except ClientError as e:
        logger.error('Failed to query provider verify rate limit', error=str(e))
        # Fail closed
        return True


def _record_provider_verify_rate_limit_event(*, compact: str, provider_id: str) -> None:
    now = config.current_standard_datetime
    try:
        config.rate_limiting_table.put_item(
            Item={
                'pk': f'PROVIDER#{compact.lower()}#{provider_id}',
                'sk': f'MFARECOVERYVERIFY#{now.isoformat()}',
                'ttl': int(now.timestamp()) + 900,
            }
        )
    except ClientError as e:
        logger.error('Failed to record provider verify rate limit event', error=str(e))
        # we will fail here, since we don't want rate-limiting to silently fail
        raise CCInternalException('Internal Server Error') from e


def _validate_token_or_raise_exception(
    compact: str, provider_id: str, record_token: str, record_expiry: str, token_from_request: str
):
    if not record_token or not record_expiry:
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException(GENERIC_INVALID_REQUEST_MESSAGE)

    if config.current_standard_datetime > record_expiry:
        # Clear expired data and return error
        logger.info('token is expired, clearing expired recovery fields.')
        config.data_client.clear_provider_account_recovery_data(compact=compact, provider_id=provider_id)
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException(GENERIC_INVALID_REQUEST_MESSAGE)

    if token_from_request != record_token:
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException(GENERIC_INVALID_REQUEST_MESSAGE)


def _recreate_cognito_user(compact: str, provider_id: str, email: str):
    try:
        config.cognito_client.admin_delete_user(UserPoolId=config.provider_user_pool_id, Username=email)
    except ClientError as e:
        error_code = e.response['Error'].get('Code')
        # If user doesn't exist, continue with create, else raise exception
        if error_code != 'UserNotFoundException':
            logger.error('Failed to delete Cognito user during account recovery', error=str(e))
            raise CCInternalException('Failed to reset current account') from e

        logger.warning('User cognito account not found, proceeding with account creation.', provider_id=provider_id)

    try:
        # recreate the user, which will send them a new temp password for them to log in, set a permanent password,
        # and then set a new MFA option.
        config.cognito_client.admin_create_user(
            UserPoolId=config.provider_user_pool_id,
            Username=email,
            UserAttributes=[
                {'Name': 'custom:compact', 'Value': compact.lower()},
                {'Name': 'custom:providerId', 'Value': str(provider_id)},
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
        )
    except ClientError as e:
        logger.error('Failed to create Cognito user during account recovery', error=str(e))
        raise CCInternalException('Failed to reset account') from e


@api_handler
def verify_account_recovery(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    try:
        body = ProviderAccountRecoveryVerifyRequestSchema().loads(event['body'])
    except ValidationError as e:
        logger.warning('Invalid request body for account recovery verify', errors=e.messages)
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException(GENERIC_INVALID_REQUEST_MESSAGE) from e

    # Verify reCAPTCHA
    if not verify_recaptcha(body['recaptchaToken']):
        logger.info('Invalid reCAPTCHA token for account recovery verify')
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCAccessDeniedException(GENERIC_INVALID_REQUEST_MESSAGE)

    compact = body['compact']
    provider_id = body['providerId']
    # Provider-based rate limiting for verification (2 per 15 minutes)
    _record_provider_verify_rate_limit_event(compact=compact, provider_id=str(provider_id))
    if _provider_verify_rate_limit_exceeded(compact=compact, provider_id=str(provider_id)):
        logger.warning('MFA recovery verify provider rate limit exceeded', compact=compact, provider_id=provider_id)
        metrics.add_metric(name='mfa-recovery-rate-limit-throttles', unit=MetricUnit.Count, value=1)
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCRateLimitingException('Please try again later.')

    # Load provider record and validate recovery token
    try:
        provider_record = config.data_client.get_provider_top_level_record(compact=compact, provider_id=provider_id)
    except CCNotFoundException as e:  # noqa: BLE001
        logger.info('Provider record not found for provided id', error=str(e), provider_id=provider_id)
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException(GENERIC_INVALID_REQUEST_MESSAGE) from e

    _validate_token_or_raise_exception(
        compact=compact,
        provider_id=provider_id,
        record_token=provider_record.recoveryToken,
        record_expiry=provider_record.recoveryExpiry,
        token_from_request=body['recoveryToken'],
    )

    # token passed validation, recreating the cognito user to reset account
    _recreate_cognito_user(
        compact=compact, provider_id=provider_id, email=provider_record.compactConnectRegisteredEmailAddress
    )

    # Clear recovery fields
    config.data_client.clear_provider_account_recovery_data(compact=compact, provider_id=provider_id)

    logger.info('Account recovery completed successfully', compact=compact, provider_id=provider_id)
    metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=1)
    return GENERIC_REQUEST_PROCESSED_RESPONSE
