from __future__ import annotations

import json
from functools import cached_property

from aws_cdk import ArnFormat
from common_constructs.stack import Stack
from constructs import Construct

from common_constructs.cc_api import CCApi
from stacks import persistent_stack as ps
from stacks.api_lambda_stack import ApiLambdaStack
from stacks.provider_users import ProviderUsersStack


class LicenseApi(CCApi):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        persistent_stack: ps.PersistentStack,
        provider_users_stack: ProviderUsersStack,
        api_lambda_stack: ApiLambdaStack,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            persistent_stack=persistent_stack,
            **kwargs,
        )
        from stacks.api_stack.v1_api import V1Api

        self._provider_users_stack = provider_users_stack
        self._staff_users = persistent_stack.staff_users

        self.v1_api = V1Api(
            self.root,
            persistent_stack=persistent_stack,
            api_lambda_stack=api_lambda_stack,
        )

        # Create the QueryDefinition after all API modules have been initialized and added their log groups
        self.create_runtime_query_definition()

    @cached_property
    def provider_users_authorizer(self):
        from aws_cdk.aws_apigateway import CognitoUserPoolsAuthorizer

        return CognitoUserPoolsAuthorizer(
            self, 'ProviderUsersPoolAuthorizer', cognito_user_pools=[self._provider_users_stack.provider_users]
        )

    @cached_property
    def staff_users_authorizer(self):
        from aws_cdk.aws_apigateway import CognitoUserPoolsAuthorizer

        return CognitoUserPoolsAuthorizer(
            self, 'StaffUsersPoolAuthorizer', cognito_user_pools=[self._persistent_stack.staff_users]
        )

    def get_secrets_manager_compact_payment_processor_arns(self):
        """
        For each supported compact in the system, return the secret arn for the payment processor credentials.
        The secret arn follows this pattern:
        compact-connect/env/{environment_name}/compact/{compact_abbr}/credentials/payment-processor

        This is used to scope the permissions granted to the lambda to only the secrets it needs to access.
        """
        stack = Stack.of(self)
        environment_name = stack.common_env_vars['ENVIRONMENT_NAME']
        compacts = json.loads(stack.common_env_vars['COMPACTS'])
        return [
            stack.format_arn(
                service='secretsmanager',
                arn_format=ArnFormat.COLON_RESOURCE_NAME,
                resource='secret',
                resource_name=(
                    # add wildcard characters to account for 6-character
                    # random version suffix appended to secret name by secrets manager
                    f'compact-connect/env/{environment_name}/compact/{compact}/credentials/payment-processor-??????'
                ),
            )
            for compact in compacts
        ]
