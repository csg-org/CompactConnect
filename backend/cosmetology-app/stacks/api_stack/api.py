from __future__ import annotations

from functools import cached_property

from constructs import Construct

from common_constructs.cc_api import CCApi
from stacks import persistent_stack as ps
from stacks import search_persistent_stack as sps
from stacks.api_lambda_stack import ApiLambdaStack


class LicenseApi(CCApi):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        persistent_stack: ps.PersistentStack,
        api_lambda_stack: ApiLambdaStack,
        search_persistent_stack: sps.SearchPersistentStack,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            persistent_stack=persistent_stack,
            **kwargs,
        )
        from stacks.api_stack.v1_api import V1Api

        self._staff_users = persistent_stack.staff_users

        self.v1_api = V1Api(
            self.root,
            persistent_stack=persistent_stack,
            api_lambda_stack=api_lambda_stack,
            search_persistent_stack=search_persistent_stack,
        )

    @cached_property
    def staff_users_authorizer(self):
        from aws_cdk.aws_apigateway import CognitoUserPoolsAuthorizer

        return CognitoUserPoolsAuthorizer(
            self, 'StaffUsersPoolAuthorizer', cognito_user_pools=[self._persistent_stack.staff_users]
        )
