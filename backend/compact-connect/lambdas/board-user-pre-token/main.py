
import logging
import os

from aws_lambda_powertools import Logger


logger = Logger()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false').lower() == 'true' else logging.INFO)


@logger.inject_lambda_context()
def customize_scopes(event, context):  # pylint: disable=unused-argument
    logger.info('Received event', event=event)

    try:
        compact = event['request']['userAttributes']['custom:compact']
        jurisdiction = event['request']['userAttributes']['custom:jurisdiction']
    except KeyError as e:
        logger.debug('User with missing board attribute', attribute=str(e))
        # Explicitly set this, to avoid future bugs
        event['response']['claimsAndScopeOverrideDetails'] = None
        return event

    scopes = [f'{compact}/{jurisdiction}']
    logger.debug('Adding scope', scopes=scopes)

    event['response']['claimsAndScopeOverrideDetails'] = {
        'accessTokenGeneration': {
            'scopesToAdd': scopes
        }
    }

    return event
