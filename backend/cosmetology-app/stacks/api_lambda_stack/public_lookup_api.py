from __future__ import annotations

import os

from aws_cdk import Stack
from aws_cdk.aws_dynamodb import ITable
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks import api_lambda_stack as als
from stacks import persistent_stack as ps


class PublicLookupApiLambdas:
    def __init__(
        self,
        *,
        scope: Construct,
        persistent_stack: ps.PersistentStack,
        api_lambda_stack: als.ApiLambdaStack,
    ):
        super().__init__()

        stack = Stack.of(scope)
        lambda_environment = {
            'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': persistent_stack.provider_table.provider_fam_giv_mid_index_name,
            'PROV_DATE_OF_UPDATE_INDEX_NAME': persistent_stack.provider_table.provider_date_of_update_index_name,
            'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
            **stack.common_env_vars,
        }

        self.get_provider_handler = self._get_provider_handler(
            scope=scope,
            env_vars=lambda_environment,
            data_encryption_key=persistent_stack.shared_encryption_key,
            provider_table=persistent_stack.provider_table,
            alarm_topic=persistent_stack.alarm_topic,
        )
        api_lambda_stack.log_groups.append(self.get_provider_handler.log_group)

        self.query_providers_handler = self._query_providers_handler(
            scope=scope,
            env_vars=lambda_environment,
            data_encryption_key=persistent_stack.shared_encryption_key,
            provider_table=persistent_stack.provider_table,
            compact_configuration_table=persistent_stack.compact_configuration_table,
            alarm_topic=persistent_stack.alarm_topic,
        )
        api_lambda_stack.log_groups.append(self.query_providers_handler.log_group)

        # Dummy export to avoid CDK deadly embrace: public query providers now uses
        # SearchPersistentStack.public_handler; this lambda is no longer wired to the API.
        # TODO: remove this export (and the lambda above) after the stack is deployed and the export can be retired  # noqa: FIX002
        stack.export_value(self.query_providers_handler.function_arn)

    def _get_provider_handler(
        self,
        scope: Construct,
        env_vars: dict,
        data_encryption_key: IKey,
        provider_table: ITable,
        alarm_topic: ITopic,
    ) -> PythonFunction:
        stack = Stack.of(scope)

        handler = PythonFunction(
            scope,
            'PublicGetProviderHandler',
            description='Public Get provider handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'public_lookup.py'),
            handler='public_get_provider',
            environment=env_vars,
            alarm_topic=alarm_topic,
        )
        data_encryption_key.grant_decrypt(handler)
        provider_table.grant_read_data(handler)

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

    def _query_providers_handler(
        self,
        scope: Construct,
        env_vars: dict,
        data_encryption_key: IKey,
        provider_table: ITable,
        compact_configuration_table: ITable,
        alarm_topic: ITopic,
    ) -> PythonFunction:
        handler = PythonFunction(
            scope,
            'PublicQueryProvidersHandler',
            description='Public Query providers handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'public_lookup.py'),
            handler='public_query_providers',
            environment=env_vars,
            alarm_topic=alarm_topic,
        )
        data_encryption_key.grant_decrypt(handler)
        provider_table.grant_read_data(handler)
        compact_configuration_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(handler.role),
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'appliesTo': [
                        'Action::kms:GenerateDataKey*',
                        'Action::kms:ReEncrypt*',
                        'Resource::<ProviderTableEC5D0597.Arn>/index/*',
                    ],
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler
