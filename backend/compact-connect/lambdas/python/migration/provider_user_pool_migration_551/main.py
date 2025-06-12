from botocore.exceptions import ClientError
from cc_common.config import config, logger
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse


class ProviderUserPoolMigration(CustomResourceHandler):
    """Migration for removing compactConnectRegisteredEmailAddress field from provider records."""

    def on_create(self, properties: dict) -> None:
        do_migration(properties)

    def on_update(self, properties: dict) -> None:
        do_migration(properties)

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        No roll-back on delete.
        """


on_event = ProviderUserPoolMigration('provider-user-pool-migration-551')


def do_migration(_properties: dict) -> None:
    """
    This migration removes registration fields from all provider records since we are moving over to the new provider
    user pool:
    - compactConnectRegisteredEmailAddress
    - currentHomeJurisdiction
    """
    logger.info('Starting provider migration - removing compactConnectRegisteredEmailAddress field from all providers')

    try:
        # Scan the table for all records with type='provider' that have compactConnectRegisteredEmailAddress
        scan_kwargs = {
            'FilterExpression': '#type = :provider_type AND (attribute_exists(compactConnectRegisteredEmailAddress))',
            'ExpressionAttributeNames': {'#type': 'type'},
            'ExpressionAttributeValues': {':provider_type': 'provider'},
        }

        updated_count = 0
        scanned_count = 0

        # Paginate through all results
        while True:
            response = config.provider_table.scan(**scan_kwargs)
            items = response.get('Items', [])
            scanned_count += response.get('ScannedCount', 0)

            for item in items:
                try:
                    # Remove both registration attributes
                    config.provider_table.update_item(
                        Key={'pk': item['pk'], 'sk': item['sk']},
                        UpdateExpression='REMOVE compactConnectRegisteredEmailAddress, currentHomeJurisdiction',
                    )
                    updated_count += 1
                    logger.info(f'Removed registration fields from provider {item.get("pk", "unknown")}')

                except ClientError as e:
                    logger.error(f'Failed to update provider {item.get("pk", "unknown")}: {e}')
                    raise

            # Check if there are more results to paginate
            if 'LastEvaluatedKey' not in response:
                break
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

        logger.info(f'Migration completed. Scanned {scanned_count} records, updated {updated_count} provider records')

    except Exception as e:
        logger.error(f'Migration failed: {e}')
        raise
