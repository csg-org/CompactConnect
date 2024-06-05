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
        event['headers'].pop('Authorization', None)
        event['multiValueHeaders'].pop('Authorization', None)

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
