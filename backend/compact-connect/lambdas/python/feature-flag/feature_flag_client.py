# ruff: noqa: N801, N815  invalid-name

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import boto3
import requests
from botocore.exceptions import ClientError
from marshmallow import Schema, ValidationError
from marshmallow.fields import Dict as DictField
from marshmallow.fields import Nested, String
from marshmallow.validate import Length
from statsig_python_core import Statsig, StatsigOptions, StatsigUser


@dataclass
class FeatureFlagRequest:
    """Request object for feature flag evaluation"""

    flagName: str  # noqa: N815
    context: dict[str, Any]


@dataclass
class FeatureFlagResult:
    """Result of a feature flag check"""

    enabled: bool
    flag_name: str
    metadata: dict[str, Any] | None = None


class BaseFeatureFlagCheckRequestSchema(Schema):
    """
    Base schema for feature flag check requests.

    All provider-specific schemas should inherit from this base schema.
    """

    flagName = String(required=True, allow_none=False, validate=Length(1, 100))  # noqa: N815


class FeatureFlagClient(ABC):
    """
    Abstract base class for feature flag clients.

    This interface provides a consistent way to interact with different
    feature flag providers (StatSig, LaunchDarkly, etc.) while hiding
    the underlying implementation details.
    """

    def __init__(self, request_schema: Schema):
        """
        Initialize the feature flag client with a provider-specific schema.

        :param request_schema: Schema instance for validating requests
        """
        self._request_schema = request_schema

    def validate_request(self, request_body: dict[str, Any]) -> dict[str, Any]:
        """
        Validate the feature flag check request using the provider-specific schema.

        :param request_body: Raw request body dictionary
        :return: Validated request data
        :raises FeatureFlagValidationException: If validation fails
        """
        try:
            return self._request_schema.load(request_body)
        except ValidationError as e:
            raise FeatureFlagValidationException(f'Invalid request: {e.messages}') from e

    @abstractmethod
    def check_flag(self, request: FeatureFlagRequest) -> FeatureFlagResult:
        """
        Check if a feature flag is enabled for the given request.

        :param request: FeatureFlagRequest containing flag name and context
        :return: FeatureFlagResult indicating if flag is enabled
        :raises FeatureFlagException: If flag check fails
        """

    @abstractmethod
    def upsert_flag(
        self, flag_name: str, auto_enable: bool = False, custom_attributes: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create or update a feature flag in the provider.

        In test environment: Creates a new flag if it doesn't exist.
        In beta/prod: Updates existing flag to add current environment if auto_enable is True.

        :param flag_name: Name of the feature flag to create
        :param auto_enable: If True, enable the flag in the current environment
        :param custom_attributes: Optional custom attributes for targeting rules
        :return: Dictionary containing flag data (including 'id' field)
        :raises FeatureFlagException: If operation fails
        """

    @abstractmethod
    def get_flag(self, flag_name: str) -> dict[str, Any] | None:
        """
        Retrieve a feature flag by name.

        :param flag_name: Name of the feature flag to retrieve
        :return: Flag data dictionary, or None if not found
        :raises FeatureFlagException: If retrieval fails
        """

    @abstractmethod
    def delete_flag(self, flag_name: str) -> bool:
        """
        Delete a feature flag or remove current environment from it.

        If the flag has multiple environments, only the current environment is removed.
        If the flag has only the current environment, the entire flag is deleted.

        :param flag_name: Name of the feature flag to delete
        :return: True if flag was fully deleted, False if only environment was removed, None if flag doesn't exist
        :raises FeatureFlagException: If operation fails
        """

    def _get_secret(self, secret_name: str) -> dict[str, Any]:
        """
        Retrieve a secret from AWS Secrets Manager and return it as a JSON object.

        :param secret_name: Name of the secret in AWS Secrets Manager
        :return: Dictionary containing the secret data
        :raises FeatureFlagException: If secret retrieval fails
        """
        try:
            # Create a Secrets Manager client
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
            )

            # Retrieve the secret value
            response = client.get_secret_value(SecretId=secret_name)

            # Parse the secret string as JSON
            return json.loads(response['SecretString'])

        except ClientError as e:
            error_code = e.response['Error']['Code']
            raise FeatureFlagException(f"Failed to retrieve secret '{secret_name}': {error_code}") from e
        except json.JSONDecodeError as e:
            raise FeatureFlagException(f"Secret '{secret_name}' does not contain valid JSON") from e
        except Exception as e:
            raise FeatureFlagException(f"Unexpected error retrieving secret '{secret_name}': {e}") from e


# Custom exceptions
class FeatureFlagException(Exception):
    """Base exception for feature flag operations"""


class FeatureFlagValidationException(FeatureFlagException):
    """Exception raised when feature flag validation fails"""


# Implementing Classes

STATSIG_DEVELOPMENT_TIER = 'development'
STATSIG_STAGING_TIER = 'staging'
STATSIG_PRODUCTION_TIER = 'production'

STATSIG_ENVIRONMENT_MAPPING = {
    'prod': STATSIG_PRODUCTION_TIER,
    'beta': STATSIG_STAGING_TIER,
    'test': STATSIG_DEVELOPMENT_TIER,
}

# StatSig Console API configuration
STATSIG_API_BASE_URL = 'https://statsigapi.net/console/v1'
STATSIG_API_VERSION = '20240601'


class StatSigContextSchema(Schema):
    """
    StatSig-specific schema for feature flag context validation.

    Includes optional userId and customAttributes.
    """

    userId = String(required=False, allow_none=False, validate=Length(1, 100))
    customAttributes = DictField(required=False, allow_none=False, load_default=dict)


class StatSigFeatureFlagCheckRequestSchema(BaseFeatureFlagCheckRequestSchema):
    """
    StatSig-specific schema for feature flag check requests.

    Includes optional context with userId and customAttributes.
    """

    context = Nested(StatSigContextSchema, required=False, allow_none=False, load_default=dict)


class StatSigFeatureFlagClient(FeatureFlagClient):
    """
    StatSig implementation of the FeatureFlagClient interface.

    This client uses StatSig's Python SDK to check feature flags.
    Configuration is handled through environment variables.
    """

    def __init__(self, environment: str):
        """
        Initialize the StatSig client.

        :param environment: The CompactConnect environment the system is running in ('test', 'beta', 'prod')
        """
        # Initialize parent class with StatSig-specific schema
        super().__init__(StatSigFeatureFlagCheckRequestSchema())

        self.environment = environment
        self.statsig_client = None
        self._is_initialized = False

        # Retrieve StatSig configuration from AWS Secrets Manager
        secret_name = f'compact-connect/env/{environment}/statsig/credentials'
        try:
            secret_data = self._get_secret(secret_name)
            self._server_secret_key = secret_data.get('serverKey')
            self._console_api_key = secret_data.get('consoleKey')

            if not self._server_secret_key:
                raise FeatureFlagException(f"Secret '{secret_name}' does not contain required 'serverKey' field")

            # If console API key not provided, try to get it from secret
            if not self._console_api_key:
                raise FeatureFlagException(f"Secret '{secret_name}' does not contain required 'consoleKey' field")

        except Exception as e:
            if isinstance(e, FeatureFlagException):
                raise
            raise FeatureFlagException(
                f"Failed to retrieve StatSig configuration from secret '{secret_name}': {e}"
            ) from e

        self._initialize_statsig()

    def _initialize_statsig(self):
        """Initialize the StatSig SDK if not already initialized"""
        if self._is_initialized:
            return

        try:
            # default to development for all other environments (ie sandbox environments)
            tier = STATSIG_ENVIRONMENT_MAPPING.get(self.environment.lower(), STATSIG_DEVELOPMENT_TIER)
            options = StatsigOptions()
            options.environment = tier

            self.statsig_client = Statsig(self._server_secret_key, options=options)
            self.statsig_client.initialize().wait()
            self._is_initialized = True

        except Exception as e:
            raise FeatureFlagException(f'Failed to initialize StatSig client: {e}') from e

    def _create_statsig_user(self, context: dict[str, Any]) -> StatsigUser:
        """Convert context dictionary to StatsigUser"""
        user_data = {
            'user_id': context.get('userId') or 'default_cc_user',
        }

        # Add custom attributes if provided
        custom_attributes = context.get('customAttributes', {})
        if custom_attributes:
            user_data.update({'custom': custom_attributes})

        return StatsigUser(**user_data)

    def check_flag(self, request: FeatureFlagRequest) -> FeatureFlagResult:
        """
        Check if a feature flag is enabled using StatSig.

        :param request: FeatureFlagRequest containing flag name and context
        :return: FeatureFlagResult indicating if flag is enabled
        :raises FeatureFlagException: If flag check fails
        """
        if not request.flagName:
            raise FeatureFlagValidationException('Flag name cannot be empty')

        try:
            self._initialize_statsig()

            # Create StatSig user from context
            statsig_user = self._create_statsig_user(request.context)

            # Check the gate (feature flag) using StatSig
            enabled = self.statsig_client.check_gate(statsig_user, request.flagName)

            return FeatureFlagResult(
                enabled=enabled,
                flag_name=request.flagName,
            )

        except (FeatureFlagException, FeatureFlagValidationException) as e:
            # If it's already a FeatureFlagException, re-raise it
            raise e
        except Exception as e:
            # Otherwise, wrap it in a FeatureFlagException
            raise FeatureFlagException(f"Failed to check feature flag '{request.flagName}': {e}") from e

    def _make_console_api_request(
        self, method: str, endpoint: str, data: dict[str, Any] | None = None
    ) -> requests.Response:
        """
        Make a request to the StatSig Console API.

        :param method: HTTP method (GET, POST, PATCH, DELETE)
        :param endpoint: API endpoint (e.g., '/gates')
        :param data: Optional request payload
        :return: Response object
        :raises FeatureFlagException: If API key not configured or request fails
        """
        if not self._console_api_key:
            raise FeatureFlagException(
                'Console API key not configured. Required for management operations (create, update, delete).'
            )

        url = f'{STATSIG_API_BASE_URL}{endpoint}'
        headers = {
            'STATSIG-API-KEY': self._console_api_key,
            'STATSIG-API-VERSION': STATSIG_API_VERSION,
            'Content-Type': 'application/json',
        }

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, data=json.dumps(data), timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, headers=headers, data=json.dumps(data), timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f'Unsupported HTTP method: {method}')

            return response

        except requests.exceptions.RequestException as e:
            raise FeatureFlagException(f'StatSig Console API request failed: {e}') from e

    def upsert_flag(
        self, flag_name: str, auto_enable: bool = False, custom_attributes: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create or update a feature gate in StatSig.

        In test environment: Creates a new gate if it doesn't exist.
        In beta/prod: Updates existing gate to add current environment if auto_enable is True.

        :param flag_name: Name of the feature gate
        :param auto_enable: If True, enable the flag in the current environment (beta/prod only)
        :param custom_attributes: Optional custom attributes for targeting
        :return: Flag data (with 'id' field)
        :raises FeatureFlagException: If operation fails
        """
        # Check if gate already exists
        existing_gate = self.get_flag(flag_name)

        # According to our current policy, we always deploy the flag from our testing
        # environment, and perform updates on any environment if the flag was set to auto enabled
        if not existing_gate and (auto_enable or self.environment.lower() == 'test'):
            # Create new gate with the environment associated with it
            return self._create_new_gate(flag_name, custom_attributes)

        # according to our current policy, we always deploy
        if existing_gate and (auto_enable or self.environment.lower() == 'test'):
            # Gate exists - update custom attributes if provided
            gate_id = existing_gate.get('id')
            if custom_attributes:
                updated_gate = self._prepare_gate_update(existing_gate, custom_attributes)
                self._update_gate(gate_id, updated_gate)
            return existing_gate  # Return existing gate data

        # Return empty dict (no action taken)
        return {}

    def _create_new_gate(self, flag_name: str, custom_attributes: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Create a new feature gate in StatSig with the current environment enabled.

        :param flag_name: Name of the feature gate
        :param custom_attributes: Optional custom attributes for targeting
        :return: Created gate data (with 'id' field)
        :raises FeatureFlagException: If creation fails
        """
        # Get the StatSig environment tier for the current environment
        statsig_tier = STATSIG_ENVIRONMENT_MAPPING.get(self.environment.lower(), STATSIG_DEVELOPMENT_TIER)

        # Build conditions for custom attributes if provided
        conditions = []
        if custom_attributes:
            for key, value in custom_attributes.items():
                conditions.append({'type': 'custom_field', 'targetValue': [value], 'field': key, 'operator': 'any'})

        # Build the feature gate payload
        gate_payload = {
            'name': flag_name,
            'description': f'Feature gate managed by CDK for {flag_name} feature',
            'isEnabled': True,
            'rules': [
                {
                    'name': 'environment_toggle',
                    'conditions': conditions,
                    'environments': [statsig_tier],
                    'passPercentage': 100,
                }
            ],
        }

        response = self._make_console_api_request('POST', '/gates', gate_payload)

        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise FeatureFlagException(f'Failed to create feature gate: {response.status_code} - {response.text[:200]}')

    def _prepare_gate_update(
        self, gate_data: dict[str, Any], custom_attributes: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Prepare an updated gate configuration with new custom attributes and/or environment.

        :param gate_data: Original gate configuration
        :param custom_attributes: New custom attributes to set (None = no change)
        :return: Updated gate configuration
        """
        updated_gate_configuration = gate_data.copy()

        # Find the environment_toggle rule
        for rule in updated_gate_configuration.get('rules', []):
            if rule.get('name') == 'environment_toggle':
                # Update custom attributes if provided
                if custom_attributes is not None:
                    new_conditions = []
                    for key, value in custom_attributes.items():
                        # if the value is a list, leave it as is
                        # else, convert to list
                        if isinstance(value, str):
                            value = [value]
                        elif not isinstance(value, list):
                            raise FeatureFlagException(f'Custom attribute value must be a string or list: {value}')

                        new_conditions.append(
                            {'type': 'custom_field', 'targetValue': value, 'field': key, 'operator': 'any'}
                        )
                    rule['conditions'] = new_conditions

                # Add current environment if requested
                statsig_tier = STATSIG_ENVIRONMENT_MAPPING.get(self.environment.lower(), STATSIG_DEVELOPMENT_TIER)
                current_environments = rule.get('environments', [])
                if statsig_tier not in current_environments:
                    rule['environments'] = current_environments + [statsig_tier]
                break

        return updated_gate_configuration

    def _update_gate(self, gate_id: str, gate_data: dict[str, Any]) -> bool:
        """
        Update a feature gate using the PATCH endpoint.

        :param gate_id: ID of the feature gate to update
        :param gate_data: Updated gate configuration
        :return: True if successful
        :raises FeatureFlagException: If update fails
        """
        response = self._make_console_api_request('PATCH', f'/gates/{gate_id}', gate_data)

        if response.status_code in [200, 204]:
            return True
        else:
            raise FeatureFlagException(f'Failed to update feature gate: {response.status_code} - {response.text[:200]}')

    def get_flag(self, flag_name: str) -> dict[str, Any] | None:
        """
        Retrieve a feature gate by name.

        :param flag_name: Name of the feature gate to retrieve
        :return: Gate data dictionary, or None if not found
        :raises FeatureFlagException: If retrieval fails
        """
        response = self._make_console_api_request('GET', '/gates')

        if response.status_code == 200:
            gates_data = response.json()

            for gate in gates_data.get('data', []):
                if gate.get('name') == flag_name:
                    return gate

            return None
        else:
            raise FeatureFlagException(f'Failed to fetch gates: {response.status_code} - {response.text[:200]}')

    def delete_flag(self, flag_name: str) -> bool | None:
        """
        Delete a feature gate or remove current environment from it.

        If the gate has multiple environments, only the current environment is removed.
        If the gate has only the current environment, the entire gate is deleted.

        :param flag_name: Name of the feature flag to delete
        :return: True if flag was fully deleted, False if only environment was removed, None if flag doesn't exist
        :raises FeatureFlagException: If operation fails
        """
        # Get the flag data first
        flag_data = self.get_flag(flag_name)
        if not flag_data:
            return None  # Flag doesn't exist

        flag_id = flag_data.get('id')
        if not flag_id:
            raise FeatureFlagException(f'Flag data missing ID field: {flag_name}')

        # Get the StatSig environment tier for the current environment
        statsig_tier = STATSIG_ENVIRONMENT_MAPPING[self.environment.lower()]

        # Find the environment_toggle rule and check environment count
        environments_in_flag = []
        for rule in flag_data.get('rules', []):
            if rule.get('name') == 'environment_toggle':
                environments_in_flag = rule.get('environments', [])
                break

        # Check if current environment is the only one (or one of only one)
        if len(environments_in_flag) <= 1 and statsig_tier in environments_in_flag:
            # Delete the entire gate
            response = self._make_console_api_request('DELETE', f'/gates/{flag_id}')

            if response.status_code in [200, 204]:
                return True  # Flag fully deleted
            else:
                raise FeatureFlagException(
                    f'Failed to delete feature gate: {response.status_code} - {response.text[:200]}'
                )
        else:
            # Remove only the current environment
            removed = self._remove_current_environment_from_flag(flag_id, flag_data)
            return False if removed else False  # Environment removed, not full deletion

    def _remove_current_environment_from_flag(self, flag_id: str, flag_data: dict[str, Any]) -> bool:
        """
        Remove the current environment from a feature gate.

        :param flag_id: ID of the feature gate
        :param flag_data: Current flag configuration
        :return: True if environment was removed, False if it wasn't present
        :raises FeatureFlagException: If operation fails
        """
        # Get the StatSig environment tier for the current environment
        statsig_tier = STATSIG_ENVIRONMENT_MAPPING.get(self.environment.lower(), STATSIG_DEVELOPMENT_TIER)

        # Check if current environment is present
        environment_present = False
        for rule in flag_data.get('rules', []):
            if rule.get('name') == 'environment_toggle':
                current_environments = rule.get('environments', [])
                if statsig_tier in current_environments:
                    environment_present = True
                break

        if not environment_present:
            return False

        # Prepare updated gate with environment removed
        updated_gate = flag_data.copy()
        for rule in updated_gate.get('rules', []):
            if rule.get('name') == 'environment_toggle':
                current_environments = rule.get('environments', [])
                if statsig_tier in current_environments:
                    current_environments.remove(statsig_tier)
                    rule['environments'] = current_environments
                break

        # Update the gate
        self._update_gate(flag_id, updated_gate)
        return True

    def _shutdown(self):
        """
        Shutdown the StatSig client to flush event logs to statsig.
        """
        if self._is_initialized:
            self.statsig_client.shutdown().wait()
            self._is_initialized = False

    def __del__(self):
        """
        Shutdown the StatSig client when the object is destroyed.

        This should be called to flush event logs to statsig when the lambda container shuts down.
        """
        self._shutdown()


def create_feature_flag_client(environment: str) -> FeatureFlagClient:
    """
    Factory function to create a FeatureFlagClient instance.

    This allows easy swapping of implementations based on configuration.
    Currently only supports StatSig, but can be extended for other providers.

    :param environment: The CompactConnect environment the system is running in ('test', 'beta', 'prod')
    :return: FeatureFlagClient instance
    :raises FeatureFlagException: If client creation fails
    """
    return StatSigFeatureFlagClient(environment=environment)
