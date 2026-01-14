"""
Feature Flag Management Stack

This stack manages feature flags through CloudFormation custom resources.
Feature flags enable/disable functionality dynamically across environments without code deployments.

While we initially create the flag through CDK deployments, updates to the flag configuration are managed through
the respective StatSig account console.

When a flag is no longer used, removing it from this stack should result in cleaning up all the environment based rules
for the flag and deleting it from StatSig once it has been removed from all environments.

NOTE: Flags are only currently supported if the environment has a domain name configured.

Feature Flag Lifecycle:
-----------------------
1. **Creation** (on_create):
   - Creates a new StatSig feature gate if it doesn't exist
   - Adds an environment-specific rule (e.g., '<env name>-rule') to the gate
   - If auto_enable=True: passPercentage=100 (enabled)
   - If auto_enable=False: passPercentage=0 (disabled)

2. **Updates** (on_update):
   - Feature flags are IMMUTABLE once created in an environment
   - Updates are no-ops to prevent overwriting manual console changes

3. **Deletion** (on_delete):
   - Removes the environment-specific rule from the gate
   - If it's the last rule, deletes the entire gate
   - Other environments' rules remain untouched

StatSig Environment Mapping:
-------------------
StatSig has three fixed environment names, so we must map our environments to one of the three environments
- test → development (StatSig tier)
- beta → staging (StatSig tier)
- prod → production (StatSig tier)
- sandbox/other → development (StatSig tier, default)


Checking Flags in Lambda:
-------------------------
There is a common feature flag client python module that can be used to check if a flag is enabled in StatSig

```python
from cc_common.feature_flag_client import is_feature_enabled, FeatureFlagContext

# Simple check
if is_feature_enabled('my-feature-flag-name'):
    # run feature gated code if enabled

# With targeting context
context = FeatureFlagContext(
    user_id='user-123',
    custom_attributes={'compact': 'aslp', 'licenseType': 'slp'}
)
if is_feature_enabled('my-feature-flag-name', context=context):
    # run feature gated code if enabled
```

Custom Attributes:
-----------------
- Values can be strings (converted to lists) or lists
- Used for targeting specific subsets of users/requests
- Examples: compact, jurisdiction, licenseType, etc.
"""

from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_logs import LogGroup, RetentionDays
from aws_cdk.aws_secretsmanager import Secret
from aws_cdk.custom_resources import Provider
from cdk_nag import NagSuppressions
from common_constructs.stack import AppStack
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks.feature_flag_stack.feature_flag_resource import FeatureFlagEnvironmentName, FeatureFlagResource


class FeatureFlagStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)

        self.provider = self._create_common_provider(environment_name)

        # Feature Flags are deployed through custom resources
        # All flags share the same custom resource provider defined above
        self.example_flag = FeatureFlagResource(
            self,
            'ExampleFlag',
            provider=self.provider,  # Shared provider
            flag_name='example-flag',
            # This causes the flag to automatically be set to enabled for every environment in the list
            auto_enable_envs=[
                FeatureFlagEnvironmentName.TEST,
                FeatureFlagEnvironmentName.BETA,
                FeatureFlagEnvironmentName.PROD,
                FeatureFlagEnvironmentName.SANDBOX,
            ],
            # Note that flags are not updated once set and must be manually updated through the console
            custom_attributes={'compact': ['aslp']},
            environment_name=environment_name,
        )

        self.duplicate_ssn_upload_check_flag = FeatureFlagResource(
            self,
            'DuplicateSsnUploadCheckFlag',
            provider=self.provider,  # Shared provider
            flag_name='duplicate-ssn-upload-check-flag',
            # Low risk update, we will automatically enable for every environment
            auto_enable_envs=[
                FeatureFlagEnvironmentName.TEST,
                FeatureFlagEnvironmentName.BETA,
                FeatureFlagEnvironmentName.PROD,
            ],
            environment_name=environment_name,
        )

    def _create_common_provider(self, environment_name: str) -> Provider:
        # Create shared Lambda function for managing all feature flags
        # This function is reused across all FeatureFlagResource instances
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
        self.statsig_secret = Secret.from_secret_name_v2(
            self,
            'StatsigSecret',
            f'compact-connect/env/{environment_name}/statsig/credentials',
        )
        self.statsig_secret.grant_read(self.manage_function)

        # Add CDK Nag suppressions for the Lambda function
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            path=f'{self.manage_function.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy contain a wildcard specifically to access the feature flag '
                    'client credentials secret and all of its versions.',
                },
            ],
        )

        provider_log_group = LogGroup(
            self,
            'ProviderLogGroup',
            retention=RetentionDays.ONE_DAY,
        )
        NagSuppressions.add_resource_suppressions(
            provider_log_group,
            suppressions=[
                {
                    'id': 'HIPAA.Security-CloudWatchLogGroupEncrypted',
                    'reason': 'We do not log sensitive data to CloudWatch, and operational visibility of system'
                    ' logs to operators with credentials for the AWS account is desired. Encryption is not'
                    ' appropriate here.',
                },
            ],
        )

        # Create shared custom resource provider
        # This provider is reused across all FeatureFlagResource instances
        provider = Provider(
            self,
            'Provider',
            on_event_handler=self.manage_function,
            log_group=provider_log_group,
        )

        # Add CDK Nag suppressions for the provider framework
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{provider.node.path}/framework-onEvent/Resource',
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
            self,
            path=f'{provider.node.path}/framework-onEvent/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy contain a wildcard specifically to access the feature flag '
                    'client credentials secret and all of its versions.',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            path=f'{provider.node.path}/framework-onEvent/ServiceRole/Resource',
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

        return provider
