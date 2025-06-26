from boto3.dynamodb.conditions import Attr, Key
from cc_common.config import config, logger
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse


class CompactConfiguredStatesMigration(CustomResourceHandler):
    """Migration for adding configuredStates field to existing compact configurations."""

    def on_create(self, properties: dict) -> None:
        do_migration(properties)

    def on_update(self, properties: dict) -> None:
        do_migration(properties)

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        No roll-back on delete.
        """


on_event = CompactConfiguredStatesMigration('compact-configured-states-871')


def do_migration(_properties: dict) -> None:
    """
    This migration performs the following:
    - Scans compact configuration table for all compact configuration records
    - For each compact configuration, checks if it already has configuredStates field
    - If not, initializes configuredStates based on existing jurisdictions with licenseeRegistrationEnabled: true
    - Sets isLive: true for all states to maintain backwards compatibility
    """
    logger.info('Starting compact configuredStates migration')

    # Get all compact abbreviations from the context
    compacts = config.compacts
    logger.info(f'Processing {len(compacts)} compacts for configuredStates migration')

    success_count = 0
    error_count = 0

    for compact in compacts:
        try:
            logger.info(f'Processing compact: {compact}')

            # Check if compact configuration exists before attempting migration
            pk = f'{compact}#CONFIGURATION'
            sk = f'{compact}#CONFIGURATION'

            response = config.compact_configuration_table.get_item(Key={'pk': pk, 'sk': sk})
            compact_item = response.get('Item')

            if not compact_item:
                logger.info(f'Compact configuration not found for {compact}, skipping migration for this compact.')
                continue

            # Get all jurisdiction configurations for this compact
            configured_states = _get_configured_states_for_compact(compact)

            if not configured_states:
                logger.info(f'No jurisdictions with licenseeRegistrationEnabled found for compact {compact}')
                # Still need to set configuredStates to empty list to complete migration
                configured_states = []

            logger.info(
                f'Updating compact {compact} with configuredStates',
                configured_states=configured_states,
                count=len(configured_states),
            )

            # Update the compact configuration with the new configuredStates field
            config.compact_configuration_table.update_item(
                Key={'pk': pk, 'sk': sk},
                UpdateExpression='SET configuredStates = :configuredStates, dateOfUpdate = :dateOfUpdate',
                ExpressionAttributeValues={
                    ':configuredStates': configured_states,
                    ':dateOfUpdate': config.current_standard_datetime.isoformat(),
                },
            )

            success_count += 1
            logger.info(f'Successfully migrated compact {compact}')

        except Exception as e:  # noqa: BLE001
            logger.exception(f'Error migrating compact {compact}', exc_info=e)
            error_count += 1

    # Log final statistics
    logger.info(f'Migration completed: {success_count} compacts migrated successfully, {error_count} errors')

    if error_count > 0:
        raise RuntimeError(f'Compact configuredStates migration completed with {error_count} errors')


def _get_configured_states_for_compact(compact: str) -> list[dict]:
    """
    Get all jurisdictions for a compact that have licenseeRegistrationEnabled: true
    and return them as configuredStates entries with isLive: true for backwards compatibility.

    Args:
        compact: The compact abbreviation

    Returns:
        List of configured state dictionaries with postalAbbreviation and isLive fields
    """
    logger.info(f'Getting jurisdictions with licenseeRegistrationEnabled for compact {compact}')

    # Query for all jurisdiction configurations for this compact with licenseeRegistrationEnabled: true
    pk = f'{compact}#CONFIGURATION'
    sk_prefix = f'{compact}#JURISDICTION#'

    response = config.compact_configuration_table.query(
        KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(sk_prefix),
        FilterExpression=Attr('licenseeRegistrationEnabled').eq(True),
    )

    configured_states = []
    items = response.get('Items', [])

    for item in items:
        postal_abbr = item.get('postalAbbreviation', '').lower()
        if postal_abbr:
            configured_states.append(
                {
                    'postalAbbreviation': postal_abbr,
                    'isLive': True,  # Set to true for backwards compatibility
                }
            )
            logger.info(
                f'Found jurisdiction with licenseeRegistrationEnabled for compact {compact}', jurisdiction=postal_abbr
            )

    logger.info(
        f'Found {len(configured_states)} jurisdictions with licenseeRegistrationEnabled for compact {compact}',
        configured_states=configured_states,
    )

    return configured_states
