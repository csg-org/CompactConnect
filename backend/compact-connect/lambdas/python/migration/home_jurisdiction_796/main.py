from boto3.dynamodb.conditions import Attr
from cc_common.config import config, logger
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse


class HomeJurisdictionMigration(CustomResourceHandler):
    """Migration for removing deprecated homeJurisdictionSelection records and updating provider records."""

    def on_create(self, properties: dict) -> None:
        do_migration(properties)

    def on_update(self, properties: dict) -> None:
        do_migration(properties)

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        No roll-back on delete.
        """


on_event = HomeJurisdictionMigration('home-jurisdiction-796')


def do_migration(_properties: dict) -> None:
    """
    This migration performs the following:
    - Scans the provider table for all homeJurisdictionSelection records
    - For each homeJurisdictionSelection record, updates the associated provider record's
      currentHomeJurisdiction field with the selected jurisdiction
    - Deletes the homeJurisdictionSelection records
    - Handles batching for cases where there are more than 100 records to update
    """
    logger.info('Starting home jurisdiction selection migration')

    # Scan for all homeJurisdictionSelection records
    home_jurisdiction_selections = []
    scan_pagination = {}

    while True:
        response = config.provider_table.scan(
            FilterExpression=Attr('type').eq('homeJurisdictionSelection'),
            **scan_pagination,
        )

        items = response.get('Items', [])
        home_jurisdiction_selections.extend(items)
        logger.info(f'Found {len(items)} homeJurisdictionSelection records in current scan batch')

        # Check if we need to continue pagination
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

        scan_pagination = {'ExclusiveStartKey': last_evaluated_key}

    logger.info(f'Found {len(home_jurisdiction_selections)} total homeJurisdictionSelection records to process')

    if not home_jurisdiction_selections:
        logger.info('No homeJurisdictionSelection records found, migration complete')
        return

    # Process records in batches of 50 (DynamoDB transaction limit is 100 items,
    # and each record generates 2 items: 1 update + 1 delete)
    batch_size = 50
    success_count = 0
    error_count = 0

    for i in range(0, len(home_jurisdiction_selections), batch_size):
        batch = home_jurisdiction_selections[i : i + batch_size]
        logger.info(f'Processing batch {i // batch_size + 1} with {len(batch)} records')

        try:
            _process_batch(batch)
            success_count += len(batch)
            logger.info(f'Successfully processed batch {i // batch_size + 1}')
        except Exception as e:  # noqa: BLE001
            logger.exception(f'Error processing batch {i // batch_size + 1}', exc_info=e)
            error_count += len(batch)

    # Log final statistics
    logger.info(f'Migration completed: {success_count} records processed successfully, {error_count} errors')
    if error_count > 0:
        raise RuntimeError(f'Home jurisdiction migration completed with {error_count} errors')


def _process_batch(home_jurisdiction_selections: list[dict]) -> None:
    """
    Process a batch of homeJurisdictionSelection records.

    Args:
        home_jurisdiction_selections: List of homeJurisdictionSelection records to process
    """
    transaction_items = []

    for selection_record in home_jurisdiction_selections:
        try:
            # Extract the selected jurisdiction from the homeJurisdictionSelection record
            selected_jurisdiction = selection_record.get('jurisdiction')
            if not selected_jurisdiction:
                logger.warning(
                    'homeJurisdictionSelection record missing jurisdiction field',
                    pk=selection_record.get('pk'),
                    sk=selection_record.get('sk'),
                )
                continue

            # Determine the provider record key
            provider_pk = selection_record['pk']
            provider_sk = f'{selection_record["compact"]}#PROVIDER'

            # Add transaction item to update the provider record
            transaction_items.append(
                {
                    'Update': {
                        'TableName': config.provider_table.table_name,
                        'Key': {
                            'pk': {'S': provider_pk},
                            'sk': {'S': provider_sk},
                        },
                        'UpdateExpression': 'SET currentHomeJurisdiction = :jurisdiction',
                        'ExpressionAttributeValues': {
                            ':jurisdiction': {'S': selected_jurisdiction},
                        },
                    }
                }
            )

            # Add transaction item to delete the homeJurisdictionSelection record
            transaction_items.append(
                {
                    'Delete': {
                        'TableName': config.provider_table.table_name,
                        'Key': {
                            'pk': {'S': selection_record['pk']},
                            'sk': {'S': selection_record['sk']},
                        },
                    }
                }
            )

            logger.info(
                'Prepared transaction items for homeJurisdictionSelection',
                provider_pk=provider_pk,
                provider_sk=provider_sk,
                selected_jurisdiction=selected_jurisdiction,
                selection_pk=selection_record['pk'],
                selection_sk=selection_record['sk'],
            )

        except Exception as e:  # noqa: BLE001
            logger.exception(
                'Error preparing transaction items for homeJurisdictionSelection record',
                exc_info=e,
                pk=selection_record.get('pk'),
                sk=selection_record.get('sk'),
            )
            raise

    # Execute the transaction
    if transaction_items:
        logger.info(f'Executing transaction with {len(transaction_items)} items')
        config.dynamodb_client.transact_write_items(TransactItems=transaction_items)
        logger.info('Transaction completed successfully')
    else:
        logger.warning('No valid transaction items to process in this batch')
