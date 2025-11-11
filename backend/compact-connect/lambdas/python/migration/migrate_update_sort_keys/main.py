from boto3.dynamodb.conditions import Attr
from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import (
    LicenseUpdateData,
    PrivilegeUpdateData,
    ProviderRecordType,
    ProviderUpdateData,
)
from cc_common.exceptions import CCInternalException
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse


class UpdateRecordSortKeyMigration(CustomResourceHandler):
    """Migration for migrating update record sort keys to support license upload rollbacks"""

    def on_create(self, properties: dict) -> None:
        do_migration(properties)

    def on_update(self, properties: dict) -> None:
        """
        No-op on delete.
        """

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        No-op on delete.
        """


on_event = UpdateRecordSortKeyMigration('update-record-sort-keys')


def do_migration(_properties: dict) -> None:
    """
    This migration performs the following:
    - Scans the provider table for all privilege update records
    - For each update record, adds effectiveDate and createDate equal to that updates dateOfUpdate
    - Handles batching for cases where there are more than 100 records to update
    """
    logger.info('Starting update record sort key migration')

    # Scan for all privilege update records
    update_records = []
    scan_pagination = {}

    while True:
        response = config.provider_table.scan(
            FilterExpression=Attr('type').eq(ProviderRecordType.LICENSE_UPDATE)
            | Attr('type').eq(ProviderRecordType.PROVIDER_UPDATE)
            | Attr('type').eq(ProviderRecordType.PRIVILEGE_UPDATE),
            **scan_pagination,
        )

        items = response.get('Items', [])
        update_records.extend(items)
        logger.info(f'Found {len(items)} privilege update records in current scan batch')

        # Check if we need to continue pagination
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

        scan_pagination = {'ExclusiveStartKey': last_evaluated_key}

    logger.info(f'Found {len(update_records)} total update records to process')

    if not update_records:
        logger.info('No update records found, migration complete')
        return

    # Process records in batches of 50 (DynamoDB transaction limit is 100 items,
    # and each record generates 2 items: 1 update + 1 delete)
    batch_size = 50

    for i in range(0, len(update_records), batch_size):
        batch = update_records[i : i + batch_size]
        logger.info(f'Processing batch {i // batch_size + 1} with {len(batch)} records')

        _process_batch(batch)
        logger.info(f'Processed batch {i // batch_size + 1}')


def _generate_delete_transaction_item(pk: str, sk: str) -> dict:
    """
    Generate a delete transaction item for a provider record.
    :param pk: The primary key of the provider record
    :param sk: The sort key of the provider record
    :return: Delete transaction item
    """
    return {
        'Delete': {
            'TableName': config.provider_table.table_name,
            'Key': {
                'pk': pk,
                'sk': sk,
            },
        }
    }


def _generate_put_transaction_item(item: dict) -> dict:
    """
    Generate a put transaction item for a provider record.
    :param item: The provider record to put.
    :return: Put transaction item
    """
    return {
        'Put': {
            'TableName': config.provider_table.table_name,
            'Item': item,
        }
    }


def _generate_transaction_items(original_update_record: dict) -> list[dict]:
    """
    In the case of a provider update record, we add a createDate field based on the dateOfUpdate field.
    Then we use the ProviderUpdateData class to serialize the record and return the transaction items.
    (one to delete the old record and one to create the new record)

    :param original_update_record: The provider update record to process
    :return: List of transaction items
    """
    # grab the old pk and sk from the object
    old_pk = original_update_record['pk']
    old_sk = original_update_record['sk']
    record_type = original_update_record.get('type')
    if record_type == ProviderRecordType.PROVIDER_UPDATE:
        data_class = ProviderUpdateData
    elif record_type == ProviderRecordType.LICENSE_UPDATE:
        data_class = LicenseUpdateData
    elif record_type == ProviderRecordType.PRIVILEGE_UPDATE:
        data_class = PrivilegeUpdateData
    else:
        logger.error('invalid record type found', record_type=record_type, pk=old_pk, sk=old_sk)
        raise CCInternalException('invalid record type found')

    # Performing deserialization/serialization on the record, which will generate
    # the new pk/sks values we are migrating to.

    update_data = data_class.from_database_record(original_update_record)
    migrated_provider_update_record = update_data.serialize_to_database_record()
    # retain original dateOfUpdate value
    migrated_provider_update_record['dateOfUpdate'] = original_update_record['dateOfUpdate']

    logger.info(
        'Prepared update items for create date',
        old_pk=old_pk,
        old_sk=old_sk,
        updated_pk=migrated_provider_update_record['pk'],
        updated_sk=migrated_provider_update_record['sk'],
    )

    # delete old record with old pk/sk, and create new one
    return [
        _generate_delete_transaction_item(pk=old_pk, sk=old_sk),
        _generate_put_transaction_item(migrated_provider_update_record),
    ]


def _process_batch(update_records: list[dict]) -> None:
    """
    Process a batch of privilege update records.

    :param update_records: List of update records to process
    """
    transaction_items = []

    for update_record in update_records:
        try:
            transaction_items.extend(_generate_transaction_items(update_record))
        except Exception as e:  # noqa: BLE001
            logger.error(
                'Error preparing update items for update record, skipping.',
                exc_info=e,
                pk=update_record.get('pk'),
                sk=update_record.get('sk'),
            )

    # Execute the transaction
    if transaction_items:
        logger.info(f'Executing transaction with {len(transaction_items)} items')
        config.provider_table.meta.client.transact_write_items(TransactItems=transaction_items)
        logger.info('Transaction completed successfully')
    else:
        logger.warning('No valid transaction items to process in this batch')
