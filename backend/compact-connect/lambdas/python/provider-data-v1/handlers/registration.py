import json

import requests
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from cc_common.config import config, logger
from cc_common.exceptions import CCAccessDeniedException, CCAwsServiceException, CCInternalException
from cc_common.utils import api_handler

# Module level variable for caching
_RECAPTCHA_SECRET = None


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
    body = json.loads(event['body'])

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
            UserPoolId=config.user_pool_id,
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
