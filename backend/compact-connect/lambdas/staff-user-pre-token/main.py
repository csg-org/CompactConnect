import logging
import os

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from user_scopes import UserScopes

logger = Logger()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false').lower() == 'true' else logging.INFO)


@logger.inject_lambda_context()
def customize_scopes(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Customize the scopes in the access token before AWS generates and issues it"""
    logger.info('Received event', event=event)

    try:
        sub = event['request']['userAttributes']['sub']
    except KeyError as e:
        # This logic will only ever trigger in the event of a misconfiguration.
        # The Cognito Authorizer will validate all JWTs before ever calling this function.
        logger.error('Unauthenticated user access attempted!', exc_info=e)
        # Explicitly set this, to avoid future bugs
        event['response']['claimsAndScopeOverrideDetails'] = None
        return event

    try:
        scopes_to_add = UserScopes(sub)
        logger.debug('Adding scopes', scopes=scopes_to_add)
    # We want to catch almost any exception here, so we can gracefully return execution back to AWS
    except Exception as e:  # noqa: BLE001 broad-exception-caught
        logger.error('Error while getting user scopes!', exc_info=e)
        event['response']['claimsAndScopeOverrideDetails'] = None
        return event

    event['response']['claimsAndScopeOverrideDetails'] = {'accessTokenGeneration': {'scopesToAdd': list(scopes_to_add)}}

    return event
