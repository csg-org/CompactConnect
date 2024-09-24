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


class authorize_compact_jurisdiction:  # pylint: disable=invalid-name
    """
    Authorize endpoint by matching path parameters compact and jurisdiction to the expected scope. (i.e. aslp/oh.write)
    """
    def __init__(self, action: str):
        """
        Decorator to wrap scope-based authorization, for a scope like '{resource_server}/{scope}.{action}'.

        For a URL path like:
        ```
        /foo/{resource_parameter}/bar/{scope_parameter}
        ```

        decorating an api handler with `@scope_by_path('resource_parameter', 'scope_parameter', 'write')` will create
        an authorization that expects a request like `/foo/zig/bar/zag` to have a scope called `zig/zag.write`.

        :param str resource_parameter: The path parameter to use for the resource server portion of a resource/scope
        requirement.
        :param str scope_parameter: The path parameter to use for the scope portion of a resource/scope requirement
        :param str action: The additional 'action' portion of the resource/scope requirement.
        """
        super().__init__()
        self.resource_parameter = 'compact'
        self.scope_parameter = 'jurisdiction'
        self.action = action

    def __call__(self, fn: Callable):
        @wraps(fn)
        @logger.inject_lambda_context
        def authorized(event: dict, context: LambdaContext):
            try:
                scope_value = event['pathParameters'][self.scope_parameter]
                resource_value = event['pathParameters'][self.resource_parameter]
            except KeyError as e:
                logger.error('Access attempt with missing path parameters!')
                raise CCInvalidRequestException('Missing path parameter!') from e

            logger.debug(
                'Checking authorizer context',
                request_context=event['requestContext']
            )
            try:
                scopes = event['requestContext']['authorizer']['claims']['scope'].split(' ')
            except KeyError as e:
                logger.error('Unauthorized access attempt!', exc_info=e)
                raise CCUnauthorizedException('Unauthorized access attempt!') from e

            required_scope = f'{resource_value}/{scope_value}.{self.action}'
            if required_scope not in scopes:
                logger.warning('Forbidden access attempt!')
                raise CCAccessDeniedException('Forbidden access attempt!')
            return fn(event, context)
        return authorized


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


def sqs_handler(fn: Callable):
    """
    Process messages from the ingest queue.

    This handler uses batch item failure reporting:
    https://docs.aws.amazon.com/lambda/latest/dg/example_serverless_SQS_Lambda_batch_item_failures_section.html
    This allows the queue to continue to scale under load, even if a number of the messages are failing. It
    also improves efficiency, as we don't have to throw away the entire batch for a single failure.
    """
    @wraps(fn)
    @logger.inject_lambda_context
    def process_messages(event, context: LambdaContext):  # pylint: disable=unused-argument
        records = event['Records']
        logger.info('Starting batch', batch_count=len(records))
        batch_failures = []
        for record in records:
            try:
                message = json.loads(record['body'])
                logger.info(
                    'Processing message',
                    message_id=record['messageId'],
                    message_attributes=record.get('messageAttributes')
                )
                # No exception here means success
                fn(message)
            # When we receive a batch of messages from SQS, letting an exception escape all the way back to AWS is
            # really undesirable. Instead, we're going to catch _almost_ any exception raised, note what message we
            # were processing, and report those item failures back to AWS.
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error('Failed to process message', exc_info=e)
                batch_failures.append({'itemIdentifier': record['messageId']})
        logger.info('Completed batch', batch_failures=len(batch_failures))
        return {
            'batchItemFailures': batch_failures
        }

    return process_messages
