from __future__ import annotations

from functools import cached_property

from constructs import Construct

from common_constructs.cc_api import CCApi
from stacks import persistent_stack, search_persistent_stack


class SearchApi(CCApi):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        persistent_stack: persistent_stack.PersistentStack,
        search_persistent_stack: search_persistent_stack.SearchPersistentStack,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            persistent_stack=persistent_stack,
            **kwargs,
        )
        from stacks.search_api_stack.v1_api import V1Api

        self.v1_api = V1Api(
            self.root,
            persistent_stack=persistent_stack,
            search_persistent_stack=search_persistent_stack
        )

    @cached_property
    def staff_users_authorizer(self):
        from aws_cdk.aws_apigateway import CognitoUserPoolsAuthorizer

        return CognitoUserPoolsAuthorizer(
            self, 'StaffUsersPoolAuthorizer', cognito_user_pools=[self._persistent_stack.staff_users]
        )
