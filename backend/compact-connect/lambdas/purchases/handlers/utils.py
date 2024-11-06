import json
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from functools import wraps
from json import JSONEncoder
from uuid import UUID

from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from cc_common.config import logger
from cc_common.exceptions import CCAccessDeniedException, CCInvalidRequestException, CCNotFoundException, CCUnauthorizedException


class ResponseEncoder(JSONEncoder):
    """JSON Encoder to handle data types that come out of our schema"""

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
    """Decorator to wrap an api gateway event handler in standard logging, HTTPError handling.

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
            context=context,
        )

        try:
            return {
                'headers': {'Access-Control-Allow-Origin': '*'},
                'statusCode': 200,
                'body': json.dumps(fn(event, context), cls=ResponseEncoder),
            }
        except CCUnauthorizedException as e:
            logger.info('Unauthorized request', exc_info=e)
            return {
                'headers': {'Access-Control-Allow-Origin': '*'},
                'statusCode': 401,
                'body': json.dumps({'message': 'Unauthorized'}),
            }
        except CCAccessDeniedException as e:
            logger.info('Forbidden request', exc_info=e)
            return {
                'headers': {'Access-Control-Allow-Origin': '*'},
                'statusCode': 403,
                'body': json.dumps({'message': 'Access denied'}),
            }
        except CCNotFoundException as e:
            logger.info('Resource not found', exc_info=e)
            return {
                'headers': {'Access-Control-Allow-Origin': '*'},
                'statusCode': 404,
                'body': json.dumps({'message': f'{e.message}'}),
            }
        except CCInvalidRequestException as e:
            logger.info('Invalid request', exc_info=e)
            return {
                'headers': {'Access-Control-Allow-Origin': '*'},
                'statusCode': 400,
                'body': json.dumps({'message': e.message}),
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
                exc_info=e,
            )
            raise

    return caught_handler

def _authorize_compact_with_scope(event: dict, resource_parameter: str, scope_parameter: str, action: str) -> None:
    """
    Check the authorization of the user attempting to access the endpoint.

    There are three types of action level permissions which can be granted to a user:

    1. read: Allows the user to read data from the compact.
    2. write: Allows the user to write data to the compact.
    3. admin: Allows the user to perform administrative actions on the compact.

    For each of these actions, specific rules apply to the scope required to perform the action, which are
    as follows:

    Read - granted at compact level, allows read access to all jurisdictions within the compact.
    i.e. aslp/read would allow read access to all jurisdictions within the aslp compact.

    Write - granted at jurisdiction level, allows write access to a specific jurisdiction within the compact.
    i.e. aslp/oh.write would allow write access to the ohio jurisdiction within the aslp compact.

    Admin - granted at compact level and jurisdiction level, allows administrative access to either a specific
    compact or a specific jurisdiction within the compact.
    i.e. 'aslp/aslp.admin' would allow administrative access to the aslp compact. 'aslp/oh.admin' would allow
    administrative access to the ohio jurisdiction within the aslp compact.

    :param dict event: The event object passed to the lambda function.
    :param str resource_parameter: The value of the resource parameter in the path.
    :param str scope_parameter: The value of the scope parameter in the path.
    :param str action: The action we want to ensure the user has permissions for.
    :raises CCUnauthorizedException: If the user is missing scope claims.
    :raises CCAccessDeniedException: If the user does not have the necessary access.
    """
    try:
        resource_value = event['pathParameters'][resource_parameter]
        if scope_parameter != resource_parameter:
            scope_value = event['pathParameters'][scope_parameter]
        else:
            # if the scope parameter is the same as the resource parameter,
            # we use the resource value as the scope value
            scope_value = resource_value
    except KeyError as e:
        logger.error('Access attempt with missing path parameters!')
        raise CCInvalidRequestException('Missing path parameter!') from e

    try:
        scopes = event['requestContext']['authorizer']['claims']['scope'].split(' ')
    except KeyError as e:
        logger.error('Unauthorized access attempt!', exc_info=e)
        raise CCUnauthorizedException('Unauthorized access attempt!') from e

    required_scope = f'{resource_value}/{scope_value}.{action}'
    if required_scope not in scopes:
        logger.warning('Forbidden access attempt!')
        raise CCAccessDeniedException('Forbidden access attempt!')


class authorize_compact_jurisdiction:  # noqa: N801 invalid-name
    """
    Authorize endpoint by matching path parameters compact and jurisdiction to the expected scope.
    (i.e. aslp/oh.write)
    """

    def __init__(self, action: str):
        super().__init__()
        self.resource_parameter = 'compact'
        self.scope_parameter = 'jurisdiction'
        self.action = action

    def __call__(self, fn: Callable):
        @wraps(fn)
        @logger.inject_lambda_context
        def authorized(event: dict, context: LambdaContext):
            _authorize_compact_with_scope(event, self.resource_parameter, self.scope_parameter, self.action)
            return fn(event, context)

        return authorized


class authorize_compact_scoped_action:  # noqa: N801 invalid-name
    """
    Authorize endpoint by matching compact path parameter to the expected scope.
    (i.e. aslp/aslp.admin)
    """

    def __init__(self, action: str):
        super().__init__()
        self.resource_parameter = 'compact'
        self.scope_parameter = 'compact'
        self.action = action

    def __call__(self, fn: Callable):
        @wraps(fn)
        @logger.inject_lambda_context
        def authorized(event: dict, context: LambdaContext):
            _authorize_compact_with_scope(event, self.resource_parameter, self.scope_parameter, self.action)
            return fn(event, context)

        return authorized
