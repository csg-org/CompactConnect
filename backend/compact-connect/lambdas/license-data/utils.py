import json
from functools import wraps
from typing import Callable

from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from config import logger


def api_handler(fn: Callable):
    """
    Decorator to wrap an api gateway event handler in standard logging, HTTPError handling
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
                'body': json.dumps(fn(event, context))
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


class scope_by_path:  # pylint: disable=invalid-name
    """
    Decorator to wrap scope-based authorization
    """
    def __init__(self, *, scope_parameter: str, resource_parameter: str):
        self.scope_parameter = scope_parameter
        self.resource_parameter = resource_parameter

    def __call__(self, fn: Callable):
        @wraps(fn)
        @logger.inject_lambda_context
        def authorized(event: dict, context: LambdaContext):
            try:
                path_value = event['pathParameters'][self.scope_parameter]
                resource_value = event['pathParameters'][self.resource_parameter]
            except KeyError:
                # If we raise this exact exception, API Gateway returns a 401 instead of 403 for a DENY statement
                # Any other exception/message will result in a 500
                logger.error('Access attempt with missing path parameters!')
                return {'statusCode': 401}

            logger.debug(
                'Checking authorizer context',
                request_context=event['requestContext']
            )
            try:
                scopes = event['requestContext']['authorizer']['claims']['scope'].split(' ')
            except KeyError:
                logger.error('Unauthorized access attempt!')
                return {'statusCode': 401}

            required_scope = f'{resource_value}/{path_value}'
            if required_scope not in scopes:
                logger.warning('Forbidden access attempt!')
                return {'statusCode': 403}
            return fn(event, context)
        return authorized
