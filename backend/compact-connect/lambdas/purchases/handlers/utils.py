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
    CCNotFoundException

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
                'body': json.dumps({'message': 'Resource not found'})
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
