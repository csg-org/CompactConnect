"""
Feature flag client for checking feature flags via the internal API.

This module provides a simple, stateless interface for checking feature flags
from other Lambda functions without direct dependency on the feature flag provider.
"""

from dataclasses import dataclass
from typing import Any

import requests

from cc_common.config import config, logger


@dataclass
class FeatureFlagContext:
    """
    Context information for feature flag evaluation.

    This context is used by the feature flag provider to determine whether a flag
    should be enabled for a specific user or scenario.

    :param user_id: Optional user identifier for user-specific flag evaluation
    :param custom_attributes: Optional dictionary of custom attributes for advanced targeting
                             (e.g., {'licenseType': 'physician', 'jurisdiction': 'oh'})
    """

    user_id: str | None = None
    custom_attributes: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the context to a dictionary for API serialization.

        :return: Dictionary representation of the context, excluding None values
        """
        result = {}
        if self.user_id is not None:
            result['userId'] = self.user_id
        if self.custom_attributes:
            result['customAttributes'] = self.custom_attributes
        return result


def is_feature_enabled(
    flag_name: str, context: FeatureFlagContext | None = None, fail_open: bool = False
) -> bool:
    """
    Check if a feature flag is enabled.

    This function calls the internal feature flag API endpoint to determine
    if a feature flag is enabled for the given context.

    :param flag_name: The name of the feature flag to check
    :param context: Optional FeatureFlagContext for feature flag evaluation
    :param fail_open: If True, return True on errors; if False, return False on errors (default: False)
    :return: True if the feature flag is enabled, False otherwise (or fail_open value on error)

    Example:
        # Simple check without context
        is_feature_enabled('test-feature')
        True

        # Check with user ID
        is_feature_enabled(
            'test-feature',
            context=FeatureFlagContext(user_id='user123')
        )
        False

        # Check with user ID and custom attributes
        is_feature_enabled(
            'test-feature',
            context=FeatureFlagContext(
                user_id='user456',
                custom_attributes={'licenseType': 'lpc', 'jurisdiction': 'oh'}
            )
        )
        True

        # Fail open - if API fails, allow access
        is_feature_enabled('critical-feature', fail_open=True)

        # Fail closed - if API fails, deny access (default)
        is_feature_enabled('new-feature', fail_open=False)
    """
    try:
        api_base_url = _get_api_base_url()
        endpoint_url = f'{api_base_url}/v1/flags/check'

        # Build request payload
        payload = {'flagName': flag_name}
        if context:
            payload['context'] = context.to_dict()

        response = requests.post(
            endpoint_url,
            json=payload,
            timeout=5,
            headers={'Content-Type': 'application/json'},
        )

        # Raise exception for HTTP errors (4xx, 5xx)
        response.raise_for_status()

        # Parse response
        response_data = response.json()

        # Extract and return the 'enabled' field
        if 'enabled' not in response_data:
            logger.info('Invalid response format - return fail_open value', response_data=response_data)
            # Invalid response format - return fail_open value
            return fail_open

        return bool(response_data['enabled'])

    except Exception as e:
        # Any error (timeout, network, parsing, etc.) - return fail_open value
        logger.info('Error checking feature flag - return fail_open value', exc_info=e)
        return fail_open


def _get_api_base_url() -> str:
    """
    Get the API base URL from environment variables.

    :return: The base URL for the API
    :raises ValueError: If API_BASE_URL is not set
    """
    api_base_url = config.api_base_url
    # Remove trailing slash if present
    return api_base_url.rstrip('/')

