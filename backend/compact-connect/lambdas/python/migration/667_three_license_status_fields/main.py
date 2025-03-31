from boto3.dynamodb.conditions import Attr
from cc_common.config import config, logger
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse


class ThreeLicenseStatusFieldsMigration(CustomResourceHandler):
    """Migration for the three license status fields."""

    def on_create(self, properties: dict) -> CustomResourceResponse | None:
        do_migration(properties)

    def on_update(self, properties: dict) -> CustomResourceResponse | None:
        do_migration(properties)

    def on_delete(self, _properties: dict) -> CustomResourceResponse | None:
        """
        No roll-back on delete.
        """


on_event = ThreeLicenseStatusFieldsMigration('667-three-license-status-fields')


def do_migration(_properties: dict) -> None:
    """
    Migrates license and provider records to have three license status fields:

    - jurisdictionStatus -> jurisdictionUploadedLicenseStatus
    - compactEligibility = 'eligible' | 'ineligible'
    - licenseStatusName = '<some string>'
    """
    logger.info('Starting three license status fields migration')

    # Scan all records in the provider table
    scan_pagination = {}
    while True:
        # Use scan operation on the fam_giv_mid index to find all provider records
        provider_response = config.provider_table.scan(
            FilterExpression=Attr('type').is_in(['provider', 'license', 'licenseUpdate']),
            **scan_pagination,
        )

        records = provider_response.get('Items', [])
        logger.info(f'Found {len(records)} records in current scan batch')

        # Process each provider
        for record in records:
            key = {
                'pk': record['pk'],
                'sk': record['sk'],
            }
            provider_id = record['providerId']
            compact = record['compact']

            with logger.append_context_keys(
                provider_id=provider_id, compact=compact, record_type=record['type'], pk=key['pk'], sk=key['sk']
            ):
                logger.info('Processing record')

                match record['type']:
                    case 'provider' | 'license':
                        logger.debug('Processing provider or license')
                        license_status = record.get(
                            'jurisdictionStatus', record.get('jurisdictionUploadedLicenseStatus', 'active')
                        )
                        # Set the new fields, remove jurisdictionStatus
                        config.provider_table.update_item(
                            Key=key,
                            UpdateExpression='SET #ju_compact_eligibility = :compact_eligibility, '
                            '#ju_license_status = :license_status, '
                            '#license_status_name = :license_status_name '
                            'REMOVE #jurisdiction_status',
                            ExpressionAttributeValues={
                                ':license_status': license_status,
                                ':compact_eligibility': 'eligible' if license_status == 'active' else 'ineligible',
                                ':license_status_name': 'SOMETHING_USEFUL',
                            },
                            ExpressionAttributeNames={
                                '#jurisdiction_status': 'jurisdictionStatus',
                                '#ju_compact_eligibility': 'jurisdictionUploadedCompactEligibility',
                                '#ju_license_status': 'jurisdictionUploadedLicenseStatus',
                                '#license_status_name': 'licenseStatusName',
                            },
                        )
                    case 'licenseUpdate':
                        logger.debug('Processing licenseUpdate')
                        # Same as provider/license but in previous
                        previous_license_status = record['previous'].get(
                            'jurisdictionStatus', record['previous'].get('jurisdictionUploadedLicenseStatus', 'active')
                        )
                        # Set the new fields, remove jurisdictionStatus
                        config.provider_table.update_item(
                            Key=key,
                            UpdateExpression='SET #previous.#ju_compact_eligibility = :compact_eligibility, '
                            '#previous.#ju_license_status = :license_status, '
                            '#previous.#license_status_name = :license_status_name '
                            'REMOVE #previous.#jurisdiction_status',
                            ExpressionAttributeValues={
                                ':license_status': previous_license_status,
                                ':compact_eligibility': 'eligible'
                                if previous_license_status == 'active'
                                else 'ineligible',
                                ':license_status_name': 'SOMETHING_USEFUL',
                            },
                            ExpressionAttributeNames={
                                '#previous': 'previous',
                                '#ju_compact_eligibility': 'jurisdictionUploadedCompactEligibility',
                                '#ju_license_status': 'jurisdictionUploadedLicenseStatus',
                                '#license_status_name': 'licenseStatusName',
                                '#jurisdiction_status': 'jurisdictionStatus',
                            },
                        )
                        # And then in `updatedValues` if needed
                        if 'jurisdictionStatus' in record.get('updatedValues', {}):
                            logger.debug('Updating updatedValues')
                            updated_license_status = record.get('updatedValues', {}).get(
                                'jurisdictionStatus',
                                record.get('updatedValues', {}).get('jurisdictionUploadedLicenseStatus', 'active'),
                            )

                            config.provider_table.update_item(
                                Key=key,
                                UpdateExpression='SET '
                                '#updatedValues.#ju_compact_eligibility = :compact_eligibility, '
                                '#updatedValues.#ju_license_status = :license_status, '
                                '#updatedValues.#license_status_name = :license_status_name '
                                'REMOVE #updatedValues.#jurisdiction_status',
                                ExpressionAttributeValues={
                                    ':license_status': updated_license_status,
                                    ':compact_eligibility': 'eligible'
                                    if updated_license_status == 'active'
                                    else 'ineligible',
                                    ':license_status_name': 'SOMETHING_ELSE_USEFUL',
                                },
                                ExpressionAttributeNames={
                                    '#updatedValues': 'updatedValues',
                                    '#ju_compact_eligibility': 'jurisdictionUploadedCompactEligibility',
                                    '#ju_license_status': 'jurisdictionUploadedLicenseStatus',
                                    '#license_status_name': 'licenseStatusName',
                                    '#jurisdiction_status': 'jurisdictionStatus',
                                },
                            )
                    case _:
                        logger.error('Unexpected record type', record_type=record['type'])
                        raise RuntimeError(f'Unexpected record type: {record["type"]}')

        # Check if we need to continue pagination
        last_evaluated_key = provider_response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break

        scan_pagination = {'ExclusiveStartKey': last_evaluated_key}
