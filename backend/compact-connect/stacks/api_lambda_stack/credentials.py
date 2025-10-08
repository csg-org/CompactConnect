from __future__ import annotations

import os

from aws_cdk import Stack
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_secretsmanager import ISecret
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks import persistent_stack as ps


class CredentialsLambdas:
    def __init__(
        self,
        *,
        scope: Construct,
        compact_payment_processor_secrets: list[ISecret],
        persistent_stack: ps.PersistentStack,
    ):
        super().__init__()
        stack = Stack.of(scope)

        env_vars = {
            **stack.common_env_vars,
            'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
        }

        self.credentials_handler = self._credentials_handler(
            scope=scope,
            env_vars=env_vars,
            compact_payment_processor_secrets=compact_payment_processor_secrets,
            alarm_topic=persistent_stack.alarm_topic,
        )

    def _credentials_handler(
        self, scope: Construct, env_vars: dict, compact_payment_processor_secrets: list[ISecret], alarm_topic: ITopic
    ):
        stack = Stack.of(scope)
        handler = PythonFunction(
            scope,
            'PostCredentialsPaymentProcessorHandler',
            description='Post credentials payment processor handler',
            runtime=Runtime.PYTHON_3_12,
            lambda_dir='purchases',
            index=os.path.join('handlers', 'credentials.py'),
            handler='post_payment_processor_credentials',
            environment=env_vars,
            alarm_topic=alarm_topic,
            # required as this lambda is bundled with the authorize.net SDK which is large
            memory_size=256,
        )
        NagSuppressions.add_resource_suppressions(
            handler,
            suppressions=[
                {
                    'id': 'AwsSolutions-L1',
                    'reason': 'Our Authorize.Net dependency is not yet compatible with Python 3.13',
                },
            ],
        )

        # grant handler access to post secrets for supported compacts
        # compact-connect/env/{environment_name}/compact/{compact_abbr}/credentials/payment-processor
        for secret in compact_payment_processor_secrets:
            secret.grant_read(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler
