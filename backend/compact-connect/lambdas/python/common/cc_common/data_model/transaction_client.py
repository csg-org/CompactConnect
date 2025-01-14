from datetime import datetime

from cc_common.config import _Config

AUTHORIZE_DOT_NET_CLIENT_TYPE = 'authorize.net'


class TransactionClient:
    """Client interface for transaction history data dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config

    def store_transactions(self, compact: str, transactions: list[dict]) -> None:
        """
        Store transaction records in DynamoDB.

        :param compact: The compact name
        :param transactions: List of transaction records to store
        """
        with self.config.transaction_history_table.batch_writer() as batch:
            for transaction in transactions:
                # Convert UTC timestamp to epoch for sorting
                transaction_processor = transaction['transactionProcessor']
                if transaction_processor == AUTHORIZE_DOT_NET_CLIENT_TYPE:
                    settlement_time = datetime.fromisoformat(transaction['batch']['settlementTimeUTC'])
                    epoch_timestamp = int(settlement_time.timestamp())
                    month_key = settlement_time.strftime('%Y-%m')

                    # Create the composite keys
                    pk = f'COMPACT#{compact}#TRANSACTIONS#MONTH#{month_key}'
                    sk = (
                        f'COMPACT#{compact}#TIME#{epoch_timestamp}#BATCH#{transaction["batch"]["batchId"]}'
                        f'#TX#{transaction["transactionId"]}'
                    )

                    # Store the full transaction record along with the keys
                    item = {'pk': pk, 'sk': sk, **transaction}
                    batch.put_item(Item=item)
                else:
                    raise ValueError(f'Unsupported transaction processor: {transaction_processor}')

    def get_transactions_in_range(self, compact: str, start_epoch: int, end_epoch: int) -> dict:
        """
        Get all transactions for a compact within a given epoch timestamp range.

        :param compact: The compact name
        :param start_epoch: Start epoch timestamp (inclusive)
        :param end_epoch: End epoch timestamp (inclusive)
        :return: Dict containing transactions
        """
        # Calculate the month keys we need to query based on the epoch timestamps
        start_date = datetime.fromtimestamp(start_epoch)
        end_date = datetime.fromtimestamp(end_epoch)
        
        start_month = start_date.strftime('%Y-%m')
        end_month = end_date.strftime('%Y-%m')

        # Build query parameters
        query_params = {
            'Limit': 500,  # Max items per page
            'ScanIndexForward': True,  # Sort by time ascending
        }

        all_items = []
        
        # Query start month
        start_month_items = self._query_transactions_for_month(
            compact=compact,
            month=start_month,
            start_epoch=start_epoch,
            end_epoch=end_epoch,
            query_params=query_params
        )
        all_items.extend(start_month_items)

        # If end month is different, query that month as well
        if end_month != start_month:
            end_month_items = self._query_transactions_for_month(
                compact=compact,
                month=end_month,
                start_epoch=start_epoch,
                end_epoch=end_epoch,
                query_params=query_params
            )
            all_items.extend(end_month_items)

        return all_items

    def _query_transactions_for_month(
        self,
        compact: str,
        month: str,
        start_epoch: int,
        end_epoch: int,
        query_params: dict,
    ) -> None:
        """
        Query transactions for a specific month with pagination.

        :param compact: The compact name
        :param month: Month to query in YYYY-MM format
        :param start_epoch: Start epoch timestamp
        :param end_epoch: End epoch timestamp
        :param query_params: Query parameters dict
        :param all_items: List to append results to
        """
        all_matching_transactions = []
        last_evaluated_key = None
        while True:
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key

            response = self.config.transaction_history_table.query(
                KeyConditionExpression=(
                    'pk = :pk AND sk BETWEEN :start_sk AND :end_sk'
                ),
                ExpressionAttributeValues={
                    ':pk': f'COMPACT#{compact}#TRANSACTIONS#MONTH#{month}',
                    ':start_sk': f'COMPACT#{compact}#TIME#{start_epoch}',
                    ':end_sk': f'COMPACT#{compact}#TIME#{end_epoch}'
                },
                **query_params
            )
            
            all_matching_transactions.extend(response.get('Items', []))
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break

        return all_matching_transactions
