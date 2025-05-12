from datetime import UTC, datetime

from boto3.dynamodb.conditions import Key
from cc_common.config import _Config, logger
from cc_common.data_model.schema.transaction.record import TransactionRecordSchema

AUTHORIZE_DOT_NET_CLIENT_TYPE = 'authorize.net'


class TransactionClient:
    """Client interface for transaction history data dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config

    def store_transactions(self, transactions: list[dict]) -> None:
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
                    transaction_schema = TransactionRecordSchema()

                    serialized_record = transaction_schema.dump(transaction)
                    batch.put_item(Item=serialized_record)
                else:
                    raise ValueError(f'Unsupported transaction processor: {transaction_processor}')

    def get_transactions_in_range(self, compact: str, start_epoch: int, end_epoch: int) -> list[dict]:
        """
        Get all transactions for a compact within a given epoch timestamp range.

        :param compact: The compact name
        :param start_epoch: Start epoch timestamp (inclusive)
        :param end_epoch: End epoch timestamp (inclusive)
        :return: List of transactions
        """
        # Calculate the month keys we need to query based on the epoch timestamps
        start_date = datetime.fromtimestamp(start_epoch, tz=UTC)

        # Build query parameters
        query_params = {
            'Limit': 500,  # Max items per page
            'ScanIndexForward': True,  # Sort by time ascending
        }

        all_items = []

        # Generate list of months to query
        current_date = start_date.replace(day=1)
        current_epoch = current_date.timestamp()
        months_to_query = []
        # here we check if the end epoch is greater than the current epoch
        # if it is, we add the current month to the list of months to query
        # we then move to the first day of the next month
        # we repeat this process until the end epoch is less than the current epoch
        while end_epoch > current_epoch:
            months_to_query.append(current_date.strftime('%Y-%m'))
            # Move to first day of next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

            current_epoch = current_date.timestamp()

        # Query each month in the range
        for month in months_to_query:
            month_items = self._query_transactions_for_month(
                compact=compact, month=month, start_epoch=start_epoch, end_epoch=end_epoch, query_params=query_params
            )
            all_items.extend(month_items)

        return all_items

    def _query_transactions_for_month(
        self,
        compact: str,
        month: str,
        start_epoch: int,
        end_epoch: int,
        query_params: dict,
    ) -> list[dict]:
        """
        Query transactions for a specific month with pagination.

        :param compact: The compact name
        :param month: Month to query in YYYY-MM format
        :param start_epoch: Start epoch timestamp
        :param end_epoch: End epoch timestamp
        :param query_params: Query parameters dict
        :return: List of transactions for the month
        """
        all_matching_transactions = []
        last_evaluated_key = None
        while True:
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key

            pk = f'COMPACT#{compact}#TRANSACTIONS#MONTH#{month}'
            start_sk = f'COMPACT#{compact}#TIME#{start_epoch}'
            end_sk = f'COMPACT#{compact}#TIME#{end_epoch}'
            response = self.config.transaction_history_table.query(
                KeyConditionExpression=Key('pk').eq(pk) & Key('sk').between(start_sk, end_sk),
                **query_params,
            )

            all_matching_transactions.extend(response.get('Items', []))

            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break

        return all_matching_transactions

    def _set_privilege_id_in_line_item(self, line_items: list[dict], item_id_prefix: str, privilege_id: str):
        for line_item in line_items:
            if line_item.get('itemId').lower().startswith(item_id_prefix.lower()):
                line_item['privilegeId'] = privilege_id

    def add_privilege_ids_to_transactions(self, compact: str, transactions: list[dict]) -> list[dict]:
        """
        Add privilege IDs to transaction line items based on the jurisdiction they were purchased for.

        :param compact: The compact name
        :param transactions: List of transaction records to process
        :return: Modified list of transactions with privilege IDs added to line items
        """
        for transaction in transactions:
            line_items = transaction['lineItems']
            licensee_id = transaction['licenseeId']
            # Extract jurisdictions from line items with format priv:{compact}-{jurisdiction}-{license type abbr}
            jurisdictions_to_process = set()
            for line_item in line_items:
                item_id = line_item['itemId']
                if item_id.startswith('priv:'):
                    parts = item_id.split('-')
                    jurisdiction = parts[1].lower()
                    jurisdictions_to_process.add(jurisdiction)

            # Query for privilege records using the GSI
            gsi_pk = f'COMPACT#{compact}#TX#{transaction["transactionId"]}#'
            response = self.config.provider_table.query(
                IndexName=self.config.compact_transaction_id_gsi_name,
                KeyConditionExpression=Key('compactTransactionIdGSIPK').eq(gsi_pk),
            )

            # Process each privilege record
            for jurisdiction in jurisdictions_to_process:
                # Currently, we only support one license type per transaction when purchasing privileges
                # so we can just use this prefix to find the matching privilege record
                item_id_prefix = f'priv:{compact}-{jurisdiction}'
                # find the first privilege record for the jurisdiction that matches the provider ID
                matching_privilege = next(
                    (
                        item
                        for item in response.get('Items', [])
                        if item['jurisdiction'].lower() == jurisdiction and item['providerId'] == licensee_id
                    ),
                    None,
                )
                if matching_privilege:
                    record_type = matching_privilege['type']
                    privilege_id = None
                    if record_type == 'privilege':
                        privilege_id = matching_privilege['privilegeId']
                    elif record_type == 'privilegeUpdate':
                        privilege_id = matching_privilege['previous']['privilegeId']

                    # Find and update the matching line item(s) using prefix match
                    self._set_privilege_id_in_line_item(
                        line_items=line_items, item_id_prefix=item_id_prefix, privilege_id=privilege_id
                    )
                else:
                    logger.error(
                        'No matching jurisdiction privilege record found for transaction. '
                        'Cannot determine privilege id for this transaction',
                        compact=compact,
                        transactionId=transaction['transactionId'],
                        jurisdiction=jurisdiction,
                        provider_id=licensee_id,
                        matching_privilege_records=response.get('Items', []),
                    )
                    # we set the privilege id to UNKNOWN, so that it will be visible in the report
                    self._set_privilege_id_in_line_item(
                        line_items=line_items, item_id_prefix=item_id_prefix, privilege_id='UNKNOWN'
                    )

        return transactions
