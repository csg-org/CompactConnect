from __future__ import annotations

import os

from aws_cdk.aws_secretsmanager import Secret
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack

from common_constructs.python_function import PythonFunction
from stacks import persistent_stack as ps


class FeatureFlagsLambdas:
    def __init__(
        self,
        *,
        scope: Stack,
        persistent_stack: ps.PersistentStack,
    ) -> None:
        self.scope = scope
        self.persistent_stack = persistent_stack

        self.stack: Stack = Stack.of(scope)
        lambda_environment = {
            **self.stack.common_env_vars,
        }

        # Get the StatsIg secret for each environment
        environment_name = self.stack.common_env_vars['ENVIRONMENT_NAME']
        self.statsig_secret = Secret.from_secret_name_v2(
            self.scope,
            'StatsigSecret',
            f'compact-connect/env/{environment_name}/statsig/credentials',
        )

        self.check_feature_flag_function = self._create_check_feature_flag_function(lambda_environment)

    def _create_check_feature_flag_function(self, lambda_environment: dict) -> PythonFunction:
        check_feature_flag_function = PythonFunction(
            self.scope,
            'CheckFeatureFlagHandler',
            description='Check feature flag handler',
            lambda_dir='feature-flag',
            index=os.path.join('handlers', 'check_feature_flag.py'),
            handler='check_feature_flag',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )

        # Grant permission to read the StatsIg secret
        self.statsig_secret.grant_read(check_feature_flag_function)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{check_feature_flag_function.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are scoped to the StatsIg secret it needs to access.',
                },
            ],
        )

        return check_feature_flag_function
