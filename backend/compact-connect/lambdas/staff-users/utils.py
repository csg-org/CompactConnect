import json
from decimal import Decimal
from functools import wraps
from json import JSONEncoder
from re import match
from typing import Callable, List, Set
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
            logger.info('Unauthorized request', exc_msg=str(e), exc_info=e)
            return {
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'statusCode': 401,
                'body': json.dumps({'message': 'Unauthorized'})
            }
        except CCAccessDeniedException as e:
            logger.info('Forbidden request', exc_msg=str(e), exc_info=e)
            return {
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'statusCode': 403,
                'body': json.dumps({'message': 'Access denied'})
            }
        except CCNotFoundException as e:
            logger.info('Resource not found', exc_msg=str(e), exc_info=e)
            return {
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'statusCode': 404,
                'body': json.dumps({'message': e.message})
            }
        except CCConflictException as e:
            logger.info('Resource not found', exc_msg=str(e), exc_info=e)
            return {
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'statusCode': 404,
                'body': json.dumps({'message': e.message})
            }
        except CCInvalidRequestException as e:
            logger.info('Invalid request', exc_msg=str(e), exc_info=e)
            return {
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                },
                'statusCode': 400,
                'body': json.dumps({'message': e.message})
            }
        except ClientError as e:
            # Any boto3 ClientErrors we haven't already caught and transformed are probably on us
            logger.error('boto3 ClientError', response=e.response, exc_msg=str(e), exc_info=e)
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


def get_allowed_jurisdictions(*, compact: str, scopes: Set[str]) -> List[str] | None:
    """
    Return a list of jurisdictions the user is allowed to access based on their scopes. If the scopes indicate
    the user is a compact admin, the function will return None, as they will do no jurisdiction-based filtering.
    :param str compact: The compact the user is trying to access.
    :param set scopes: The user's scopes from the request.
    :return: A list of jurisdictions the user is allowed to access, or None, if no filtering is needed.
    :rtype: list
    """
    if f'{compact}/{compact}.admin' in scopes:
        # The user has compact-level admin, so no jurisdiction filtering
        return None

    compact_jurisdictions = []
    scope_pattern = f'{compact}/(.*).admin'
    for scope in scopes:
        if match_obj := match(scope_pattern, scope):
            compact_jurisdictions.append(match_obj.group(1))
    return compact_jurisdictions


def get_event_scopes(event: dict):
    return set(event['requestContext']['authorizer']['claims']['scope'].split(' '))

def collect_changes(*, path_compact: str, scopes: set, compact_changes: dict) -> dict:
    """
    Transform PATCH user API changes to permissions into db operation changes. Operation changes are checked
    against the provided scopes to ensure the user is allowed to make the requested changes.
    :param str path_compact: The compact declared in the url path
    :param set scopes: The scopes associated with the user making the request
    :param dict compact_changes: Permissions changes in the request body
    Example:
    {
        'actions': {
            'admin': True,
            'read': False
        },
        'jurisdictions': {
            'oh': {
                'actions': {
                    'admin': True,
                    'write': False
                }
            }
        }
    }
    :return: Changes to the User's underlying record
    :rtype: dict
    """
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
    for jurisdiction, jurisdiction_changes in compact_changes.get('jurisdictions', {}).items():
        if not {f'{path_compact}/{path_compact}.admin', f'{path_compact}/{jurisdiction}.admin'}.intersection(scopes):
            raise CCAccessDeniedException(
                f'Only {path_compact} or {path_compact}/{jurisdiction} admins can affect {path_compact}/{jurisdiction} '
                'permissions'
            )

        for action, value in jurisdiction_changes.get('actions', {}).items():
            if value:
                jurisdiction_action_additions.setdefault(jurisdiction, set()).add(action)
            else:
                jurisdiction_action_removals.setdefault(jurisdiction, set()).add(action)

    return {
        'compact_action_additions': compact_action_additions,
        'compact_action_removals': compact_action_removals,
        'jurisdiction_action_additions': jurisdiction_action_additions,
        'jurisdiction_action_removals': jurisdiction_action_removals
    }

def get_sub_from_user_attributes(attributes: list):
    for attribute in attributes:
        if attribute['Name'] == 'sub':
            return attribute['Value']
    raise ValueError('Failed to find user sub!')
