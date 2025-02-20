import json
from datetime import timedelta

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from purchase_client import PurchaseClient


def _all_transactions_processed(transaction_response: dict) -> bool:
    return 'lastProcessedTransactionId' not in transaction_response


def process_settled_transactions(event: dict, context: LambdaContext) -> dict:  # noqa: ARG001 unused-argument
    """
    Process settled transactions from the payment processor.

    This lambda is invoked as part of the transaction history processing workflow. It retrieves settled transactions
    from the payment processor and stores them in DynamoDB. It is designed to be invoked multiple times until all
    transactions have been processed. The lambda will return a status of 'IN_PROGRESS' until all transactions have been
    processed, at which point it will return a status of 'COMPLETE'.

    If any transactions in a batch have a settlement error, the lambda will store all transactions from the batch
    but will return a status of 'BATCH_FAILURE', which will cause the workflow to send an alert to the compact
    operations team.

    :param event: Lambda event containing:
        - compact: The compact name
        - lastProcessedTransactionId: Optional last processed transaction ID
        - currentBatchId: Optional current batch ID being processed
        - processedBatchIds: Optional list of batch IDs that have been processed, this ensures we don't process the same
            batch multiple times.
    :param context: Lambda context
    :return: Dictionary indicating processing status and optional pagination info
    """
    compact = event['compact']
    last_processed_transaction_id = event.get('lastProcessedTransactionId')
    current_batch_id = event.get('currentBatchId')
    processed_batch_ids = event.get('processedBatchIds', [])

    # By default, the authorize.net accounts batch settlements at 4:00pm Pacific Time.
    # This daily collector runs an hour later (5pm PST, which is 1am UTC) to collect
    # all settled transaction for the last 24 hours.
    end_time = config.current_standard_datetime.replace(hour=1, minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=1)

    # Format timestamps for API call
    start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    logger.info(
        'Collecting settled transaction for time period',
        compact=compact,
        start_time=start_time_str,
        end_time=end_time_str,
    )

    # Get transactions from payment processor
    purchase_client = PurchaseClient()
    transaction_response = purchase_client.get_settled_transactions(
        compact=compact,
        start_time=start_time_str,
        end_time=end_time_str,
        # we set the transaction limit to 500 to avoid hitting the 15-minute timeout for lambda
        transaction_limit=500,
        last_processed_transaction_id=last_processed_transaction_id,
        current_batch_id=current_batch_id,
        processed_batch_ids=processed_batch_ids,
    )

    # Store transactions in DynamoDB
    if transaction_response['transactions']:
        logger.info('Fetching privilege ids for transactions', compact=compact)
        # first we must add the associated privilege ids to each transaction so we can show the association in our
        # reports
        transactions_with_privilege_ids = config.transaction_client.add_privilege_ids_to_transactions(
            compact=compact, transactions=transaction_response['transactions']
        )
        logger.info('Storing transactions in DynamoDB', compact=compact)
        config.transaction_client.store_transactions(transactions=transactions_with_privilege_ids)

    # Return appropriate response based on whether there are more transactions to process
    response = {
        'compact': compact,  # Always include the compact name
        'status': 'IN_PROGRESS' if not _all_transactions_processed(transaction_response) else 'COMPLETE',
        'processedBatchIds': transaction_response['processedBatchIds'],
    }

    # Only include pagination values if we're not done processing
    if not _all_transactions_processed(transaction_response):
        logger.info('Not all transactions processed, updating response with pagination values')
        response.update(
            {
                'lastProcessedTransactionId': transaction_response['lastProcessedTransactionId'],
                'currentBatchId': transaction_response['currentBatchId'],
            }
        )

    # here we check if there were any settlement errors in the batch or if there was a settlement failure
    # in a previous iteration, and we need to send an alert to the compact operations team
    failed_transactions_ids = transaction_response.get('settlementErrorTransactionIds')
    if failed_transactions_ids or event.get('batchFailureErrorMessage'):
        # error message should be a json object we can load
        if event.get('batchFailureErrorMessage'):
            batch_failure_error_message = json.loads(event.get('batchFailureErrorMessage'))
            batch_failure_error_message['failedTransactionIds'].extend(failed_transactions_ids)
            response['batchFailureErrorMessage'] = json.dumps(batch_failure_error_message)
        else:
            # if there was no previous error message, we'll create a new one
            response['batchFailureErrorMessage'] = json.dumps(
                {
                    'message': 'Settlement errors detected in one or more transactions.',
                    'failedTransactionIds': failed_transactions_ids,
                }
            )

        if _all_transactions_processed(transaction_response):
            # we've finished storing all transactions for this period,
            # and we need to send an alert to the compact operations team
            logger.warning(
                'Batch settlement error detected', batchFailureErrorMessage=response['batchFailureErrorMessage']
            )
            response['status'] = 'BATCH_FAILURE'

    return response
