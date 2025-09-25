# ruff: noqa: N801, N815  invalid-name

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.exceptions import ClientError
from marshmallow import Schema, ValidationError
from marshmallow.fields import Dict as DictField
from marshmallow.fields import Nested, String
from marshmallow.validate import Length
from statsig import StatsigEnvironmentTier, StatsigOptions, statsig
from statsig.statsig_user import StatsigUser


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
        pass

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
            secret_data = json.loads(response['SecretString'])

            return secret_data

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

    pass


class FeatureFlagValidationException(FeatureFlagException):
    """Exception raised when feature flag validation fails"""

    pass


# Implementing Classes


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
        self._is_initialized = False

        # Retrieve StatSig configuration from AWS Secrets Manager
        try:
            secret_name = f'compact-connect/env/{environment}/statsig/credentials'
            secret_data = self._get_secret(secret_name)
            self._server_secret_key = secret_data.get('serverKey')

            if not self._server_secret_key:
                raise FeatureFlagException(f"Secret '{secret_name}' does not contain required 'serverKey' field")

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
            # Map environment tier string to StatsigEnvironmentTier enum
            tier_mapping = {
                'prod': StatsigEnvironmentTier.production,
                'beta': StatsigEnvironmentTier.staging,
                'test': StatsigEnvironmentTier.development,
            }

            # default to development for all other environments (ie sandbox environments)
            tier = tier_mapping.get(self.environment.lower(), StatsigEnvironmentTier.development)
            options = StatsigOptions(tier=tier)

            statsig.initialize(self._server_secret_key, options=options).wait()
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
            enabled = statsig.check_gate(statsig_user, request.flagName)

            return FeatureFlagResult(
                enabled=enabled,
                flag_name=request.flagName,
            )

        except Exception as e:
            # If it's already a FeatureFlagException, re-raise it
            if isinstance(e, (FeatureFlagException, FeatureFlagValidationException)):
                raise

            # Otherwise, wrap it in a FeatureFlagException
            raise FeatureFlagException(f"Failed to check feature flag '{request.flagName}': {e}") from e

    def _shutdown(self):
        """
        Shutdown the StatSig client to flush event logs to statsig.
        """
        if self._is_initialized:
            statsig.shutdown().wait()
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
