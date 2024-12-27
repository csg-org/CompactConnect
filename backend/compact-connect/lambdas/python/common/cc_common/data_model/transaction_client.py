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
                    sk = f'COMPACT#{compact}#TIME#{epoch_timestamp}#BATCH#{transaction["batch"]["batchId"]}#TX#{transaction["transactionId"]}'

                    # Store the full transaction record along with the keys
                    item = {
                        'pk': pk,
                        'sk': sk,
                        **transaction
                    }
                    batch.put_item(Item=item)
                else:
                    raise ValueError(f'Unsupported transaction processor: {transaction_processor}')
