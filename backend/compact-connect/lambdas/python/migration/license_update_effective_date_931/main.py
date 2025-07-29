from datetime import datetime

from boto3.dynamodb.conditions import Attr
from cc_common.config import config, logger
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse


class CreateEffectiveDateMigration(CustomResourceHandler):
    """Migration for adding effective date and create date to all privilege update records"""

    def on_create(self, properties: dict) -> None:
        do_migration(properties)

    def on_update(self, properties: dict) -> None:
        do_migration(properties)

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        No roll-back on delete.
        """


on_event = CreateEffectiveDateMigration('license-update-effective-date-931')


def do_migration(_properties: dict) -> None:
    """
    This migration performs the following:
    - Scans the provider table for all license update records
    - For each update record, adds effectiveDate and createDate equal to that updates dateOfUpdate
    - Handles batching for cases where there are more than 100 records to update
    """
    logger.info('Starting license update date fields migration')

    # Scan for all privilege update records
    license_updates = []
    scan_pagination = {}

    while True:
        response = config.provider_table.scan(
            FilterExpression=Attr('type').eq('licenseUpdate'),
            **scan_pagination,
        )

        items = response.get('Items', [])
        license_updates.extend(items)
        logger.info(f'Found {len(items)} license update records in current scan batch')

        # Check if we need to continue pagination
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

        scan_pagination = {'ExclusiveStartKey': last_evaluated_key}

    logger.info(f'Found {len(license_updates)} total update records to process')

    if not license_updates:
        logger.info('No license update records found, migration complete')
        return

    # Process records in batches of 50
    batch_size = 50
    success_count = 0
    error_count = 0

    for i in range(0, len(license_updates), batch_size):
        batch = license_updates[i : i + batch_size]
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
        raise RuntimeError(f'License update migration completed with {error_count} errors')


def _process_batch(license_updates: list[dict]) -> None:
    """
    Process a batch of privilege update records.

    Args:
        license_updates: List of privilegeUpdate records to process
    """
    transaction_items = []

    for update_record in license_updates:
        try:
            # Extract the dateOfUpdate from the license update record
            datetime_of_update = update_record.get('dateOfUpdate')
            if not datetime_of_update:
                logger.warning(
                    'update record missing datetime_of_update field',
                    pk=update_record.get('pk'),
                    sk=update_record.get('sk'),
                )
                continue
            date_of_update = datetime.fromisoformat(datetime_of_update).date().isoformat()

            # Determine the provider record key
            provider_pk = update_record['pk']
            provider_sk = update_record['sk']

            # Add transaction item to update the provider record
            transaction_items.append(
                {
                    'Update': {
                        'TableName': config.provider_table.table_name,
                        'Key': {
                            'pk': {'S': provider_pk},
                            'sk': {'S': provider_sk},
                        },
                        'UpdateExpression': 'SET createDate = :createDate, effectiveDate = :effectiveDate',
                        'ExpressionAttributeValues': {
                            ':createDate': {'S': datetime_of_update},
                            ':effectiveDate': {'S': date_of_update},
                        },
                    }
                }
            )

            logger.info(
                'Prepared update items with create and effective date',
                provider_pk=provider_pk,
                provider_sk=provider_sk,
                update_pk=update_record['pk'],
                update_sk=update_record['sk'],
            )

        except Exception as e:  # noqa: BLE001
            logger.exception(
                'Error preparing update items for update record',
                exc_info=e,
                pk=update_record.get('pk'),
                sk=update_record.get('sk'),
            )
            raise

    # Execute the transaction
    if transaction_items:
        logger.info(f'Executing transaction with {len(transaction_items)} items')
        config.dynamodb_client.transact_write_items(TransactItems=transaction_items)
        logger.info('Transaction completed successfully')
    else:
        logger.warning('No valid transaction items to process in this batch')
