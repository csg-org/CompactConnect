from boto3.dynamodb.conditions import Key

from cc_common.config import _Config, logger
from cc_common.data_model.schema.attestation import AttestationRecordSchema
from cc_common.data_model.schema.compact import CompactConfigurationData
from cc_common.data_model.schema.compact.common import COMPACT_TYPE
from cc_common.data_model.schema.compact.record import CompactRecordSchema
from cc_common.data_model.schema.jurisdiction import JurisdictionConfigurationData
from cc_common.data_model.schema.jurisdiction.common import JURISDICTION_TYPE
from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema
from cc_common.exceptions import CCInternalException, CCNotFoundException
from cc_common.utils import logger_inject_kwargs


class CompactConfigurationClient:
    """Client interface for compact configuration dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config
        self.attestation_schema = AttestationRecordSchema()
        self.compact_schema = CompactRecordSchema()
        self.jurisdiction_schema = JurisdictionRecordSchema()

    def get_attestation(self, *, compact: str, attestation_id: str, locale: str = 'en') -> dict:
        """
        Get the latest version of an attestation.

        :param compact: The compact name
        :param attestation_id: The attestation id used to query.
        :param locale: The language code for the attestation text (defaults to 'en')
        :return: The attestation record
        :raises CCNotFoundException: If no attestation is found
        """
        logger.info('Getting attestation', compact=compact, attestation_type=attestation_id, locale=locale)

        pk = f'COMPACT#{compact}#ATTESTATIONS'
        sk_prefix = f'COMPACT#{compact}#LOCALE#{locale}#ATTESTATION#{attestation_id}#VERSION#'
        response = self.config.compact_configuration_table.query(
            KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(sk_prefix),
            ScanIndexForward=False,  # Sort in descending order
            Limit=1,  # We only want the latest version
        )

        items = response.get('Items', [])
        if not items:
            raise CCNotFoundException(f'No attestation found for type "{attestation_id}" in locale "{locale}"')

        # Load and return the latest version through the schema
        return self.attestation_schema.load(items[0])

    def get_attestations_by_locale(self, *, compact: str, locale: str = 'en') -> dict[str, dict]:
        """
        Get all attestations for a compact and locale, keyed by attestation ID.
        Returns only the latest version of each attestation.

        :param compact: The compact name
        :param locale: The language code for the attestation text (defaults to 'en')
        :return: Dictionary of attestation records keyed by attestation ID
        """
        logger.info('Getting all attestations', compact=compact, locale=locale)

        pk = f'COMPACT#{compact}#ATTESTATIONS'
        sk_prefix = f'COMPACT#{compact}#LOCALE#{locale}#ATTESTATION#'
        response = self.config.compact_configuration_table.query(
            KeyConditionExpression=Key('pk').eq(pk) & Key('sk').begins_with(sk_prefix),
            ScanIndexForward=False,  # Sort in descending order to get latest versions first
        )

        # Group by attestation ID and take the first (latest) version
        attestations_by_id = {}
        for item in response.get('Items', []):
            attestation = self.attestation_schema.load(item)
            attestation_id = attestation['attestationId']
            if attestation_id not in attestations_by_id:
                attestations_by_id[attestation_id] = attestation

        return attestations_by_id

    def get_compact_configuration(self, compact: str) -> CompactConfigurationData:
        """
        Get the configuration for a specific compact.

        :param compact: The compact abbreviation
        :return: Compact configuration model
        :raises CCNotFoundException: If the compact configuration is not found
        """
        logger.info('Getting compact configuration', compact=compact)

        pk = f'{compact}#CONFIGURATION'
        sk = f'{compact}#CONFIGURATION'

        response = self.config.compact_configuration_table.get_item(Key={'pk': pk, 'sk': sk})

        item = response.get('Item')
        if not item:
            raise CCNotFoundException(f'No configuration found for compact "{compact}"')

        # Load through schema and convert to Compact model
        return CompactConfigurationData.from_database_record(item)

    def save_compact_configuration(self, compact_configuration: CompactConfigurationData) -> None:
        """
        Save the compact configuration, preserving existing fields like paymentProcessorPublicFields.
        If a record exists, it merges the new values with the existing record to preserve all fields.

        :param compact_configuration: The compact configuration data
        """
        logger.info('Saving compact configuration', compactAbbr=compact_configuration.compactAbbr)

        try:
            existing_compact_config = self.get_compact_configuration(compact_configuration.compactAbbr)
        except CCNotFoundException:
            logger.info('Existing compact configuration not found.', compact=compact_configuration.compactAbbr)
            existing_compact_config = None

        if existing_compact_config:
            # Record exists - merge with existing data to preserve fields like paymentProcessorPublicFields
            logger.info('Updating existing compact configuration record', compactAbbr=compact_configuration.compactAbbr)

            # Load the existing record into a data class to get the existing data
            existing_data = existing_compact_config.to_dict()

            # Get the new data
            new_data = compact_configuration.to_dict()

            # Merge the data - new values override existing ones, but existing fields not in new_data are preserved
            merged_data = existing_data.copy()
            merged_data.update(new_data)

            # Handle the special case where transactionFeeConfiguration should be removed
            # If the new configuration doesn't have transactionFeeConfiguration, remove it from merged data
            if 'transactionFeeConfiguration' not in new_data and 'transactionFeeConfiguration' in merged_data:
                del merged_data['transactionFeeConfiguration']

            # Create a new CompactConfigurationData with the merged data
            merged_config = CompactConfigurationData.create_new(merged_data)
            final_serialized = merged_config.serialize_to_database_record()
        else:
            # First time creation - use the new data directly
            logger.info('Creating new compact configuration record', compactAbbr=compact_configuration.compactAbbr)
            final_serialized = compact_configuration.serialize_to_database_record()

        # Use put_item to save the final record
        self.config.compact_configuration_table.put_item(Item=final_serialized)

    def get_active_compact_jurisdictions(self, compact: str) -> list[dict]:
        """
        Get the active member jurisdictions for a specific compact.

        Note this is not the list of jurisdiction configurations defined within a compact. This is specifically the list
        of jurisdictions that are currently reported as active member jurisdictions within the compact.

        This configuration is defined in the 'active_compact_member_jurisdictions' field of the project's cdk.json file.
        It is uploaded into the table by the compact configuration uploader custom resource which runs with every new
        deployment.

        :param compact: The compact abbreviation.
        :return: List of active member jurisdictions for the compact, each object including the name,
        postal abbreviation, and abbreviation of the compact the jurisdiction is associated with.
        """
        logger.info('Getting active member jurisdictions', compact=compact)

        pk = f'COMPACT#{compact}#ACTIVE_MEMBER_JURISDICTIONS'
        sk = f'COMPACT#{compact}#ACTIVE_MEMBER_JURISDICTIONS'

        response = self.config.compact_configuration_table.get_item(Key={'pk': pk, 'sk': sk})

        item = response.get('Item')
        if not item or not item.get('active_member_jurisdictions'):
            raise CCNotFoundException(f'No active member jurisdiction data found for compact "{compact}"')

        # Return the active_member_jurisdictions list from the item
        return item['active_member_jurisdictions']

    def is_jurisdiction_live_in_compact(self, compact: str, jurisdiction: str) -> bool:
        """
        Check if a jurisdiction is live (enabled for operations) in a compact.

        :param compact: The compact abbreviation
        :param jurisdiction: The jurisdiction postal abbreviation
        :return: True if the jurisdiction is live in the compact, False otherwise
        """
        logger.info('Checking if jurisdiction is live in compact', compact=compact, jurisdiction=jurisdiction)

        try:
            compact_config = self.get_compact_configuration(compact)
        except CCNotFoundException:
            logger.info('Compact configuration not found', compact=compact)
            return False

        # Check if the jurisdiction is configured and live in the compact's configuredStates
        configured_state = next(
            (
                configured_state
                for configured_state in compact_config.configuredStates
                if configured_state['postalAbbreviation'].lower() == jurisdiction.lower()
            ),
            None,
        )

        if not configured_state:
            logger.info(
                'Jurisdiction not found in compact configured states', compact=compact, jurisdiction=jurisdiction
            )
            return False

        is_live = configured_state.get('isLive', False)
        logger.info(
            'Jurisdiction live status checked',
            compact=compact,
            jurisdiction=jurisdiction,
            is_live=is_live,
        )
        return is_live

    def get_jurisdiction_configuration(self, compact: str, jurisdiction: str) -> JurisdictionConfigurationData:
        """
        Get the configuration for a specific jurisdiction within a compact.

        :param compact: The compact abbreviation
        :param jurisdiction: The jurisdiction postal abbreviation
        :return: Jurisdiction configuration model
        :raises CCNotFoundException: If the jurisdiction configuration is not found
        """
        logger.info('Getting jurisdiction configuration', compact=compact, jurisdiction=jurisdiction)

        pk = f'{compact}#CONFIGURATION'
        sk = f'{compact}#JURISDICTION#{jurisdiction.lower()}'

        response = self.config.compact_configuration_table.get_item(Key={'pk': pk, 'sk': sk})

        item = response.get('Item')
        if not item:
            raise CCNotFoundException(
                f'No configuration found for jurisdiction "{jurisdiction}" in compact "{compact}"'
            )

        # Load through schema and convert to Jurisdiction model
        return JurisdictionConfigurationData.from_database_record(item)

    def save_jurisdiction_configuration(self, jurisdiction_config: JurisdictionConfigurationData) -> None:
        """
        Save the jurisdiction configuration and update related compact configuration if needed.

        :param jurisdiction_config: The jurisdiction configuration model
        """
        logger.info('Saving jurisdiction configuration', jurisdiction=jurisdiction_config.postalAbbreviation)

        serialized_jurisdiction = jurisdiction_config.serialize_to_database_record()
        self.config.compact_configuration_table.put_item(Item=serialized_jurisdiction)

        # Always check if jurisdiction should be in compact's configuredStates (idempotent)
        self._ensure_jurisdiction_in_configured_states_if_registration_enabled(jurisdiction_config)

    def _ensure_jurisdiction_in_configured_states_if_registration_enabled(
        self, jurisdiction_config: JurisdictionConfigurationData
    ) -> None:
        """
        Ensure that if a jurisdiction has licensee registration enabled, it appears in the compact's
        configuredStates list.

        :param jurisdiction_config: The jurisdiction configuration to check
        """
        if not jurisdiction_config.licenseeRegistrationEnabled:
            logger.debug(
                'Jurisdiction does not have licensee registration enabled - no action needed',
                compact=jurisdiction_config.compact,
                jurisdiction=jurisdiction_config.postalAbbreviation,
            )
            return

        try:
            # Get current compact configuration
            compact_config = self.get_compact_configuration(compact=jurisdiction_config.compact)
            current_configured_states = compact_config.configuredStates.copy()

            # Check if jurisdiction is already in configuredStates
            existing_postal_abbrs = {state['postalAbbreviation'].lower() for state in current_configured_states}
            jurisdiction_postal = jurisdiction_config.postalAbbreviation.lower()

            if jurisdiction_postal not in existing_postal_abbrs:
                # Add the jurisdiction with isLive: false
                new_jurisdiction = {'postalAbbreviation': jurisdiction_postal, 'isLive': False}
                current_configured_states.append(new_jurisdiction)

                logger.info(
                    'Adding jurisdiction to compact configuredStates',
                    compact=jurisdiction_config.compact,
                    jurisdiction=jurisdiction_config.postalAbbreviation,
                    new_configured_states=current_configured_states,
                )

                # Update the compact configuration
                self.update_compact_configured_states(
                    compact=jurisdiction_config.compact, configured_states=current_configured_states
                )

                logger.info(
                    'Added jurisdiction to compact configuredStates',
                    compact=jurisdiction_config.compact,
                    jurisdiction=jurisdiction_config.postalAbbreviation,
                    new_configured_states=current_configured_states,
                )
            else:
                logger.debug(
                    'Jurisdiction already exists in compact configuredStates - no action needed',
                    compact=jurisdiction_config.compact,
                    jurisdiction=jurisdiction_config.postalAbbreviation,
                )

        except CCNotFoundException as e:
            # This is unlikely, but possible if jurisdiction admins submit state config before compact admins have
            # submitted their own configurations for the first time
            # After the initial onboarding phase, if this occurs it is more likely the result of an error that needs
            # to be investigated, so we raise an exception here
            message = 'Compact configuration not found when trying to ensure jurisdiction in configuredStates'
            logger.error(
                message,
                compact=jurisdiction_config.compact,
                jurisdiction=jurisdiction_config.postalAbbreviation,
            )
            raise CCInternalException(message) from e

    @logger_inject_kwargs(logger, 'compact')
    def get_privilege_purchase_options(self, *, compact: str):
        logger.info('Getting privilege purchase options for compact')

        # Get all compact configurations (both compact and jurisdiction records)
        # Use pagination to ensure we get all records
        all_items = []
        query_params = {
            'Select': 'ALL_ATTRIBUTES',
            'KeyConditionExpression': Key('pk').eq(f'{compact}#CONFIGURATION'),
        }

        while True:
            response = self.config.compact_configuration_table.query(**query_params)
            all_items.extend(response.get('Items', []))

            # Check if there are more records to fetch
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break

            # Set up for next page
            query_params['ExclusiveStartKey'] = last_evaluated_key

        logger.info(
            'Retrieved all configuration records',
            total_items=len(all_items),
        )

        # Get the compact configuration from the response items to access configuredStates
        compact_config_item = next((item for item in all_items if item['type'] == COMPACT_TYPE), None)

        if compact_config_item and compact_config_item.get('configuredStates'):
            live_jurisdictions = {
                state['postalAbbreviation'] for state in compact_config_item['configuredStates'] if state.get('isLive')
            }

            if not live_jurisdictions:
                logger.info('No live jurisdictions found for compact. Returning empty list')
                # in this case, there is nothing to return, so we return an empty list, and let the caller decide to
                # raise an exception or not.
                return {'items': []}

            logger.info(
                'Filtering privilege purchase options by live jurisdictions',
                live_jurisdictions=list(live_jurisdictions),
            )
            # Filter jurisdictions to only include live ones
            filtered_items = [
                item
                for item in all_items
                if item.get('type') == COMPACT_TYPE
                or (
                    item.get('type') == JURISDICTION_TYPE
                    and item.get('postalAbbreviation', '').lower() in live_jurisdictions
                )
            ]

            # Return in the expected format for backward compatibility
            return {
                'items': filtered_items,
                'pagination': {
                    'pageSize': len(filtered_items),
                    'prevLastKey': None,
                    'lastKey': None,
                },
            }

        message = 'Compact configuration not found or has no configuredStates when filtering privilege purchase options'
        logger.info(
            message,
            compact_config_found=compact_config_item is not None,
            configured_states=compact_config_item.get('configuredStates') if compact_config_item else None,
        )
        # in this case, there is nothing to return, so we return an empty list, and let the caller decide to raise
        # an exception or not.
        return {'items': []}

    def set_compact_authorize_net_public_values(self, compact: str, api_login_id: str, public_client_key: str) -> None:
        """
        Set the payment processor public fields (apiLoginId and publicClientKey) for a compact's configuration.
        This is used to store the public fields needed for the frontend Accept UI integration.

        :param compact: The compact abbreviation
        :param api_login_id: The API login ID from authorize.net
        :param public_client_key: The public client key from authorize.net
        """
        logger.info('Verifying that compact configuration exists', compact=compact)
        pk = f'{compact}#CONFIGURATION'
        sk = f'{compact}#CONFIGURATION'

        response = self.config.compact_configuration_table.get_item(Key={'pk': pk, 'sk': sk})

        item = response.get('Item')
        if not item:
            raise CCNotFoundException(f'No configuration found for compact "{compact}"')

        logger.info('Setting authorize.net public values for compact', compact=compact)

        # Use UPDATE with SET to add/update the paymentProcessorPublicFields
        self.config.compact_configuration_table.update_item(
            Key={'pk': pk, 'sk': sk},
            UpdateExpression='SET paymentProcessorPublicFields = :ppf',
            ExpressionAttributeValues={':ppf': {'apiLoginId': api_login_id, 'publicClientKey': public_client_key}},
        )

    def update_compact_configured_states(self, compact: str, configured_states: list[dict]) -> None:
        """
        Update the configuredStates field for a compact configuration using DynamoDB UPDATE operation.
        This is used to add states to configuredStates when they enable licensee registration.

        :param compact: The compact abbreviation
        :param configured_states: The updated list of configured states
        """
        logger.info('Updating configured states for compact', compact=compact, configured_states=configured_states)

        pk = f'{compact}#CONFIGURATION'
        sk = f'{compact}#CONFIGURATION'

        # Use UPDATE with SET to update both configuredStates and dateOfUpdate

        self.config.compact_configuration_table.update_item(
            Key={'pk': pk, 'sk': sk},
            UpdateExpression='SET configuredStates = :cs, dateOfUpdate = :dou',
            ExpressionAttributeValues={
                ':cs': configured_states,
                ':dou': self.config.current_standard_datetime.isoformat(),
            },
        )

    def get_live_compact_jurisdictions(self, compact: str) -> list[str]:
        """
        Get all live (isLive: true) jurisdiction postal abbreviations for a specific compact.

        :param compact: The compact abbreviation
        :return: List of jurisdiction postal abbreviations that are live in the compact
        """
        logger.info('Getting live jurisdictions for compact', compact=compact)

        try:
            compact_config = self.get_compact_configuration(compact)
        except CCNotFoundException:
            logger.info('Compact configuration not found, returning empty list', compact=compact)
            return []

        # Filter configuredStates for those with isLive: true and extract postal abbreviations
        live_jurisdictions = [
            state['postalAbbreviation'] for state in compact_config.configuredStates if state.get('isLive', False)
        ]

        logger.info(
            'Retrieved live jurisdictions for compact',
            compact=compact,
            live_jurisdictions_count=len(live_jurisdictions),
        )

        return live_jurisdictions
