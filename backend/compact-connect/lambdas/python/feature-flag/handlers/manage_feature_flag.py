"""
Custom resource handler for managing StatSig feature flags.

This handler manages feature flag lifecycle through CloudFormation custom resources,
automatically creating and configuring flags across different environments.
"""

import os

from cc_common.config import logger
from custom_resource_handler import CustomResourceHandler, CustomResourceResponse
from feature_flag_client import StatSigFeatureFlagClient


class ManageFeatureFlagHandler(CustomResourceHandler):
    """Handler for managing StatSig feature flags as custom resources"""

    def __init__(self):
        super().__init__('ManageFeatureFlag')
        self.environment = os.environ['ENVIRONMENT_NAME']
        # Create a StatSig client with console API access
        self.client = StatSigFeatureFlagClient(environment=self.environment)

    def on_create(self, properties: dict) -> CustomResourceResponse | None:
        """
        Handle Create events for feature flags.

        Creates or updates the feature flag based on environment and autoEnable setting.

        :param properties: ResourceProperties containing flagName, autoEnable, customAttributes
        :return: CustomResourceResponse with PhysicalResourceId
        """
        flag_name = properties.get('flagName')
        auto_enable = properties.get('autoEnable', False)
        custom_attributes = properties.get('customAttributes')

        if not flag_name:
            raise ValueError('flagName is required in ResourceProperties')

        logger.info(
            'Creating feature flag resource',
            flag_name=flag_name,
            environment=self.environment,
            auto_enable=auto_enable,
        )

        # Create or update the flag - client handles all environment-specific logic
        flag_data = self.client.upsert_flag(flag_name, auto_enable, custom_attributes)

        # Handle the case where no action was taken (beta/prod with autoEnable=False and no existing flag)
        if not flag_data:
            logger.warning('Feature flag not created (autoEnable=False in beta/prod)', flag_name=flag_name)
            return None

        # Extract gate ID from response
        gate_id = flag_data.get('data', {}).get('id') or flag_data.get('id')

        logger.info('Feature flag resource created/updated successfully', flag_name=flag_name, gate_id=gate_id)

        # Return the gate ID as the PhysicalResourceId for tracking
        return {'PhysicalResourceId': f'feature-flag-{flag_name}-{self.environment}', 'Data': {'gateId': gate_id}}

    def on_update(self, properties: dict) -> CustomResourceResponse | None:
        """
        Flags are not updated once created in an environment.

        :param properties: ResourceProperties containing updated values
        :return: None (no-op)
        """
        return None

    def on_delete(self, properties: dict) -> CustomResourceResponse | None:
        """
        Handle Delete events for feature flags.

        Removes the environment rule from the feature gate. If it's the last environment,
        deletes the gate entirely.

        :param properties: ResourceProperties containing flagName
        :return: Optional response data
        """
        flag_name = properties.get('flagName')

        if not flag_name:
            raise ValueError('flagName is required in ResourceProperties')

        logger.info('Deleting feature flag resource', flag_name=flag_name, environment=self.environment)

        # Delete flag or remove current environment
        # The delete_flag method handles all logic internally (fetching, checking environments, etc.)
        result = self.client.delete_flag(flag_name)

        if result is None:
            logger.info('Feature gate does not exist, nothing to delete', flag_name=flag_name)
        elif result is True:
            logger.info('Feature gate fully deleted (was last environment)', flag_name=flag_name)
        else:
            logger.info('Removed current environment from feature gate', flag_name=flag_name)

        return None


# Lambda handler
handler = ManageFeatureFlagHandler()


def on_event(event: dict, context) -> dict | None:
    """Lambda handler function for CloudFormation custom resource events"""
    return handler(event, context)
