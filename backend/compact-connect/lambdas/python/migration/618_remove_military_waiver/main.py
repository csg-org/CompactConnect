from cc_common.config import config, logger
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse


class MilitaryWaiverRemoval(CustomResourceHandler):
    """Migration for removing military wavier field."""

    def on_create(self, properties: dict) -> CustomResourceResponse | None:
        do_migration(properties)

    def on_update(self, properties: dict) -> CustomResourceResponse | None:
        do_migration(properties)

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        No roll-back on delete.
        """


on_event = MilitaryWaiverRemoval('618-remove-military-waiver')


def do_migration(_properties: dict) -> None:
    """
    Removes the 'militaryWaiver' field from all license and provider records.
    """
    logger.info('Starting militaryWaiverField removal')

    # Scan all providers in a single pass
    scan_pagination = {}
    success_count = 0
    error_count = 0
    while True:
        response = config.provider_table.scan(**scan_pagination)

        provider_records = response.get('Items', [])
        logger.info(f'Found {len(provider_records)} providers in current scan batch')

        # Process each provider
        for provider_record in provider_records:
            try:
                if not provider_record.get('type'):
                    logger.info('No type defined. Skipping record.', pk=provider_record['pk'], sk=provider_record['sk'])
                    continue
                # Prepare key for update_item
                key = {
                    'pk': provider_record['pk'],
                    'sk': provider_record['sk']
                }

                if provider_record['type'] == 'provider' or provider_record['type'] == 'license':
                    # Use update_item with REMOVE expression to safely remove the field
                    update_expression = "REMOVE militaryWaiver"
                    logger.info('Updating record', pk=provider_record['pk'], sk=provider_record['sk'])
                    config.provider_table.update_item(
                        Key=key,
                        UpdateExpression=update_expression
                    )
                    success_count += 1
                elif provider_record['type'] == 'licenseUpdate':
                    # For licenseUpdate, we need to remove from both previous and updatedValues objects
                    update_expression = "REMOVE previous.militaryWaiver, updatedValues.militaryWaiver"
                    logger.info('Updating licenseUpdate record', pk=provider_record['pk'], sk=provider_record['sk'])
                    config.provider_table.update_item(
                        Key=key,
                        UpdateExpression=update_expression
                    )
                    success_count += 1
                else:
                    logger.info('Skipping record', pk=provider_record['pk'], sk=provider_record['sk'])
                    continue

            except Exception as e:  # noqa: BLE001
                logger.exception('Error processing record', exc_info=e)
                error_count += 1

        # Check if we need to continue pagination
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

        scan_pagination = {'ExclusiveStartKey': last_evaluated_key}

    # Log final statistics
    logger.info(f"Removed militaryWaiver field from {success_count} records")
    if error_count > 0:
        raise RuntimeError('military waiver removal migration completed with errors')
