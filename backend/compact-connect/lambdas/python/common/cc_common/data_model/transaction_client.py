from datetime import UTC, datetime, timedelta

from boto3.dynamodb.conditions import Key

from cc_common.config import _Config, logger
from cc_common.data_model.schema.transaction import TransactionData
from cc_common.data_model.schema.transaction.record import UnsettledTransactionRecordSchema

AUTHORIZE_DOT_NET_CLIENT_TYPE = 'authorize.net'


class TransactionClient:
    """Client interface for transaction history data dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config

    def store_transactions(self, transactions: list[TransactionData]) -> None:
        """
        Store transaction records in DynamoDB.

        :param transactions: List of transaction records to store
        """
        with self.config.transaction_history_table.batch_writer() as batch:
            for transaction in transactions:
                # Convert UTC timestamp to epoch for sorting
                transaction_processor = transaction.transactionProcessor
                if transaction_processor == AUTHORIZE_DOT_NET_CLIENT_TYPE:
                    serialized_record = transaction.serialize_to_database_record()
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

    def get_most_recent_transaction_for_compact(self, compact: str) -> TransactionData:
        """
        Get the most recent transaction for a compact.

        Starts by querying the current month's partition key (based on config.current_standard_datetime),
        then sequentially queries previous months until a record is found.

        :param compact: The compact name
        :return: The most recent transaction for the compact
        :raises ValueError: If no transactions are found for the compact
        """
        # Start with the current month
        current_date = self.config.current_standard_datetime.replace(day=1)
        # During normal operations, the most recent transaction should be no more than two days old, if there were any
        # transactions in that period. We'll look back up to three months, which should cover most reasonable
        # situations.
        max_months_to_check = 3

        for _ in range(max_months_to_check):
            month_key = current_date.strftime('%Y-%m')
            pk = f'COMPACT#{compact}#TRANSACTIONS#MONTH#{month_key}'

            # Query for the most recent transaction in this month (descending order, limit 1)
            response = self.config.transaction_history_table.query(
                KeyConditionExpression=Key('pk').eq(pk),
                ScanIndexForward=False,  # Descending order (most recent first)
                Limit=1,
            )

            items = response.get('Items', [])
            if items:
                # Found a transaction, return it
                return TransactionData.from_database_record(items[0])

            # Move to previous month
            if current_date.month == 1:
                current_date = current_date.replace(year=current_date.year - 1, month=12)
            else:
                current_date = current_date.replace(month=current_date.month - 1)

        # No transactions found after checking max_months_to_check months
        raise ValueError(f'No transactions found for compact: {compact}')

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
            item_id = line_item.get('itemId')
            if item_id and item_id.lower().startswith(item_id_prefix.lower()):
                line_item['privilegeId'] = privilege_id

    def add_privilege_information_to_transactions(
        self, compact: str, transactions: list[TransactionData]
    ) -> list[TransactionData]:
        """
        Add privilege and licensee IDs to transaction line items based on the jurisdiction they were purchased for.

        :param compact: The compact name
        :param transactions: List of transaction records to process
        :return: Modified list of transactions with privilege and licensee IDs added to line items
        """
        for transaction in transactions:
            line_items = transaction.lineItems
            # Extract jurisdictions from line items with format priv:{compact}-{jurisdiction}-{license type abbr}
            jurisdictions_to_process = set()
            for line_item in line_items:
                item_id = line_item['itemId']
                if item_id.startswith('priv:'):
                    parts = item_id.split('-')
                    jurisdiction = parts[1].lower()
                    jurisdictions_to_process.add(jurisdiction)

            # Query for privilege records using the GSI
            gsi_pk = f'COMPACT#{compact}#TX#{transaction.transactionId}#'
            response = self.config.provider_table.query(
                IndexName=self.config.compact_transaction_id_gsi_name,
                KeyConditionExpression=Key('compactTransactionIdGSIPK').eq(gsi_pk),
            )

            # Verify that the query returned at least one record
            records_for_transaction_id = response.get('Items', [])
            if not records_for_transaction_id:
                logger.error(
                    'No privilege records found for this transaction id.',
                    compact=compact,
                    transaction_id=transaction.transactionId,
                    # attempt to grab the licensee id from the authorize.net data, which may be invalid if it was masked
                    licensee_id=transaction.licenseeId,
                )
                # We mark the data as UNKNOWN so it still shows up in the history,
                # and move onto the next transaction
                for jurisdiction in jurisdictions_to_process:
                    item_id_prefix = f'priv:{compact}-{jurisdiction}'
                    # we set the privilege id to UNKNOWN, so that it will be visible in the report
                    self._set_privilege_id_in_line_item(
                        line_items=line_items, item_id_prefix=item_id_prefix, privilege_id='UNKNOWN'
                    )
                continue

            # ensure we only map to one provider for this transaction id
            provider_ids = {
                item['providerId']
                for item in records_for_transaction_id
                if item['type'] == 'privilege' or item['type'] == 'privilegeUpdate'
            }
            # there should only be one provider id in the set
            if len(provider_ids) > 1:
                logger.error(
                    'More than one matching provider id found for a transaction id.',
                    compact=compact,
                    transaction_id=transaction.transactionId,
                    # attempt to grab the licensee id from the authorize.net data, which may be invalid if it was masked
                    provider_ids=transaction.licenseeId,
                )

            # The licensee id recorded in Authorize.net cannot be trusted, as Authorize.net masks any values that look
            # like a credit card number (consecutive digits separated by dashes). We need to grab the provider id from
            # the privileges associated with this transaction and set the licensee id on the transaction to that value
            # to ensure it is valid.
            transaction.update({'licenseeId': provider_ids.pop()})

            # Process each privilege record
            for jurisdiction in jurisdictions_to_process:
                # Currently, we only support one license type per transaction when purchasing privileges
                # so we can just use this prefix to find the matching privilege record
                item_id_prefix = f'priv:{compact}-{jurisdiction}'
                # find the first privilege record for the jurisdiction that matches the provider ID
                matching_privilege = next(
                    (item for item in records_for_transaction_id if item['jurisdiction'].lower() == jurisdiction),
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
                        transactionId=transaction.transactionId,
                        jurisdiction=jurisdiction,
                        provider_id=transaction.licenseeId,
                        matching_privilege_records=response.get('Items', []),
                    )
                    # we set the privilege id to UNKNOWN, so that it will be visible in the report
                    self._set_privilege_id_in_line_item(
                        line_items=line_items, item_id_prefix=item_id_prefix, privilege_id='UNKNOWN'
                    )
            transaction.update({'lineItems': line_items})

        return transactions

    def store_unsettled_transaction(self, compact: str, transaction_id: str, transaction_date: str) -> None:
        """
        Store an unsettled transaction record in DynamoDB.

        :param compact: The compact abbreviation
        :param transaction_id: The transaction ID from the payment processor
        :param transaction_date: ISO datetime string of when the transaction was submitted
        """
        try:
            # Create the record data
            record_data = {
                'compact': compact,
                'transactionId': transaction_id,
                'transactionDate': transaction_date,
                'dateOfUpdate': datetime.now(UTC).isoformat(),
            }

            # Validate and serialize using the schema
            unsettled_schema = UnsettledTransactionRecordSchema()
            serialized_record = unsettled_schema.dump(record_data)

            self.config.transaction_history_table.put_item(Item=serialized_record)
            logger.info(
                'Stored unsettled transaction record',
                compact=compact,
                transaction_id=transaction_id,
            )
        except Exception as e:  # noqa: BLE001
            # This record is created for monitoring unsettled transactions, not business critical
            # If we fail to record it for whatever reason, log error but don't raise an exception
            logger.error(
                'Failed to store unsettled transaction record',
                compact=compact,
                transaction_id=transaction_id,
                error=str(e),
            )

    def reconcile_unsettled_transactions(self, compact: str, settled_transactions: list[TransactionData]) -> list[str]:
        """
        Reconcile unsettled transactions with settled transactions and detect old unsettled transactions.

        This method:
        1. Queries all unsettled transactions for the compact
        2. Matches them with settled transactions by transaction ID
        3. Deletes matched unsettled transactions
        4. Checks for unsettled transactions older than 48 hours

        :param compact: The compact abbreviation
        :param settled_transactions: List of settled transaction records
        :return: List of transaction IDs that have not been matched and are older than 48 hours
        (empty list if none found)
        """
        # Query all unsettled transactions for this compact
        pk = f'COMPACT#{compact}#UNSETTLED_TRANSACTIONS'
        response = self.config.transaction_history_table.query(
            KeyConditionExpression=Key('pk').eq(pk),
        )

        unsettled_transactions = response.get('Items', [])

        if not unsettled_transactions:
            logger.info('No unsettled transactions found for compact', compact=compact)
            return []

        # Create a set of settled transaction IDs for efficient lookup
        settled_transaction_ids = {tx.transactionId for tx in settled_transactions}

        # Separate matched and unmatched unsettled transactions
        matched_unsettled = []
        unmatched_unsettled = []

        for unsettled_tx in unsettled_transactions:
            if unsettled_tx['transactionId'] in settled_transaction_ids:
                matched_unsettled.append(unsettled_tx)
            else:
                unmatched_unsettled.append(unsettled_tx)

        # Batch delete matched unsettled transactions
        if matched_unsettled:
            logger.info(
                'Deleting matched unsettled transactions',
                compact=compact,
                count=len(matched_unsettled),
                settled_transaction_ids=settled_transaction_ids,
            )
            with self.config.transaction_history_table.batch_writer() as batch:
                for tx in matched_unsettled:
                    batch.delete_item(Key={'pk': tx['pk'], 'sk': tx['sk']})

        # Check for unsettled transactions older than 48 hours
        cutoff_time = datetime.now(UTC) - timedelta(hours=48)
        old_unsettled_transactions = []

        for unsettled_tx in unmatched_unsettled:
            transaction_date = datetime.fromisoformat(unsettled_tx['transactionDate'])
            if transaction_date < cutoff_time:
                old_unsettled_transactions.append(unsettled_tx['transactionId'])

        if old_unsettled_transactions:
            logger.warning(
                'Found unsettled transactions older than 48 hours',
                compact=compact,
                old_transaction_ids=old_unsettled_transactions,
            )

        return old_unsettled_transactions
