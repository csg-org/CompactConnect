from boto3.dynamodb.conditions import Key
from cc_common.config import config, logger
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse


class CompactConfigurationMigration(CustomResourceHandler):
    """Migration for adding deactivation notes to privilege deactivation records."""

    def on_create(self, properties: dict) -> None:
        """
        Triggers the migration process for compact and jurisdiction configuration records.
        
        Initiates the update of relevant records in the DynamoDB table by removing deprecated fields and setting new values as required.
        """
        do_migration(properties)

    def on_update(self, properties: dict) -> None:
        """
        Triggers the migration process when the resource is updated.
        
        Args:
            properties: The properties passed to the resource update event.
        """
        do_migration(properties)

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        Handles the delete event for the custom resource without performing any rollback actions.
        """


on_event = CompactConfigurationMigration('compact-configuration-783')


def do_migration(_properties: dict) -> None:
    """
    Migrates compact and jurisdiction configuration records to remove deprecated fields.
    
    Scans the DynamoDB configuration table for records of type 'compact' or 'jurisdiction', removing the deprecated 'licenseeRegistrationEnabledForEnvironments' and 'militaryDiscount' fields as appropriate. Sets 'licenseeRegistrationEnabled' to True where required. Logs progress and raises a RuntimeError if any errors occur during the migration.
    """
    logger.info('Starting compact configuration migration')

    # Scan all compact and jurisdiction configuration records
    scan_pagination = {}
    success_count = 0
    error_count = 0

    while True:
        # Scan for compact and jurisdiction records
        response = config.compact_configuration_table.scan(
            FilterExpression=Key('type').eq('compact') | Key('type').eq('jurisdiction'),
            **scan_pagination,
        )

        configuration_records = response.get('Items', [])
        logger.info(f'Found {len(configuration_records)} configuration records in current scan batch')

        # Process each record
        for record in configuration_records:
            try:
                # Prepare key for update_item
                key = {'pk': record['pk'], 'sk': record['sk']}

                # For all records (compact and jurisdiction):
                # Replace licenseeRegistrationEnabledForEnvironments with licenseeRegistrationEnabled=true
                if (
                    'licenseeRegistrationEnabledForEnvironments' in record
                    and 'militaryDiscount' in record
                    and record.get('type') == 'jurisdiction'
                ):
                    # Combined update for both fields
                    update_expression = (
                        'REMOVE licenseeRegistrationEnabledForEnvironments, militaryDiscount '
                        'SET #licRegEnabled = :licRegEnabled'
                    )
                    expression_attribute_values = {':licRegEnabled': True}
                    expression_attribute_names = {'#licRegEnabled': 'licenseeRegistrationEnabled'}

                    logger.info('Updating record with both fields', pk=record['pk'], sk=record['sk'])

                    config.compact_configuration_table.update_item(
                        Key=key,
                        UpdateExpression=update_expression,
                        ExpressionAttributeValues=expression_attribute_values,
                        ExpressionAttributeNames=expression_attribute_names,
                    )
                elif 'licenseeRegistrationEnabledForEnvironments' in record:
                    # Only update licenseeRegistrationEnabledForEnvironments
                    update_expression = (
                        'REMOVE licenseeRegistrationEnabledForEnvironments SET #licRegEnabled = :licRegEnabled'
                    )
                    expression_attribute_values = {':licRegEnabled': True}
                    expression_attribute_names = {'#licRegEnabled': 'licenseeRegistrationEnabled'}

                    logger.info('Updating registration field', pk=record['pk'], sk=record['sk'])

                    config.compact_configuration_table.update_item(
                        Key=key,
                        UpdateExpression=update_expression,
                        ExpressionAttributeValues=expression_attribute_values,
                        ExpressionAttributeNames=expression_attribute_names,
                    )
                elif 'militaryDiscount' in record and record.get('type') == 'jurisdiction':
                    # Only remove militaryDiscount for jurisdiction records
                    update_expression = 'REMOVE militaryDiscount'

                    logger.info('Removing military discount field', pk=record['pk'], sk=record['sk'])

                    config.compact_configuration_table.update_item(
                        Key=key,
                        UpdateExpression=update_expression,
                    )
                else:
                    # Skip if no updates needed
                    continue

                success_count += 1

            except Exception as e:  # noqa: BLE001
                logger.exception('Error processing record', exc_info=e)
                error_count += 1

        # Check if we need to continue pagination
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

        scan_pagination = {'ExclusiveStartKey': last_evaluated_key}

    # Log final statistics
    logger.info(f'Successfully updated {success_count} configuration records')
    if error_count > 0:
        raise RuntimeError(f'Configuration migration completed with {error_count} errors')
