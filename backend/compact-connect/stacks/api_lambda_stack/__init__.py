from __future__ import annotations

import json
import os

from aws_cdk.aws_dynamodb import ITable
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_secretsmanager import ISecret, Secret
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from common_constructs.stack import AppStack
from constructs import Construct

from common_constructs.python_function import PythonFunction
from common_constructs.ssm_parameter_utility import SSMParameterUtility
from stacks import persistent_stack as ps
from stacks.provider_users import ProviderUsersStack

from .attestations import AttestationsLambdas
from .bulk_upload_url import BulkUploadUrlLambdas
from .compact_configuration_api import CompactConfigurationApiLambdas
from .credentials import CredentialsLambdas
from .post_licenses import PostLicensesLambdas
from .provider_users import ProviderUsersLambdas
from .public_lookup_api import PublicLookupApiLambdas
from .purchases import PurchasesLambdas
from .staff_users import StaffUsersLambdas


class ApiLambdaStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        environment_context: dict,
        persistent_stack: ps.PersistentStack,
        provider_users_stack: ProviderUsersStack,
        **kwargs,
    ) -> None:
        super().__init__(
            scope,
            construct_id,
            environment_name=environment_name,
            environment_context=environment_context,
            **kwargs,
        )

        data_event_bus = SSMParameterUtility.load_data_event_bus_from_ssm_parameter(self)
        compact_payment_processor_secrets = self._get_compact_payment_processor_secrets()

        self.privilege_history_handler = self._privilege_history_handler(
            data_encryption_key=persistent_stack.shared_encryption_key,
            provider_table=persistent_stack.provider_table,
            alarm_topic=persistent_stack.alarm_topic,
        )

        # Attestation lambdas
        self.attestations_lambdas = AttestationsLambdas(
            scope=self,
            persistent_stack=persistent_stack,
        )

        # Bulk upload url lambdas
        self.bulk_upload_url_lambdas = BulkUploadUrlLambdas(
            scope=self,
            persistent_stack=persistent_stack,
        )

        # Compact configuration lambdas
        self.compact_configuration_lambdas = CompactConfigurationApiLambdas(
            scope=self,
            persistent_stack=persistent_stack,
        )

        # Credentials lambdas
        self.credentials_lambdas = CredentialsLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            compact_payment_processor_secrets=compact_payment_processor_secrets,
        )

        # Post licenses lambdas
        self.post_licenses_lambdas = PostLicensesLambdas(
            scope=self,
            persistent_stack=persistent_stack,
        )

        # Provider Users lambdas
        self.provider_users_lambdas = ProviderUsersLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            provider_users_stack=provider_users_stack,
        )

        # Provider Management lambdas

        # Public lookup lambdas
        self.public_lookup_lambdas = PublicLookupApiLambdas(
            scope=self,
            persistent_stack=persistent_stack,
        )

        # Purchases lambdas
        self.purchases_lambdas = PurchasesLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
            compact_payment_processor_secrets=compact_payment_processor_secrets,
        )

        # Staff user lambdas
        self.staff_users_lambdas = StaffUsersLambdas(
            scope=self,
            persistent_stack=persistent_stack,
        )

    def _get_compact_payment_processor_secrets(self) -> list[ISecret]:
        """
        For each supported compact in the system, return the secret arn for the payment processor credentials.
        The secret arn follows this pattern:
        compact-connect/env/{environment_name}/compact/{compact_abbr}/credentials/payment-processor


        This is used to scope the permissions granted to the lambda to only the secrets it needs to access.
        """
        environment_name = self.common_env_vars['ENVIRONMENT_NAME']
        compacts = json.loads(self.common_env_vars['COMPACTS'])
        return [
            Secret.from_secret_name_v2(
                self,
                f'{compact}Secret',
                f'compact-connect/env/{environment_name}/compact/{compact}/credentials/payment-processor',
            )
            for compact in compacts
        ]

    def _privilege_history_handler(
        self,
        data_encryption_key: IKey,
        provider_table: ITable,
        alarm_topic: ITopic,
    ):
        handler = PythonFunction(
            self,
            'GetPrivilegeHistory',
            description='Get privilege history handler',
            lambda_dir='provider-data-v1',
            environment={
                'PROVIDER_TABLE_NAME': provider_table.table_name,
                **self.common_env_vars,
            },
            index=os.path.join('handlers', 'privilege_history.py'),
            handler='privilege_history_handler',
            alarm_topic=alarm_topic,
        )
        data_encryption_key.grant_decrypt(handler)
        provider_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler
