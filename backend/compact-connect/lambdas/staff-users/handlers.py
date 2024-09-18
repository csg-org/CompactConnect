import json

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from config import config
from data_model.client import UserClient
from utils import api_handler, authorize_compact, get_event_scopes, transform_user_permissions, collect_changes

logger = Logger()
user_client = UserClient(config=config)


@api_handler
@authorize_compact(action='admin')
def get_one_user(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Return a user by userId
    """
    user_id = event['pathParameters']['userId']
    user = user_client.get_user(compact='aslp', user_id=user_id)
    # Transform record schema to API schema
    return {
        'type': user['type'],
        'dateOfUpdate': user['dateOfUpdate'],
        'userId': user['userId'],
        'attributes': user['attributes'],
        'permissions': transform_user_permissions(compact='aslp', compact_permissions=user['permissions'])
    }


@api_handler
@authorize_compact(action='admin')
def get_users(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Return users
    """
    # If no query string parameters are provided, APIGW will set the value to None, which we need to handle here
    query_string_params = event.get('queryStringParameters') if event.get('queryStringParameters') is not None else {}
    pagination = {
        'lastKey': query_string_params.get('lastKey'),
        'pageSize': query_string_params.get('pageSize')
    }
    resp = user_client.get_users(pagination=pagination)
    # Convert to API-specific field
    resp['users'] = resp.pop('users')
    return resp


@api_handler
@authorize_compact(action='admin')
def patch_user(event: dict, context: LambdaContext):  # pylint: disable=unused-argument
    """
    Admins update a user's data

    Example: This body would be requesting to:
      - add aslp/aslp admin permission
      - add aslp/oh admin permission
      - remove aslp/oh write permission
    ```json
    {
      "permissions": {
        "actions": {
          "admin": true
        }
        "jurisdictions": {
          "oh": {
            "actions": {
              "admin": true,
              "write": false
          }
        }
      }
    }
    ```
    """
    compact = event['pathParameters']['compact']
    user_id = event['pathParameters']['userId']
    scopes = get_event_scopes(event)
    path_compact = event['pathParameters']['compact']
    permission_changes = json.loads(event['body']).get('permissions', {})
    changes = collect_changes(path_compact=path_compact, scopes=scopes, permission_changes=permission_changes)
    user_client.update_user_permissions(
        compact=compact,
        user_id=user_id,
        **changes
    )
