
from boto3.dynamodb.conditions import Key
from cc_common.config import config, logger
from cc_common.data_model.provider_record_util import ProviderRecordType, ProviderRecordUtility
from cc_common.data_model.schema.license.record import LicenseRecordSchema, LicenseUpdateRecordSchema
from cc_common.data_model.schema.privilege.record import PrivilegeRecordSchema, PrivilegeUpdateRecordSchema
from cc_common.data_model.schema.provider.record import ProviderRecordSchema
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse


class MultiLicenseMigration(CustomResourceHandler):
    """Migration for the multi-license feature."""

    def on_create(self, properties: dict) -> CustomResourceResponse | None:
        do_migration(properties)

    def on_update(self, properties: dict) -> CustomResourceResponse | None:
        do_migration(properties)

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        No roll-back on delete.
        """


on_event = MultiLicenseMigration('569-multi-license')


def do_migration(_properties: dict) -> None:
    """
    Migrates privileges and licenses to the new multi-license model by:

    1) Scanning all providers on the config.fam_giv_mid_index_name index
    2) For each provider, query for all records under the partition key
    3) For each record, transform it to the new multi-license model, then write it back to the database
    4) Find the 'best license' for the provider, save for reference in privilege records

    Provider records:
      - Remove `licenseNumber` and `licenseType` from the provider record
      - Put the updated record
    License records:
      - Reserialize through its RecordSchema to generate the new sk
      - Put the new license record
      - Delete the old license record
    Privilege records:
      - Add `licenseJurisdiction` and `licenseType` fields, copied from the 'best license' `jurisdiction` and
        `licenseType` fields, respectively
      - Reserialize through its RecordSchema to generate the new sk
      - Put the new privilege record
      - Delete the old privilege record
    LicenseUpdate records:
      - Reserialize through its RecordSchema to generate the new sk
      - Put the new licenseUpdate record
      - Delete the old licenseUpdate record
    PrivilegeUpdate records:
      - Add `previous.licenseJurisdiction` and `previous.licenseType` fields, copied from the 'best license'
      `jurisdiction` and `licenseType` fields, respectively
      - Reserialize through its RecordSchema to generate the new sk
      - Put the new privilegeUpdate record
      - Delete the old privilegeUpdate record
    """
    # Initialize schemas
    license_schema = LicenseRecordSchema()
    license_update_schema = LicenseUpdateRecordSchema()
    privilege_schema = PrivilegeRecordSchema()
    privilege_update_schema = PrivilegeUpdateRecordSchema()
    provider_schema = ProviderRecordSchema()

    # Track migration statistics
    stats = {
        'providers_processed': 0,
        'providers_updated': 0,
        'licenses_updated': 0,
        'privileges_updated': 0,
        'license_updates_updated': 0,
        'privilege_updates_updated': 0,
        'errors': 0,
        'compacts_processed': set(),
    }

    logger.info('Starting multi-license migration')

    # Scan all providers in a single pass
    scan_pagination = {}
    while True:
        # Use scan operation on the fam_giv_mid index to find all provider records
        provider_response = config.provider_table.scan(
            IndexName=config.fam_giv_mid_index_name, FilterExpression=Key('type').eq('provider'), **scan_pagination
        )

        provider_records = provider_response.get('Items', [])
        logger.info(f'Found {len(provider_records)} providers in current scan batch')

        # Process each provider
        for provider_record in provider_records:
            provider_id = provider_record.get('providerId')
            compact = provider_record.get('compact')
            stats['providers_processed'] += 1
            stats['compacts_processed'].add(compact)

            with logger.append_context_keys(provider_id=provider_id, compact=compact):
                logger.info('Processing provider')

                try:
                    # Query all records for this provider
                    partition_key = f'{compact}#PROVIDER#{provider_id}'
                    provider_data_response = config.provider_table.query(
                        KeyConditionExpression=Key('pk').eq(partition_key)
                    )

                    all_provider_data = provider_data_response.get('Items', [])

                    logger.debug('Found records for provider', record_count=len(all_provider_data))

                    # Extract records by type
                    license_records = ProviderRecordUtility.get_records_of_type(
                        all_provider_data, ProviderRecordType.LICENSE
                    )
                    privilege_records = ProviderRecordUtility.get_records_of_type(
                        all_provider_data, ProviderRecordType.PRIVILEGE
                    )
                    license_update_records = ProviderRecordUtility.get_records_of_type(
                        all_provider_data, ProviderRecordType.LICENSE_UPDATE
                    )
                    privilege_update_records = ProviderRecordUtility.get_records_of_type(
                        all_provider_data, ProviderRecordType.PRIVILEGE_UPDATE
                    )

                    logger.debug(
                        'Record counts by type',
                        licenses=len(license_records),
                        privileges=len(privilege_records),
                        license_updates=len(license_update_records),
                        privilege_updates=len(privilege_update_records),
                    )

                    # Skip if no licenses found
                    if not license_records:
                        logger.warning(f'No license records found for provider {provider_id}, skipping')
                        continue

                    # Find the best license for this provider
                    home_jurisdiction = ProviderRecordUtility.get_provider_home_state_selection(all_provider_data)
                    best_license = ProviderRecordUtility.find_best_license(license_records, home_jurisdiction)

                    with logger.append_context_keys(
                        best_license_jurisdiction=best_license['jurisdiction'],
                        best_license_type=best_license['licenseType'],
                        home_jurisdiction=home_jurisdiction,
                    ):
                        logger.debug('Using best license as reference')

                        # Process provider record
                        if 'licenseNumber' in provider_record or 'licenseType' in provider_record:
                            logger.debug('Updating provider record')
                            # Remove licenseNumber and licenseType from provider record
                            provider_record_copy = provider_record.copy()
                            if 'licenseNumber' in provider_record_copy:
                                del provider_record_copy['licenseNumber']
                            if 'licenseType' in provider_record_copy:
                                del provider_record_copy['licenseType']

                            # Add licenseJurisdiction if not present
                            if 'licenseJurisdiction' not in provider_record_copy:
                                provider_record_copy['licenseJurisdiction'] = best_license['jurisdiction']

                            # Reserialize and put back
                            updated_provider = provider_schema.dump(provider_schema.load(provider_record_copy))

                            # Remove privilegeJurisdictions if they are empty - no empty string sets in DynamoDB
                            if not updated_provider.get('privilegeJurisdictions'):
                                del updated_provider['privilegeJurisdictions']

                            config.provider_table.put_item(Item=updated_provider)
                            logger.info('Updated provider record')
                            stats['providers_updated'] += 1

                        # Process license records
                        for license_record in license_records:
                            # Save the old sk for deletion
                            old_sk = license_record['sk']
                            with logger.append_context_keys(
                                license_jurisdiction=license_record.get('jurisdiction'),
                                license_type=license_record.get('licenseType'),
                            ):
                                logger.debug('Processing license record')

                                # Reserialize through schema to generate new sk
                                updated_license = license_schema.dump(license_schema.load(license_record))

                                # Put the new license record
                                logger.debug('Putting new license record')
                                config.provider_table.put_item(Item=updated_license)

                                # Delete the old license record if sk changed
                                if old_sk != updated_license['sk']:
                                    logger.debug('Deleting old license record')
                                    config.provider_table.delete_item(Key={'pk': license_record['pk'], 'sk': old_sk})
                                    stats['licenses_updated'] += 1

                        # Process privilege records
                        for privilege_record in privilege_records:
                            # Save the old sk for deletion
                            old_sk = privilege_record['sk']
                            with logger.append_context_keys(
                                privilege_jurisdiction=privilege_record.get('jurisdiction')
                            ):
                                logger.debug('Processing privilege record')

                                # Add licenseJurisdiction and licenseType fields from best license
                                privilege_record_copy = privilege_record.copy()
                                privilege_record_copy['licenseJurisdiction'] = best_license['jurisdiction']
                                privilege_record_copy['licenseType'] = best_license['licenseType']

                                # Reserialize through schema to generate new sk
                                updated_privilege = privilege_schema.dump(privilege_schema.load(privilege_record_copy))

                                # Put the new privilege record
                                logger.debug('Putting new privilege record')
                                config.provider_table.put_item(Item=updated_privilege)

                                # Delete the old privilege record if sk changed
                                if old_sk != updated_privilege['sk']:
                                    logger.debug('Deleting old privilege record')
                                    config.provider_table.delete_item(Key={'pk': privilege_record['pk'], 'sk': old_sk})
                                    stats['privileges_updated'] += 1

                        # Process license update records
                        for license_update_record in license_update_records:
                            # Save the old sk for deletion
                            old_sk = license_update_record['sk']
                            with logger.append_context_keys(
                                license_update_license_type=license_update_record.get('licenseType'),
                                license_update_jurisdiction=license_update_record.get('jurisdiction'),
                            ):
                                logger.debug('Processing license update record')

                                # Move licenseType to main record
                                license_update_copy = license_update_record.copy()
                                if 'licenseType' not in license_update_copy:
                                    license_update_copy['licenseType'] = license_update_record['previous'].pop(
                                        'licenseType'
                                    )

                                # Reserialize through schema to generate new sk
                                updated_license_update = license_update_schema.dump(
                                    license_update_schema.load(license_update_copy)
                                )

                                # Put the new license update record
                                logger.debug('Putting new license update record')
                                config.provider_table.put_item(Item=updated_license_update)

                                # Delete the old license update record if sk changed
                                if old_sk != updated_license_update['sk']:
                                    logger.debug('Deleting old license update record')
                                    config.provider_table.delete_item(
                                        Key={'pk': license_update_record['pk'], 'sk': old_sk}
                                    )
                                    stats['license_updates_updated'] += 1

                        # Process privilege update records
                        for privilege_update_record in privilege_update_records:
                            # Save the old sk for deletion
                            old_sk = privilege_update_record['sk']
                            with logger.append_context_keys(
                                privilege_update_license_type=privilege_update_record.get('licenseType'),
                                privilege_update_jurisdiction=privilege_update_record.get('jurisdiction'),
                            ):
                                logger.debug('Processing privilege update record')

                                # Add licenseJurisdiction fields to previous
                                privilege_update_copy = privilege_update_record.copy()
                                if 'licenseJurisdiction' not in privilege_update_copy['previous']:
                                    privilege_update_copy['previous']['licenseJurisdiction'] = best_license[
                                        'jurisdiction'
                                    ]
                                # Add licenseType if it doesn't exist
                                if 'licenseType' not in privilege_update_copy:
                                    privilege_update_copy['licenseType'] = best_license['licenseType']

                                # Reserialize through schema to generate new sk
                                updated_privilege_update = privilege_update_schema.dump(
                                    privilege_update_schema.load(privilege_update_copy)
                                )

                                logger.debug('Putting new privilege update record')
                                config.provider_table.put_item(Item=updated_privilege_update)

                                # Delete the old privilege update record if sk changed
                                if old_sk != updated_privilege_update['sk']:
                                    logger.debug('Deleting old privilege update record')
                                    config.provider_table.delete_item(
                                        Key={'pk': privilege_update_record['pk'], 'sk': old_sk}
                                    )
                                    stats['privilege_updates_updated'] += 1
                except Exception as e:  # noqa: BLE001
                    logger.exception('Error processing provider', exc_info=e)
                    stats['errors'] += 1

        # Check if we need to continue pagination
        last_evaluated_key = provider_response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

        scan_pagination = {'ExclusiveStartKey': last_evaluated_key}

    # Log final statistics
    logger.info(
        'Multi-license migration completed',
        providers_processed=stats['providers_processed'],
        providers_updated=stats['providers_updated'],
        licenses_updated=stats['licenses_updated'],
        privileges_updated=stats['privileges_updated'],
        license_updates_updated=stats['license_updates_updated'],
        privilege_updates_updated=stats['privilege_updates_updated'],
        compacts_processed=len(stats['compacts_processed']),
        errors=stats['errors'],
    )
    if stats['errors'] > 0:
        raise RuntimeError('Multi-license migration completed with errors')
