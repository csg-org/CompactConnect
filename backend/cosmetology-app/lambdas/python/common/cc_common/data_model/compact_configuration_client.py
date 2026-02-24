from cc_common.config import _Config, logger
from cc_common.data_model.schema.compact import CompactConfigurationData
from cc_common.data_model.schema.compact.record import CompactRecordSchema
from cc_common.data_model.schema.jurisdiction import JurisdictionConfigurationData
from cc_common.data_model.schema.jurisdiction.record import JurisdictionRecordSchema
from cc_common.exceptions import CCInternalException, CCNotFoundException


class CompactConfigurationClient:
    """Client interface for compact configuration dynamodb queries"""

    def __init__(self, config: _Config):
        self.config = config
        self.compact_schema = CompactRecordSchema()
        self.jurisdiction_schema = JurisdictionRecordSchema()

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
        Save the compact configuration.
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
            # Record exists - merge with existing data to preserve all fields
            logger.info('Updating existing compact configuration record', compactAbbr=compact_configuration.compactAbbr)

            # Load the existing record into a data class to get the existing data
            existing_data = existing_compact_config.to_dict()

            # Get the new data
            new_data = compact_configuration.to_dict()

            # Merge the data - new values override existing ones, but existing fields not in new_data are preserved
            merged_data = existing_data.copy()
            merged_data.update(new_data)

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

        live_jurisdictions = self.get_live_compact_jurisdictions(compact)
        is_live = jurisdiction in live_jurisdictions
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
