from datetime import datetime, timedelta

from aws_lambda_powertools.utilities.typing import LambdaContext

from cc_common.config import config
from cc_common.exceptions import TransactionBatchSettlementFailureException
from purchase_client import PurchaseClient


def process_settled_transactions(event: dict, context: LambdaContext) -> dict:  # noqa: ARG001 unused-argument
    """
    Process settled transactions from the payment processor.

    :param event: Lambda event containing:
        - compact: The compact name
        - lastProcessedTransactionId: Optional last processed transaction ID
        - currentBatchId: Optional current batch ID being processed
        - processedBatchIds: Optional list of batch IDs that have been processed
    :param context: Lambda context
    :return: Dictionary indicating processing status and optional pagination info
    """
    compact = event['compact']
    last_processed_transaction_id = event.get('lastProcessedTransactionId')
    current_batch_id = event.get('currentBatchId')
    processed_batch_ids = event.get('processedBatchIds', [])

    # Calculate time range for the last 24 hours
    end_time = config.current_standard_datetime
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
            transaction_limit=500,
            last_processed_transaction_id=last_processed_transaction_id,
            current_batch_id=current_batch_id,
            processed_batch_ids=processed_batch_ids,
        )

        # Store transactions in DynamoDB
        if transaction_response['transactions']:
            config.transaction_client.store_transactions(compact, transaction_response['transactions'])

        # Return appropriate response based on whether there are more transactions to process
        response = {
            'compact': compact,  # Always include the compact name
            'status': 'IN_PROGRESS' if 'lastProcessedTransactionId' in transaction_response else 'COMPLETE',
            'processedBatchIds': transaction_response['processedBatchIds']
        }

        # Only include pagination values if we're not done processing
        if 'lastProcessedTransactionId' in transaction_response:
            response.update({
                'lastProcessedTransactionId': transaction_response['lastProcessedTransactionId'],
                'currentBatchId': transaction_response['currentBatchId']
            })

        return response

    except TransactionBatchSettlementFailureException as e:
        return {
            'compact': compact,
            'status': 'BATCH_FAILURE',
            'batchFailureErrorMessage': str(e)
        }
