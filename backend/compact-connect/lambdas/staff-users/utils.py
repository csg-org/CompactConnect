import json
from decimal import Decimal
from functools import wraps
from json import JSONEncoder
from typing import Callable
from datetime import date
from uuid import UUID

from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from config import logger
from exceptions import CCInvalidRequestException, CCUnauthorizedException, CCAccessDeniedException, \
    CCNotFoundException, CCConflictException


class ResponseEncoder(JSONEncoder):
    """
    JSON Encoder to handle data types that come out of our schema
    """
    def default(self, o):
        if isinstance(o, Decimal):
            ratio = o.as_integer_ratio()
            if ratio[1] == 1:
                return ratio[0]
            return float(o)

        if isinstance(o, UUID):
            return str(o)

        if isinstance(o, date):
            return o.isoformat()

        if isinstance(o, set):
            return list(o)

        # This is just a catch-all that shouldn't realistically ever be reached.
        return super().default(o)


def api_handler(fn: Callable):
    """
    Decorator to wrap an api gateway event handler in standard logging, HTTPError handling.

    - Logs each access
    - JSON-encodes returned responses
    - Translates CCBaseException subclasses to their respective HTTP response codes
    """

    @wraps(fn)
    @logger.inject_lambda_context
    def caught_handler(event, context: LambdaContext):
        # We have to jump through extra hoops to handle the case where APIGW sets headers to null
        (event.get('headers') or {}).pop('Authorization', None)
        (event.get('multiValueHeaders') or {}).pop('Authorization', None)

        logger.info(
            'Incoming request',
            method=event['httpMethod'],
            path=event['requestContext']['resourcePath'],
            query_params=event['queryStringParameters'],
            username=event['requestContext'].get('authorizer', {}).get('claims', {}).get('cognito:username'),
            context=context
        )

        try:
            return {
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'statusCode': 200,
                'body': json.dumps(fn(event, context), cls=ResponseEncoder)
            }
        except CCUnauthorizedException as e:
            logger.info('Unauthorized request', exc_info=e)
            return {
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'statusCode': 401,
                'body': json.dumps({'message': 'Unauthorized'})
            }
        except CCAccessDeniedException as e:
            logger.info('Forbidden request', exc_info=e)
            return {
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'statusCode': 403,
                'body': json.dumps({'message': 'Access denied'})
            }
        except CCNotFoundException as e:
            logger.info('Resource not found', exc_info=e)
            return {
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'statusCode': 404,
                'body': json.dumps({'message': e.message})
            }
        except CCConflictException as e:
            logger.info('Resource not found', exc_info=e)
            return {
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'statusCode': 404,
                'body': json.dumps({'message': e.message})
            }
        except CCInvalidRequestException as e:
            logger.info('Invalid request', exc_info=e)
            return {
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'statusCode': 400,
                'body': json.dumps({'message': e.message})
            }
        except ClientError as e:
            # Any boto3 ClientErrors we haven't already caught and transformed are probably on us
            logger.error('boto3 ClientError', response=e.response, exc_info=e)
            raise
        except Exception as e:
            logger.warning(
                'Error processing request',
                method=event['httpMethod'],
                path=event['requestContext']['resourcePath'],
                query_params=event['queryStringParameters'],
                context=context,
                exc_info=e
            )
            raise

    return caught_handler


class authorize_compact:  # pylint: disable=invalid-name
    """
    Authorize endpoint by matching path parameter compact to the expected scope, (i.e. aslp/read)
    """
    def __init__(self, action: str):
        super().__init__()
        self.action = action

    def __call__(self, fn: Callable):
        @wraps(fn)
        @logger.inject_lambda_context
        def authorized(event: dict, context: LambdaContext):
            try:
                resource_value = event['pathParameters']['compact']
            except KeyError as e:
                logger.error('Access attempt with missing path parameter!')
                raise CCInvalidRequestException('Missing path parameter!') from e

            logger.debug(
                'Checking authorizer context',
                request_context=event['requestContext']
            )
            try:
                scopes = get_event_scopes(event)
            except KeyError as e:
                logger.error('Unauthorized access attempt!', exc_info=e)
                raise CCUnauthorizedException('Unauthorized access attempt!') from e

            required_scope = f'{resource_value}/{self.action}'
            if required_scope not in scopes:
                logger.warning('Forbidden access attempt!')
                raise CCAccessDeniedException('Forbidden access attempt!')
            return fn(event, context)
        return authorized


def get_event_scopes(event: dict):
    return set(event['requestContext']['authorizer']['claims']['scope'].split(' '))


def transform_user_permissions(*, compact: str, compact_permissions: dict) -> dict:
    """
    Transform compact permissions from database format into API format
    :param dict compact_permissions: User compact permissions from the database
    :return: Permissions formatted for returning via the API
    :rtype: dict
    """
    user_permissions = {compact: {}}

    compact_actions = compact_permissions.get('actions')
    if compact_actions is not None:
        # Set to dict of '{action}: True' items
        user_permissions[compact]['actions'] = {
            action: True
            for action in compact_permissions['actions']
        }
    jurisdictions = compact_permissions['jurisdictions']
    if jurisdictions is not None:
        # Transform jurisdiction permissions
        user_permissions[compact]['jurisdictions'] = {}
        for jurisdiction, jurisdiction_permissions in jurisdictions.items():
            # Set to dict of '{action}: True' items
            user_permissions[compact]['jurisdictions'][jurisdiction] = {
                'actions': {
                    action: True
                    for action in jurisdiction_permissions
                }
            }
    return user_permissions


def collect_changes(*, path_compact: str, scopes: set, permission_changes: dict) -> dict:
    """
    Transform PATCH user API changes to permissions into db operation changes.
    :param dict permission_changes: Permissions changes in the request body
    :return: Changes to the User's underlying record
    :rtype: dict
    """
    # The admin can only touch permissions related to the compact they are currently representing
    # (as declared by the url path). We've already verified their permission to affect the compact
    # in the url path by virtue of the `authorize_compact` decorator, so no need to do that here.
    body_compacts = permission_changes.keys()
    disallowed_compacts = set(path_compact) - body_compacts
    if disallowed_compacts:
        # There are compacts in the body besides the one declared in the url path
        raise CCAccessDeniedException(f'Forbidden compact changes: {disallowed_compacts}')

    # At this point, we've effectively limited permission_changes to including zero or one compacts
    compact_changes = permission_changes.get(path_compact, {})
    compact_action_additions = set()
    compact_action_removals = set()
    jurisdiction_action_additions = {}
    jurisdiction_action_removals = {}

    # Collect compact-wide permission changes
    for action, value in compact_changes.get('actions', {}).items():
        if action == 'admin' and f'{path_compact}/{path_compact}.admin' not in scopes:
            raise CCAccessDeniedException('Only compact admins can affect compact-level admin permissions')
        # Any admin in the compact can affect read permissions, so no read-specific check is necessary here
        if value:
            compact_action_additions.add(action)
        else:
            compact_action_removals.add(action)

    # Collect jurisdiction-specific changes
    for jurisdiction, jurisdiction_changes in compact_changes.get('jurisdictions', {}):
        if not {f'{path_compact}/{path_compact}.admin', f'{path_compact}/{jurisdiction}.admin'}.intersection(scopes):
            raise CCAccessDeniedException(
                f'Only {path_compact} or {path_compact}/{jurisdiction} admins can affect {path_compact}/{jurisdiction} '
                'permissions'
            )

        jurisdiction_action_additions[jurisdiction] = {
            action
            for action, value in jurisdiction_changes.get('actions', {}).items()
            if value
        }
        jurisdiction_action_removals[jurisdiction] = {
            action
            for action, value in jurisdiction_changes.get('actions', {}).items()
            if not value
        }
    return {
        'compact_action_additions': compact_action_additions,
        'compact_action_removals': compact_action_removals,
        'jurisdiction_action_additions': jurisdiction_action_additions,
        'jurisdiction_action_removals': jurisdiction_action_removals
    }

def filter_for_jurisdiction(*, jurisdiction: str) -> Callable[[dict], bool]:
    """
    Create a Callable client filter that returns True if the provided user has permissions in the provided compact and
    jurisdiction
    """
    def client_filter(user: dict) -> bool:
        return jurisdiction in user['permissions'].get('jurisdictions', {})

    return client_filter


def get_sub_from_user_attributes(attributes: list):
    for attribute in attributes:
        if attribute['Name'] == 'sub':
            return attribute['Value']
    raise ValueError('Failed to find user sub!')
