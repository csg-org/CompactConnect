import logging
import os

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config
from cc_common.data_model.schema.common import StaffUserStatus
from user_data import UserData

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
        user_data = UserData(sub)
        logger.debug('Adding scopes', scopes=user_data.scopes)

        # Get all the user's records and set their status to active
        for record in user_data.records:
            # Only update the status if it's not already active
            if record['status'] != StaffUserStatus.ACTIVE.value:
                config.users_table.update_item(
                    Key={'pk': record['pk'], 'sk': record['sk']},
                    UpdateExpression='SET #status = :status',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':status': StaffUserStatus.ACTIVE.value},
                )

    # We want to catch almost any exception here, so we can gracefully return execution back to AWS
    except Exception as e:  # noqa: BLE001 broad-exception-caught
        logger.error('Error while getting user scopes!', exc_info=e)
        event['response']['claimsAndScopeOverrideDetails'] = None
        return event

    event['response']['claimsAndScopeOverrideDetails'] = {
        'accessTokenGeneration': {
            'scopesToAdd': list(user_data.scopes),
            # we explicitly suppress the cognito admin scope,
            # so they cannot change their email directly with the Cognito API
            'scopesToSuppress': ['aws.cognito.signin.user.admin'],
        }
    }

    return event
