import json
from collections.abc import Callable
from functools import wraps

from aws_lambda_powertools.utilities.typing import LambdaContext
from config import logger


def sqs_handler(fn: Callable) -> Callable:
    """Process messages from the ingest queue.

    This handler uses batch item failure reporting:
    https://docs.aws.amazon.com/lambda/latest/dg/example_serverless_SQS_Lambda_batch_item_failures_section.html
    This allows the queue to continue to scale under load, even if a number of the messages are failing. It
    also improves efficiency, as we don't have to throw away the entire batch for a single failure.
    """

    @wraps(fn)
    @logger.inject_lambda_context
    def process_messages(event, context: LambdaContext):  # noqa: ARG001 unused-argument
        records = event['Records']
        logger.info('Starting batch', batch_count=len(records))
        batch_failures = []
        for record in records:
            try:
                message = json.loads(record['body'])
                logger.info(
                    'Processing message',
                    message_id=record['messageId'],
                    message_attributes=record.get('messageAttributes'),
                )
                # No exception here means success
                fn(message)
            # When we receive a batch of messages from SQS, letting an exception escape all the way back to AWS is
            # really undesirable. Instead, we're going to catch _almost_ any exception raised, note what message we
            # were processing, and report those item failures back to AWS.
            except Exception as e:  # noqa: BLE001 broad-exception-caught
                logger.error('Failed to process message', exc_info=e)
                batch_failures.append({'itemIdentifier': record['messageId']})
        logger.info('Completed batch', batch_failures=len(batch_failures))
        return {'batchItemFailures': batch_failures}

    return process_messages
