from __future__ import annotations

import os

from aws_cdk.aws_secretsmanager import Secret
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

from stacks import persistent_stack as ps
from stacks.provider_users import ProviderUsersStack


class ProviderUsersLambdas:
    def __init__(
        self,
        *,
        scope: Stack,
        persistent_stack: ps.PersistentStack,
        provider_users_stack: ProviderUsersStack,
    ) -> None:
        self.scope = scope
        self.persistent_stack = persistent_stack
        self.provider_users_stack = provider_users_stack

        self.stack: Stack = Stack.of(scope)
        lambda_environment = {
            'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': 'providerFamGivMid',
            'PROV_DATE_OF_UPDATE_INDEX_NAME': 'providerDateOfUpdate',
            'PROVIDER_USER_BUCKET_NAME': persistent_stack.provider_users_bucket.bucket_name,
            'LICENSE_GSI_NAME': persistent_stack.provider_table.license_gsi_name,
            'PROVIDER_USER_POOL_ID': provider_users_stack.provider_users.user_pool_id,
            'RATE_LIMITING_TABLE_NAME': persistent_stack.rate_limiting_table.table_name,
            'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
            'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': persistent_stack.email_notification_service_lambda.function_name,
            **self.stack.common_env_vars,
        }

        # Get the recaptcha secret
        environment_name = self.stack.common_env_vars['ENVIRONMENT_NAME']
        self.recaptcha_secret = Secret.from_secret_name_v2(
            self.scope,
            'RecaptchaSecret',
            f'compact-connect/env/{environment_name}/recaptcha/token',
        )

        self.account_recovery_initiate_function = self._create_account_recovery_initiate_function(lambda_environment)
        self.account_recovery_verify_function = self._create_account_recovery_verify_function(lambda_environment)

    def _create_account_recovery_initiate_function(self, lambda_environment: dict) -> PythonFunction:
        # Add client id only for initiate function
        env = {
            **lambda_environment,
            'PROVIDER_USER_POOL_CLIENT_ID': self.provider_users_stack.provider_users.ui_client.user_pool_client_id,
        }

        initiate_account_recovery = PythonFunction(
            self.scope,
            'ProviderUsersAccountRecoveryInitiate',
            description='Provider users account recovery initiate handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'account_recovery.py'),
            handler='initiate_recovery',
            environment=env,
            alarm_topic=self.persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        self.persistent_stack.provider_table.grant_read_write_data(initiate_account_recovery)
        self.persistent_stack.rate_limiting_table.grant_read_write_data(initiate_account_recovery)
        self.persistent_stack.compact_configuration_table.grant_read_data(initiate_account_recovery)
        self.persistent_stack.email_notification_service_lambda.grant_invoke(initiate_account_recovery)
        self.provider_users_stack.provider_users.grant(initiate_account_recovery, 'cognito-idp:AdminInitiateAuth')
        self.recaptcha_secret.grant_read(initiate_account_recovery)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{initiate_account_recovery.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are scoped to the tables, user pool, '
                    'and recaptcha secret it needs to access.',
                },
            ],
        )

        return initiate_account_recovery

    def _create_account_recovery_verify_function(self, lambda_environment: dict) -> PythonFunction:
        verify_account_recovery_function = PythonFunction(
            self.scope,
            'ProviderUsersAccountRecoveryVerify',
            description='Provider users account recovery verify handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'account_recovery.py'),
            handler='verify_recovery',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        self.persistent_stack.provider_table.grant_read_write_data(verify_account_recovery_function)
        self.persistent_stack.rate_limiting_table.grant_read_write_data(verify_account_recovery_function)
        self.provider_users_stack.provider_users.grant(verify_account_recovery_function, 'cognito-idp:AdminDeleteUser')
        self.provider_users_stack.provider_users.grant(verify_account_recovery_function, 'cognito-idp:AdminCreateUser')
        self.recaptcha_secret.grant_read(verify_account_recovery_function)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{verify_account_recovery_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are scoped to the tables, user pool, '
                    'and recaptcha secret it needs to access.',
                },
            ],
        )

        return verify_account_recovery_function
