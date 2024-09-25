import json

from aws_lambda_powertools.utilities.typing import LambdaContext

from handlers import user_client, user_api_schema
from utils import api_handler, get_event_scopes, validate_compact_in_scopes


@api_handler
def get_me(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Return a user by the sub in their token
    """
    compact = event['pathParameters']['compact']
    user_id = event['requestContext']['authorizer']['claims']['sub']
    scopes = get_event_scopes(event)

    validate_compact_in_scopes(scopes, compact)

    return user_api_schema.load(user_client.get_user(compact=compact, user_id=user_id))


@api_handler
def patch_me(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Edit a user's own attributes
    """
    compact = event['pathParameters']['compact']
    user_id = event['requestContext']['authorizer']['claims']['sub']
    scopes = get_event_scopes(event)

    validate_compact_in_scopes(scopes, compact)

    body = json.loads(event['body'])
    return user_api_schema.load(user_client.update_user_attributes(
        compact=compact,
        user_id=user_id,
        attributes=body['attributes']
    ))
