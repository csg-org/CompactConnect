"""
CDK construct for managing StatSig feature flags as custom resources.

This construct creates a CloudFormation custom resource that manages the lifecycle
of StatSig feature flags across different environments.
"""

from enum import StrEnum

from aws_cdk import CustomResource
from aws_cdk.custom_resources import Provider
from constructs import Construct


class FeatureFlagEnvironmentName(StrEnum):
    TEST = 'test'
    BETA = 'beta'
    PROD = 'prod'
    # add sandbox environment names here if needed
    SANDBOX = 'landon'


class FeatureFlagResource(Construct):
    """
    Custom resource for managing StatSig feature flags.

    This construct creates a CloudFormation custom resource that manages
    the lifecycle of a single feature flag in StatSig. The Lambda function
    and provider are shared across all flags and passed in as parameters.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        provider: Provider,
        flag_name: str,
        auto_enable_envs: list[FeatureFlagEnvironmentName],
        custom_attributes: dict[str, str | list[str]] | None = None,
        environment_name: str,
    ):
        """
        Initialize the FeatureFlagResource construct.

        :param provider: Shared CloudFormation custom resource provider
        :param flag_name: Name of the feature flag to manage
        :param auto_enable_envs: List of environments to automatically enable the flag for
        :param custom_attributes: Optional custom attributes for feature flag targeting
        :param environment_name: The environment name (test, beta, prod)
        """
        super().__init__(scope, construct_id)

        if not flag_name or not environment_name:
            raise ValueError('flag_name and environment_name are required')

        self.provider = provider

        # Build custom resource properties
        properties = {'flagName': flag_name, 'autoEnable': environment_name in auto_enable_envs}

        if custom_attributes:
            properties['customAttributes'] = custom_attributes

        # Create the custom resource
        self.custom_resource = CustomResource(
            self,
            'CustomResource',
            resource_type='Custom::FeatureFlag',
            service_token=self.provider.service_token,
            properties=properties,
        )
