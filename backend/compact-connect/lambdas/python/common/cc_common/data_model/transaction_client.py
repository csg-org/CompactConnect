from datetime import datetime

from cc_common.config import _Config


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
                settlement_time = datetime.strptime(transaction['batch']['settlementTimeUTC'], '%Y-%m-%dT%H:%M:%S.%fZ')
                epoch_timestamp = int(settlement_time.timestamp())
                month_key = settlement_time.strftime('%Y-%m')

                # Create the composite keys
                pk = f'COMPACT#{compact}#TRANSACTIONS#MONTH#{month_key}'
                sk = f'COMPACT#{compact}#TIME#{epoch_timestamp}#BATCH#{transaction["batch"]["batch_id"]}#TX#{transaction["transactionId"]}'

                # Store the full transaction record along with the keys
                item = {
                    'pk': pk,
                    'sk': sk,
                    **transaction
                }
                batch.put_item(Item=item)
