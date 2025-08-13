import json
import os
import uuid
from datetime import timedelta

import requests
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
    CCAwsServiceException,
    CCInternalException,
    CCInvalidRequestException,
)
from cc_common.utils import api_handler
from marshmallow import ValidationError

MFA_RECOVERY_INITIATE_ATTEMPT_METRIC = 'mfa-recovery-initiate'
MFA_RECOVERY_VERIFY_ATTEMPT_METRIC = 'mfa-recovery-verify'

# Module-level cache
_RECAPTCHA_SECRET = None


def _get_recaptcha_secret() -> str:
    global _RECAPTCHA_SECRET
    if _RECAPTCHA_SECRET is None:
        logger.info('Loading reCAPTCHA secret')
        try:
            _RECAPTCHA_SECRET = json.loads(
                config.secrets_manager_client.get_secret_value(
                    SecretId=f'compact-connect/env/{config.environment_name}/recaptcha/token'
                )['SecretString']
            )['token']
        except Exception as e:  # noqa: BLE001
            logger.error('Failed to load reCAPTCHA secret', error=str(e))
            raise CCAwsServiceException('Failed to load reCAPTCHA secret') from e
    return _RECAPTCHA_SECRET


def _verify_recaptcha(token: str) -> bool:
    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={'secret': _get_recaptcha_secret(), 'response': token},
            timeout=5,
        )
        return response.json().get('success', False)
    except Exception as e:  # noqa: BLE001
        logger.error('Failed to verify reCAPTCHA token', error=str(e))
        return False


def _per_ip_rate_limit_exceeded(ip_address: str) -> bool:
    now = config.current_standard_datetime
    window_start = now - timedelta(minutes=15)
    try:
        response = config.rate_limiting_table.query(
            KeyConditionExpression='pk = :pk AND sk BETWEEN :start_sk AND :end_sk',
            ExpressionAttributeValues={
                ':pk': f'IP#{ip_address}',
                ':start_sk': f'MFARECOVERY#{window_start.isoformat()}',
                ':end_sk': f'MFARECOVERY#{now.isoformat()}',
            },
            Select='COUNT',
            ConsistentRead=True,
        )
        return response['Count'] >= 3
    except ClientError as e:
        logger.error('Failed to query per-IP rate limit', error=str(e))
        # Fail closed to protect the endpoint
        return True


def _global_rate_limit_exceeded() -> bool:
    """
    Returns True if there are at least 3 requests across 5 or more distinct IPs in the last hour.
    """
    now = config.current_standard_datetime
    window_start = now - timedelta(hours=1)
    try:
        result = config.rate_limiting_table.query(
            KeyConditionExpression='pk = :pk AND sk BETWEEN :start_sk AND :end_sk',
            ExpressionAttributeValues={
                ':pk': 'RECOVERY_REQUESTS',
                ':start_sk': f'MFARECOVERY#{window_start.isoformat()}',
                ':end_sk': f'MFARECOVERY#{now.isoformat()}',
            },
            Select='ALL_ATTRIBUTES',
            ConsistentRead=True,
        )
        items = result.get('Items', [])
        ip_to_count: dict[str, int] = {}
        for item in items:
            ip = item.get('ip') or 'unknown'
            ip_to_count[ip] = ip_to_count.get(ip, 0) + 1
        ips_meeting_threshold = sum(1 for count in ip_to_count.values() if count >= 3)
        return ips_meeting_threshold >= 5
    except ClientError as e:
        logger.error('Failed to query global rate limit', error=str(e))
        # Fail closed
        return True


def _record_rate_limit_event(ip_address: str) -> None:
    now = config.current_standard_datetime
    try:
        # Per-IP record (15 min TTL)
        config.rate_limiting_table.put_item(
            Item={
                'pk': f'IP#{ip_address}',
                'sk': f'MFARECOVERY#{now.isoformat()}',
                'ttl': int(now.timestamp()) + 900,
            }
        )
        # Global record (1 hour TTL)
        config.rate_limiting_table.put_item(
            Item={
                'pk': 'RECOVERY_REQUESTS',
                'sk': f'MFARECOVERY#{now.isoformat()}#IP#{ip_address}',
                'ip': ip_address,
                'ttl': int(now.timestamp()) + 3600,
            }
        )
    except ClientError as e:
        logger.error('Failed to record rate limit event', error=str(e))


def _attempt_admin_password_auth(username: str, password: str) -> bool:
    try:
        client_id = os.environ['PROVIDER_USER_POOL_CLIENT_ID']
    except KeyError as e:
        logger.error('PROVIDER_USER_POOL_CLIENT_ID not configured', error=str(e))
        return False

    try:
        response = config.cognito_client.admin_initiate_auth(
            UserPoolId=config.provider_user_pool_id,
            ClientId=client_id,
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
def initiate_recovery(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    source_ip = event['requestContext']['identity']['sourceIp']

    try:
        body = ProviderAccountRecoveryInitiateRequestSchema().loads(event['body'])
    except ValidationError as e:
        logger.info('Invalid request body for account recovery initiate', errors=e.messages)
        # Always return generic success
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return {'message': 'request processed'}

    # Verify reCAPTCHA
    if not _verify_recaptcha(body['recaptchaToken']):
        logger.info('Invalid reCAPTCHA token for account recovery initiate', ip_address=source_ip)
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return {'message': 'request processed'}

    # Rate limiting checks (fail closed to generic 200)
    if _per_ip_rate_limit_exceeded(source_ip) or _global_rate_limit_exceeded():
        logger.warning('MFA recovery initiate rate limit exceeded', ip_address=source_ip)
        _record_rate_limit_event(source_ip)
        metrics.add_metric(name='mfa-recovery-rate-limit-throttles', unit=MetricUnit.Count, value=1)
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return {'message': 'request processed'}

    # Record this attempt for future rate limiting windows
    _record_rate_limit_event(source_ip)

    username = body['username']
    password = body['password']

    # Find matching license record
    try:
        matching_record = config.data_client.find_matching_license_record(
            compact=body['compact'],
            jurisdiction=body['jurisdiction'],
            family_name=body['familyName'],
            given_name=body['givenName'],
            partial_ssn=body['partialSocial'],
            dob=body['dob'],
            license_type=body['licenseType'],
        )
    except Exception as e:  # noqa: BLE001
        logger.error('Failed to search for matching license record', error=str(e))
        matching_record = None

    if not matching_record:
        logger.info('No matching license for account recovery initiate')
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return {'message': 'request processed'}

    # Resolve provider record and validate email
    try:
        provider_record = config.data_client.get_provider_top_level_record(
            compact=matching_record.compact, provider_id=matching_record.providerId
        )
        registered_email = provider_record.compactConnectRegisteredEmailAddress
        if registered_email is None or registered_email.lower() != username.lower():
            logger.info(
                'Provided email does not match registered email for provider', provider_id=matching_record.providerId
            )
            metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
            return {'message': 'request processed'}
    except Exception as e:  # noqa: BLE001
        logger.error('Failed to fetch provider record for account recovery', error=str(e))
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return {'message': 'request processed'}

    # Validate password against Cognito
    if not _attempt_admin_password_auth(username=username, password=password):
        logger.info('Password validation failed for account recovery initiate')
        metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        return {'message': 'request processed'}

    # Create recovery token and store on provider record
    recovery_uuid = str(uuid.uuid4())
    expiry_time = config.current_standard_datetime + timedelta(minutes=15)
    try:
        config.data_client.update_provider_account_recovery_data(
            compact=matching_record.compact,
            provider_id=matching_record.providerId,
            recovery_uuid=recovery_uuid,
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
            provider_id=matching_record.providerId,
            recovery_uuid=recovery_uuid,
        )
    except Exception as e:  # noqa: BLE001
        logger.error('Failed to send account recovery confirmation email', error=str(e))
        raise CCInternalException('Internal server error') from e

    metrics.add_metric(name=MFA_RECOVERY_INITIATE_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=1)
    return {'message': 'request processed'}


@api_handler
def verify_recovery(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    try:
        schema = ProviderAccountRecoveryVerifyRequestSchema()
        body = schema.loads(event['body'])
    except ValidationError as e:
        logger.warning('Invalid request body for account recovery verify', errors=e.messages)
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException('Invalid request') from e

    # Verify reCAPTCHA
    if not _verify_recaptcha(body['recaptchaToken']):
        logger.info('Invalid reCAPTCHA token for account recovery verify')
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCAccessDeniedException('Invalid request')

    compact = body['compact']
    provider_id = body['providerId']
    provided_recovery_uuid = body['recoveryUuid']

    # Load provider record and validate recovery UUID
    try:
        provider_record = config.data_client.get_provider_top_level_record(compact=compact, provider_id=provider_id)
    except Exception as e:  # noqa: BLE001
        logger.error('Failed to get provider record for account recovery verify', error=str(e))
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException('Invalid or expired recovery link') from e

    record_uuid = provider_record.recoveryUuid
    record_expiry = provider_record.recoveryExpiry
    current_email = provider_record.compactConnectRegisteredEmailAddress

    if not record_uuid or not record_expiry:
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException('Invalid or expired recovery link')

    if config.current_standard_datetime > record_expiry:
        # Clear expired data and return error
        try:
            config.data_client.clear_provider_account_recovery_data(compact=compact, provider_id=provider_id)
        except Exception as e:  # noqa: BLE001
            logger.error('Failed to clear expired recovery data', error=str(e))
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException('Invalid or expired recovery link')

    if provided_recovery_uuid != record_uuid:
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException('Invalid or expired recovery link')

    # Delete and recreate the Cognito user
    try:
        config.cognito_client.admin_delete_user(UserPoolId=config.provider_user_pool_id, Username=current_email)
    except ClientError as e:
        error_code = e.response['Error'].get('Code')
        # If user doesn't exist, continue with create, else raise exception
        if error_code != 'UserNotFoundException':
            logger.error('Failed to delete Cognito user during account recovery', error=str(e))
            metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
            raise CCAwsServiceException('Failed to reset account') from e

    try:
        config.cognito_client.admin_create_user(
            UserPoolId=config.provider_user_pool_id,
            Username=current_email,
            UserAttributes=[
                {'Name': 'custom:compact', 'Value': compact.lower()},
                {'Name': 'custom:providerId', 'Value': str(provider_id)},
                {'Name': 'email', 'Value': current_email},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
        )
    except ClientError as e:
        logger.error('Failed to create Cognito user during account recovery', error=str(e))
        metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=0)
        raise CCAwsServiceException('Failed to reset account') from e

    # Clear recovery fields
    try:
        config.data_client.clear_provider_account_recovery_data(compact=compact, provider_id=provider_id)
    except Exception as e:  # noqa: BLE001
        logger.error('Failed to clearing recovery id', error=str(e))
        # Continue; user account already reset; surface generic success

    logger.info('Account recovery completed successfully', compact=compact, provider_id=provider_id)
    metrics.add_metric(name=MFA_RECOVERY_VERIFY_ATTEMPT_METRIC, unit=MetricUnit.NoUnit, value=1)
    return {'message': 'request processed'}
