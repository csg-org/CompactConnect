from boto3.dynamodb.conditions import Key
from cc_common.config import config, logger
from cc_common.data_model.schema.privilege.record import DeactivationDetailsSchema
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse


class PrivilegeDeactivationNotes(CustomResourceHandler):
    """Migration for adding deactivation notes to privilege deactivation records."""

    def on_create(self, properties: dict) -> CustomResourceResponse | None:
        do_migration(properties)

    def on_update(self, properties: dict) -> CustomResourceResponse | None:
        do_migration(properties)

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        No roll-back on delete.
        """


on_event = PrivilegeDeactivationNotes('deactivation-details-566')


def do_migration(_properties: dict) -> None:
    """
    Adds the 'deactivationDetails' field to all privilege deactivation records.
    """
    logger.info('Starting deactivation notes migration')

    # Scan all privilege deactivation records in a single pass
    scan_pagination = {}
    success_count = 0
    error_count = 0
    while True:
        # only scan providerUpdate records that have an updateType of 'deactivation'
        response = config.provider_table.scan(
            FilterExpression=Key('type').eq('privilegeUpdate') & Key('updateType').eq('deactivation'),
            **scan_pagination,
        )

        privilege_deactivation_records = response.get('Items', [])
        logger.info(f'Found {len(privilege_deactivation_records)} privilege deactivation records in current scan batch')

        # Process each provider
        for privilege_deactivation_record in privilege_deactivation_records:
            try:
                # Prepare key for update_item
                key = {'pk': privilege_deactivation_record['pk'], 'sk': privilege_deactivation_record['sk']}
                retro_deactivation_details = {
                    'note': 'Notes unavailable. Privilege deactivated before notes supported.',
                    'deactivatedByStaffUserId': '00000000-0000-4000-a000-000000000000',
                    'deactivatedByStaffUserName': 'UNKNOWN',
                }
                # validate the object before storing it in the database
                DeactivationDetailsSchema().load(retro_deactivation_details)

                # Use update_item with SET expression to add deactivationDetails remove the field
                update_expression = 'SET deactivationDetails = :deactivationDetails'
                logger.info(
                    'Updating record', pk=privilege_deactivation_record['pk'], sk=privilege_deactivation_record['sk']
                )
                config.provider_table.update_item(
                    Key=key,
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues={':deactivationDetails': retro_deactivation_details},
                )
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
    logger.info(f'Added deactivation notes to {success_count} records')
    if error_count > 0:
        raise RuntimeError('deactivation notes migration completed with errors')
