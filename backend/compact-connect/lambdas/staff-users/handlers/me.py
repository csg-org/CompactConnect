import json

from aws_lambda_powertools.utilities.typing import LambdaContext

from config import logger
from exceptions import CCInternalException
from handlers import user_client, user_api_schema
from utils import api_handler


@api_handler
def get_me(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Return a user by the sub in their token
    """
    user_id = event['requestContext']['authorizer']['claims']['sub']

    resp = user_client.get_user(user_id=user_id)  # pylint: disable=missing-kwoa
    # This is really unlikely, but will check anyway
    last_key = resp['pagination'].get('lastKey')
    if last_key is not None:
        logger.error('A provider had so many records, they paginated!')
        raise CCInternalException('Unexpected provider data')

    return _merge_user_records(user_id, resp['items'])


@api_handler
def patch_me(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Edit a user's own attributes
    """
    user_id = event['requestContext']['authorizer']['claims']['sub']

    body = json.loads(event['body'])
    user_records = user_client.update_user_attributes(
        user_id=user_id,
        attributes=body['attributes']
    )
    return _merge_user_records(user_id, user_records)

def _merge_user_records(user_id: str, records: list) -> dict:
    users_iter = iter(records)
    merged_user = user_api_schema.load(next(users_iter))
    for record in users_iter:
        compact = record['compact']
        next_user = user_api_schema.load(record)
        if next_user['attributes'] != merged_user['attributes']:
            logger.warning('Inconsistent user attributes', user_id=user_id, compact=compact)
        # Keep the last date of update
        merged_user['dateOfUpdate'] = max(next_user['dateOfUpdate'], merged_user['dateOfUpdate'])
        # Merge compact fields in permissions
        merged_user['permissions'].update(next_user['permissions'])
    return merged_user
