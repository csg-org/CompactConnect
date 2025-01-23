import json
from datetime import timedelta

import requests
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from cc_common.config import config, logger
from cc_common.exceptions import (
    CCAccessDeniedException,
    CCAwsServiceException,
    CCInternalException,
    CCRateLimitingException,
)
from cc_common.utils import api_handler

# Module level variable for caching
_RECAPTCHA_SECRET = None


def _rate_limit_exceeded(ip_address: str) -> bool:
    """Check if the IP address has exceeded the rate limit.

    Returns:
        bool: True if rate limit is exceeded, False otherwise
    """
    now = config.current_standard_datetime
    window_start = now - timedelta(minutes=15)
    window_start_str = window_start.isoformat()

    try:
        # Query for requests in the last 15 minutes
        response = config.rate_limiting_table.query(
            KeyConditionExpression='pk = :pk AND sk BETWEEN :start_sk AND :end_sk',
            ExpressionAttributeValues={
                ':pk': f'IP#{ip_address}',
                ':start_sk': f'REGISTRATION#{window_start_str}',
                ':end_sk': f'REGISTRATION#{now.isoformat()}',
            },
            ConsistentRead=True,
        )

        # If there are 4 or more requests in the window, rate limit is exceeded
        if len(response.get('Items', [])) >= 3:
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


def get_recaptcha_secret() -> str:
    """Get the reCAPTCHA secret from Secrets Manager with module-level caching."""
    global _RECAPTCHA_SECRET
    if _RECAPTCHA_SECRET is None:
        logger.info('Loading reCAPTCHA secret')
        try:
            _RECAPTCHA_SECRET = json.loads(
                config.secrets_manager_client.get_secret_value(
                    SecretId=f'compact-connect/env/{config.environment_name}/recaptcha/token'
                )['SecretString']
            )['token']
        except Exception as e:
            logger.error('Failed to load reCAPTCHA secret', error=str(e))
            raise CCInternalException('Failed to load reCAPTCHA secret') from e
    return _RECAPTCHA_SECRET


def verify_recaptcha(token: str) -> bool:
    """Verify the reCAPTCHA token with Google's API."""
    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': get_recaptcha_secret(),
                'response': token,
            },
            timeout=5,
        )
        return response.json().get('success', False)
    except ClientError as e:
        logger.error('Failed to verify reCAPTCHA token', error=str(e))
        return False


@api_handler
def register_provider(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Endpoint for a practitioner to register an account with the system.

    :param event: Standard API Gateway event, API schema documented in the CDK ApiStack
    :param LambdaContext context:
    """
    # Get IP address from the request context
    source_ip = event['requestContext']['identity']['sourceIp']
    body = json.loads(event['body'])

    # Check rate limit before proceeding
    if _rate_limit_exceeded(source_ip):
        # log the minimal request data
        logger.warning(
            'Rate limit exceeded for ip address',
            compact=body['compact'],
            state=body['state'],
            given_name=body['givenName'],
            license_type=body['licenseType'],
            ip_address=source_ip,
        )
        raise CCRateLimitingException('Rate limit exceeded. Please try again later.')

    # Verify reCAPTCHA token
    if not verify_recaptcha(body['token']):
        logger.info('Invalid reCAPTCHA token', token=body['token'])
        raise CCAccessDeniedException('Invalid request')

    # Query license records
    try:
        license_records = config.data_client.query_license_records(
            compact=body['compact'],
            state=body['state'],
            family_name=body['familyName'],
            given_name=body['givenName'],
        )
    except Exception as e:
        logger.error('Failed to query license records', error=str(e))
        raise CCAwsServiceException('Failed to query license records') from e

    if not license_records:
        # log the minimal request data
        logger.info(
            'No license records found for request',
            compact=body['compact'],
            state=body['state'],
            given_name=body['givenName'],
            license_type=body['licenseType'],
        )
        return {'message': 'request processed'}

    # Find matching license record
    matching_record = config.data_client.find_matching_license_record(
        license_records,
        partial_ssn=body['partialSocial'],
        dob=body['dob'],
        license_type=body['licenseType'],
    )

    if not matching_record:
        logger.info(
            'No matching license record found for request',
            compact=body['compact'],
            state=body['state'],
            given_name=body['givenName'],
            license_type=body['licenseType'],
        )
        return {'message': 'request processed'}

    # Check if already registered by looking for home jurisdiction record
    # this is only created if the provider has registered previously
    home_jurisdiction = config.data_client.get_provider_home_jurisdiction_selection(
        compact=body['compact'],
        provider_id=matching_record['providerId'],
    )

    if home_jurisdiction:
        logger.warning(
            'Provider already registered', compact=body['compact'], provider_id=matching_record['providerId']
        )
        return {'message': 'request processed'}

    # Create home jurisdiction selection record first
    config.data_client.create_home_jurisdiction_selection(
        compact=body['compact'],
        provider_id=matching_record['providerId'],
        jurisdiction=body['state'],
    )

    # Create Cognito user
    try:
        config.cognito_client.admin_create_user(
            UserPoolId=config.provider_user_pool_id,
            Username=body['email'],
            UserAttributes=[
                {'Name': 'custom:compact', 'Value': body['compact']},
                {'Name': 'custom:providerId', 'Value': matching_record['providerId']},
                {'Name': 'email', 'Value': body['email']},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
        )
    except Exception as e:
        logger.error('Failed to create Cognito user', error=str(e))
        # Roll back home jurisdiction selection record
        config.data_client.rollback_home_jurisdiction_selection(
            compact=body['compact'],
            provider_id=matching_record['providerId'],
        )
        raise CCInternalException('Failed to create user account') from e

    return {'message': 'request processed'}
