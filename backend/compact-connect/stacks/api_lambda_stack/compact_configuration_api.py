from __future__ import annotations

import os

from aws_cdk import Duration, Stack
from aws_cdk.aws_dynamodb import ITable
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks import persistent_stack as ps


class CompactConfigurationApiLambdas:
    def __init__(
        self,
        *,
        scope: Construct,
        persistent_stack: ps.PersistentStack,
    ):
        super().__init__()
        stack = Stack.of(scope)

        env_vars = {
            'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
            **stack.common_env_vars,
        }

        self.compact_configuration_api_handler = self._compact_configuration_api_handler(
            scope=scope,
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            compact_configuration_table=persistent_stack.compact_configuration_table,
        )

    def _compact_configuration_api_handler(
        self, scope: Construct, env_vars: dict, data_encryption_key: IKey, compact_configuration_table: ITable
    ):
        stack = Stack.of(scope)
        handler = PythonFunction(
            scope,
            'CompactConfigurationApiFunction',
            index=os.path.join('handlers', 'compact_configuration.py'),
            lambda_dir='compact-configuration',
            handler='compact_configuration_api_handler',
            environment=env_vars,
            timeout=Duration.seconds(30),
        )
        data_encryption_key.grant_decrypt(handler)
        compact_configuration_table.grant_read_write_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler
