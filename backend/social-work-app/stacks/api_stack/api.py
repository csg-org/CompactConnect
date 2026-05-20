from __future__ import annotations

from functools import cached_property

from constructs import Construct

from common_constructs.compact_connect_api import CompactConnectApi
from stacks import persistent_stack as ps
from stacks import search_persistent_stack as sps
from stacks.api_lambda_stack import ApiLambdaStack


class LicenseApi(CompactConnectApi):
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
            alarm_topic=persistent_stack.alarm_topic,
            staff_users_user_pool=persistent_stack.staff_users,
            **kwargs,
        )
        from stacks.api_stack.v1_api import V1Api

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
            self, 'StaffUsersPoolAuthorizer', cognito_user_pools=[self.staff_users]
        )
