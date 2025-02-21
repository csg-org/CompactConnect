import json

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.exceptions import CCAccessDeniedException, CCNotFoundException
from cc_common.utils import (
    api_handler,
    authorize_compact,
    collect_and_authorize_changes,
    get_allowed_jurisdictions,
    get_event_scopes,
)

from handlers import user_api_schema


@api_handler
@authorize_compact(action='admin')
def get_one_user(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Return a user by userId"""
    compact = event['pathParameters']['compact']
    user_id = event['pathParameters']['userId']
    scopes = get_event_scopes(event)
    allowed_jurisdictions = get_allowed_jurisdictions(compact=compact, scopes=scopes)

    user = config.user_client.get_user_in_compact(compact=compact, user_id=user_id)

    # For jurisdiction-admins, don't return users if they have no permissions in the admin's jurisdiction
    if allowed_jurisdictions is not None:
        allowed_jurisdictions = set(allowed_jurisdictions)
        if not allowed_jurisdictions.intersection(user['permissions']['jurisdictions'].keys()):
            # The user has no permissions in the jurisdictions the admin is allowed to see, so we'll return a 404
            raise CCNotFoundException('User not found')

    # Transform record schema to API schema
    # If the user has permissions that intersect the admin's jurisdiction, we will return the full user's permissions
    # for the requested compact
    return user_api_schema.load(user)


@api_handler
@authorize_compact(action='admin')
def get_users(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Return users"""
    compact = event['pathParameters']['compact']
    # If no query string parameters are provided, APIGW will set the value to None, which we need to handle here
    query_string_params = event.get('queryStringParameters') if event.get('queryStringParameters') is not None else {}
    pagination = {}
    if 'pageSize' in query_string_params.keys():
        pagination['pageSize'] = int(query_string_params['pageSize'])
    if 'lastKey' in query_string_params.keys():
        pagination['lastKey'] = query_string_params['lastKey']

    scopes = get_event_scopes(event)
    allowed_jurisdictions = get_allowed_jurisdictions(compact=compact, scopes=scopes)

    resp = config.user_client.get_users_sorted_by_family_name(
        compact=compact,
        jurisdictions=allowed_jurisdictions,
        pagination=pagination,
    )
    # Convert to API-specific format
    users = resp.pop('items', [])
    resp['users'] = [user_api_schema.load(user) for user in users]
    return resp


@api_handler
@authorize_compact(action='admin')
def patch_user(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    """Admins update a user's data

    Example: This body would be requesting to:
      - add aslp/aslp admin permission
      - add aslp/oh admin permission
      - remove aslp/oh write permission
    ```json
    {
      "permissions": {
        "aslp": {
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
    }
    ```
    """
    compact = event['pathParameters']['compact']
    user_id = event['pathParameters']['userId']
    scopes = get_event_scopes(event)
    path_compact = event['pathParameters']['compact']
    permission_changes = json.loads(event['body']).get('permissions', {}).get(compact, {})
    logger.debug('Requested changes', permission_changes=permission_changes)
    changes = collect_and_authorize_changes(
        path_compact=path_compact,
        scopes=scopes,
        compact_changes=permission_changes,
    )
    user = config.user_client.update_user_permissions(compact=compact, user_id=user_id, **changes)
    return user_api_schema.load(user)


@api_handler
@authorize_compact(action='admin')
def post_user(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    scopes = get_event_scopes(event)
    compact = event['pathParameters']['compact']
    body = json.loads(event['body'])

    # Verify that the client has permission to create a user with the requested permissions
    for compact, compact_permissions in body['permissions'].items():
        # This method will raise an exception if they request an inappropriate permission for the new user
        collect_and_authorize_changes(path_compact=compact, scopes=scopes, compact_changes=compact_permissions)

    # Use the UserClient to create a new user
    user = user_api_schema.dump(body)
    return user_api_schema.load(
        config.user_client.create_user(compact=compact, attributes=user['attributes'], permissions=user['permissions']),
    )


@api_handler
@authorize_compact(action='admin')
def delete_user(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    compact = event['pathParameters']['compact']
    user_id = event['pathParameters']['userId']
    # If the caller is a jurisdiction admin, they can only delete the user if the user only has permissions in the
    # caller's jurisdiction. If the user has permissions in another jurisdiction, an admin in that other jurisdiction
    # must remove those permissions first before this operation will succeed. A compact admin can delete any user in
    # their compact, regardless of where they have permissions.
    allowed_jurisdictions = get_allowed_jurisdictions(compact=compact, scopes=get_event_scopes(event))

    # None means they are a compact admin - no jurisdiction restrictions at all
    if allowed_jurisdictions is not None:
        allowed_jurisdictions = set(allowed_jurisdictions)
        user = config.user_client.get_user_in_compact(compact=compact, user_id=user_id)
        user_jurisdictions = user['permissions']['jurisdictions'].keys()
        disallowed_jurisdictions = user_jurisdictions - allowed_jurisdictions
        common_jurisdictions = allowed_jurisdictions.intersection(user_jurisdictions)

        # We won't show that the user even exists, if they have no common jurisdictions
        if not common_jurisdictions:
            raise CCNotFoundException('User not found')

        # If they have permissions elsewhere, we return an error
        if disallowed_jurisdictions:
            raise CCAccessDeniedException(
                f'User has permissions in other jurisdictions ({", ".join(disallowed_jurisdictions)}). Those must be'
                'removed first or a compact admin must perform this operation.'
            )

    # At this time, 'delete' really means just deleting their compact permission record but doing nothing to the actual
    # Cognito user.
    config.user_client.delete_user(compact=compact, user_id=user_id)
    return {'message': 'User deleted'}


@api_handler
@authorize_compact(action='admin')
def reinvite_user(event: dict, context: LambdaContext):  # noqa: ARG001 unused-argument
    compact = event['pathParameters']['compact']
    user_id = event['pathParameters']['userId']

    allowed_jurisdictions = get_allowed_jurisdictions(compact=compact, scopes=get_event_scopes(event))

    # None means they are a compact admin - no jurisdiction restrictions at all
    user = config.user_client.get_user_in_compact(compact=compact, user_id=user_id)
    if allowed_jurisdictions is not None:
        allowed_jurisdictions = set(allowed_jurisdictions)
        user = config.user_client.get_user_in_compact(compact=compact, user_id=user_id)
        user_jurisdictions = user['permissions']['jurisdictions'].keys()
        common_jurisdictions = allowed_jurisdictions.intersection(user_jurisdictions)

        # We won't show that the user even exists, if they have no common jurisdictions
        if not common_jurisdictions:
            raise CCNotFoundException('User not found')

    config.user_client.reinvite_user(email=user['attributes']['email'])
    return {'message': 'User reinvited'}
