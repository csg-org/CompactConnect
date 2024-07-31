
import logging
import os

from aws_lambda_powertools import Logger

from config import config

logger = Logger()
logger.setLevel(logging.DEBUG if os.environ.get('DEBUG', 'false').lower() == 'true' else logging.INFO)


@logger.inject_lambda_context()
def customize_scopes(event, context):  # pylint: disable=unused-argument
    """
    Customize the scopes in the access token before AWS generates and issues it
    """
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
        scopes_to_add = get_scopes_from_db(sub)
        logger.debug('Adding scopes', scopes=scopes_to_add)
    # We want to catch almost any exception here, so we can gracefully return execution back to AWS
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error('Error while getting user scopes!', exc_info=e)
        event['response']['claimsAndScopeOverrideDetails'] = None
        return event

    event['response']['claimsAndScopeOverrideDetails'] = {
        'accessTokenGeneration': {
            'scopesToAdd': list(scopes_to_add)
        }
    }

    return event


def get_scopes_from_db(sub: str) -> set[str]:
    """
    Parse the user's database record to calculate scopes.

    Note: See the accompanying unit tests for expected db record shape.
    :param sub: The `sub` field value from the Cognito Authorizer (which gets it from the JWT)
    """
    try:
        user_data = config.users_table.get_item(Key={'pk': sub})['Item']
    except KeyError as e:
        logger.error('Authenticated user not found!', exc_info=e, sub=sub)
        raise RuntimeError('Authenticated user not found!') from e

    permissions = user_data.get('permissions', {})
    scopes_to_add = set()

    # Ensure included compacts are limited to supported values
    disallowed_compcats = permissions.keys() - config.compacts
    if disallowed_compcats:
        raise ValueError(f'User permissions include disallowed compacts: {disallowed_compcats}')

    for compact_name, compact_permissions in permissions.items():
        # Compact-level permissions
        compact_actions = compact_permissions.get('actions', set())

        # Ensure included actions are limited to supported values
        disallowed_actions = compact_actions - {'read', 'admin'}
        if disallowed_actions:
            raise ValueError(f'User {compact_name} permissions include disallowed actions: {disallowed_actions}')

        for action in compact_actions:
            scopes_to_add.add(f'{compact_name}/{action}')

        # Ensure included jurisdictions are limited to supported values
        jurisdictions = compact_permissions['jurisdictions']
        disallowed_jurisdictions = jurisdictions.keys() - config.jurisdictions
        if disallowed_jurisdictions:
            raise ValueError(
                f'User {compact_name} permissions include disallowed jurisdictions: {disallowed_jurisdictions}'
            )

        for jurisdiction_name, jurisdiction_permissions in compact_permissions['jurisdictions'].items():
            # Jurisdiction-level permissions
            jurisdiction_actions = jurisdiction_permissions.get('actions', set())

            # Ensure included actions are limited to supported values
            disallowed_actions = jurisdiction_actions - {'write', 'admin'}
            if disallowed_actions:
                raise ValueError(
                    f'User {compact_name}/{jurisdiction_name} permissions include disallowed actions: '
                    f'{disallowed_actions}'
                )
            for action in jurisdiction_actions:
                scopes_to_add.add(f'{compact_name}/{jurisdiction_name}.{action}')
    return scopes_to_add
