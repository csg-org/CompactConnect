from datetime import timedelta

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config
from cc_common.exceptions import TransactionBatchSettlementFailureException
from purchase_client import PurchaseClient


def process_settled_transactions(event: dict, context: LambdaContext) -> dict:  # noqa: ARG001 unused-argument
    """
    Process settled transactions from the payment processor.

    This lambda is invoked as part of the transaction history processing workflow. It retrieves settled transactions
    from the payment processor and stores them in DynamoDB. It is designed to be invoked multiple times until all
    transactions have been processed. The lambda will return a status of 'IN_PROGRESS' until all transactions have been
    processed, at which point it will return a status of 'COMPLETE'.

    If the payment processor reports that there was a settlement failure, the lambda will return a status of
    'BATCH_FAILURE', which will cause the workflow to send an alert to the compact operations team.

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

    # This lambda is triggered at noon UTC-4, so we calculate the time range for the last 24 hours
    end_time = config.current_standard_datetime.replace(hour=16, minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=1)

    # Format timestamps for API call
    start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time_str = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    try:
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
            # first we must add the associated privilege ids to each transaction so we can show the association in our
            # reports
            transactions_with_privilege_ids = config.transaction_client.add_privilege_ids_to_transactions(
                compact=compact, transactions=transaction_response['transactions']
            )
            config.transaction_client.store_transactions(transactions=transactions_with_privilege_ids)

        # Return appropriate response based on whether there are more transactions to process
        response = {
            'compact': compact,  # Always include the compact name
            'status': 'IN_PROGRESS' if 'lastProcessedTransactionId' in transaction_response else 'COMPLETE',
            'processedBatchIds': transaction_response['processedBatchIds'],
        }

        # Only include pagination values if we're not done processing
        if 'lastProcessedTransactionId' in transaction_response:
            response.update(
                {
                    'lastProcessedTransactionId': transaction_response['lastProcessedTransactionId'],
                    'currentBatchId': transaction_response['currentBatchId'],
                }
            )

        return response

    except TransactionBatchSettlementFailureException as e:
        return {'compact': compact, 'status': 'BATCH_FAILURE', 'batchFailureErrorMessage': str(e)}
