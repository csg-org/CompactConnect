import json
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from functools import wraps
from json import JSONEncoder
from uuid import UUID

from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from config import logger
from exceptions import CCAccessDeniedException, CCInvalidRequestException, CCNotFoundException, CCUnauthorizedException


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

class authorize_compact:  # noqa: N801 invalid-name
    """Authorize endpoint by matching path parameter compact to the expected scope, (i.e. aslp/read)"""

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

            logger.debug('Checking authorizer context', request_context=event['requestContext'])
            try:
                scopes = event['requestContext']['authorizer']['claims']['scope'].split(' ')
            except KeyError as e:
                logger.error('Unauthorized access attempt!', exc_info=e)
                raise CCUnauthorizedException('Unauthorized access attempt!') from e

            required_scope = f'{resource_value}/{self.action}'
            if required_scope not in scopes:
                logger.warning('Forbidden access attempt!')
                raise CCAccessDeniedException('Forbidden access attempt!')
            return fn(event, context)

        return authorized
