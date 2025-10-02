"""
CDK construct for managing StatSig feature flags as custom resources.

This construct creates a CloudFormation custom resource that manages the lifecycle
of StatSig feature flags across different environments.
"""

import os

import jsii
from aws_cdk import CustomResource, Duration, Stack
from aws_cdk.aws_iam import IGrantable, PolicyStatement
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.custom_resources import Provider
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from constructs import Construct


@jsii.implements(IGrantable)
class FeatureFlagResource(Construct):
    """
    Custom resource for managing StatSig feature flags.

    This construct creates a Lambda-backed custom resource that handles
    creation, updates, and deletion of feature flags in StatSig.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        flag_name: str,
        auto_enable_envs: list[str],
        custom_attributes: dict[str, str] | dict[str, list] | None = None,
        environment_name: str,
    ):
        """
        Initialize the FeatureFlagResource construct.

        :param flag_name: Name of the feature flag to manage
        :param auto_enable_envs: List of environments to automatically enable the flag for
        :param custom_attributes: Optional custom attributes for feature flag targeting
        :param environment_name: The environment name (test, beta, prod)
        """
        super().__init__(scope, construct_id)

        if not flag_name:
            raise ValueError('flag_name is required')

        # Lambda function for managing feature flags
        self.manage_function = PythonFunction(
            self,
            'ManageFunction',
            index=os.path.join('handlers', 'manage_feature_flag.py'),
            lambda_dir='feature-flag',
            handler='on_event',
            log_retention=RetentionDays.ONE_MONTH,
            environment={'ENVIRONMENT_NAME': environment_name},
            timeout=Duration.minutes(5),
            memory_size=256,
        )

        # Grant permissions to read secrets
        secret_name = f'compact-connect/env/{environment_name}/statsig/credentials'
        self.manage_function.add_to_role_policy(
            PolicyStatement(
                actions=['secretsmanager:GetSecretValue'],
                resources=[
                    f'arn:aws:secretsmanager:{Stack.of(self).region}:{Stack.of(self).account}:secret:{secret_name}-*'
                ],
            )
        )

        # Create the custom resource provider
        self.provider = Provider(
            self, 'Provider', on_event_handler=self.manage_function, log_retention=RetentionDays.ONE_DAY
        )

        # Add CDK Nag suppressions for the provider framework
        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(self),
            f'{self.provider.node.path}/framework-onEvent/Resource',
            [
                {'id': 'AwsSolutions-L1', 'reason': 'We do not control this runtime'},
                {
                    'id': 'HIPAA.Security-LambdaConcurrency',
                    'reason': 'This function is only run at deploy time, by CloudFormation and has no need for '
                    'concurrency limits.',
                },
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': 'This is a synchronous function run at deploy time. It does not need a DLQ',
                },
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'We may choose to move our lambdas into private VPC subnets in a future enhancement',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(self),
            path=f'{self.manage_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy contain a wildcard specifically to access the feature flag '
                    'client credentials secret and all of its versions.',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(self),
            path=f'{self.provider.node.path}/framework-onEvent/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy contain a wildcard specifically to access the feature flag '
                    'client credentials secret and all of its versions.',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(self),
            path=f'{self.provider.node.path}/framework-onEvent/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'appliesTo': [
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    ],
                    'reason': 'This policy is appropriate for the custom resource lambda',
                },
            ],
        )

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

    @property
    def grant_principal(self):
        """Return the grant principal for IAM permissions"""
        return self.manage_function.grant_principal
