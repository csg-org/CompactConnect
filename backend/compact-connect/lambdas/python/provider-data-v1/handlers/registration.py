import json
from datetime import timedelta

import requests
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from cc_common.config import config, logger, metrics
from cc_common.data_model.schema.provider.api import ProviderRegistrationRequestSchema
from cc_common.exceptions import (
    CCAccessDeniedException,
    CCAwsServiceException,
    CCInternalException,
    CCInvalidRequestException,
    CCNotFoundException,
    CCRateLimitingException,
)
from cc_common.utils import api_handler
from marshmallow import ValidationError

RECAPTCHA_ATTEMPT_METRIC_NAME = 'recaptcha-attempt'
REGISTRATION_ATTEMPT_METRIC_NAME = 'registration-attempt'

# Module level variable for caching
_RECAPTCHA_SECRET = None


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
    if not compact_config.licensee_registration_enabled:
        logger.info(
            'Registration is not enabled for this compact', compact=body['compact'], environment=config.environment_name
        )
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException(
            f'Registration is not currently available for the {compact_config.compact_name} compact.'
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
        raise CCInvalidRequestException('Registration is not currently available for the specified state.') from e

    if not jurisdiction_config.licensee_registration_enabled:
        logger.info(
            'Registration is not enabled for this jurisdiction',
            compact=body['compact'],
            jurisdiction=body['jurisdiction'],
            environment=config.environment_name,
        )
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInvalidRequestException(
            f'Registration is not currently available for {jurisdiction_config.jurisdiction_name}.'
        )

    # Query license records for one matching on all provided fields
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

    # First check if the provider is already registered
    try:
        if config.data_client.provider_is_registered_in_compact_connect(
            compact=body['compact'],
            provider_id=matching_record['providerId'],
        ):
            logger.warning(
                'This provider is already registered in the system',
                compact=body['compact'],
                provider_id=matching_record['providerId'],
            )
            metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
            return {'message': 'request processed'}
    except Exception as e:
        logger.error('Failed to check if provider is registered', error=str(e))
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInternalException('Failed to check if provider is registered') from e

    # Create Cognito user
    try:
        response = config.cognito_client.admin_create_user(
            UserPoolId=config.provider_user_pool_id,
            Username=body['email'],
            UserAttributes=[
                {'Name': 'custom:compact', 'Value': body['compact']},
                {'Name': 'custom:providerId', 'Value': matching_record['providerId']},
                {'Name': 'email', 'Value': body['email']},
                {'Name': 'email_verified', 'Value': 'true'},
            ],
        )
        # Get the Cognito sub from the response
        cognito_sub = next((attr['Value'] for attr in response['User']['Attributes'] if attr['Name'] == 'sub'), None)
        if cognito_sub is None:
            logger.info('Failed to get cognito sub from response', response=response)
            raise CCInternalException('Failed to get cognito sub from response')

    except Exception as e:
        logger.error('Failed to create Cognito user', error=str(e))
        metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=0)
        raise CCInternalException('Failed to create user account') from e

    # Set registration values and create home jurisdiction selection in a transaction
    try:
        config.data_client.process_registration_values(
            compact=body['compact'],
            provider_id=matching_record['providerId'],
            cognito_sub=cognito_sub,
            email_address=body['email'],
            jurisdiction=body['jurisdiction'],
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

    logger.info('Registered user successfully', compact=body['compact'], provider_id=matching_record['providerId'])
    metrics.add_metric(name=REGISTRATION_ATTEMPT_METRIC_NAME, unit=MetricUnit.NoUnit, value=1)
    return {'message': 'request processed'}
