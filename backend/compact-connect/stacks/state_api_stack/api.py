from __future__ import annotations

from functools import cached_property

from aws_cdk.aws_logs import QueryDefinition, QueryString
from constructs import Construct

from common_constructs.cc_api import CCApi
from stacks import persistent_stack as ps
from stacks.state_auth import StateAuthStack


class StateApi(CCApi):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        persistent_stack: ps.PersistentStack,
        state_auth_stack: StateAuthStack,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            persistent_stack=persistent_stack,
            **kwargs,
        )
        from stacks.state_api_stack.v1_api import V1Api

        self._state_auth_stack = state_auth_stack

        # Initialize log groups list for QueryDefinition
        self.log_groups = []

        self.v1_api = V1Api(self.root, persistent_stack=persistent_stack)

        # Create the QueryDefinition after all API modules have been initialized and added their log groups
        self._create_runtime_query_definition()

    @cached_property
    def state_auth_authorizer(self):
        from aws_cdk.aws_apigateway import CognitoUserPoolsAuthorizer

        return CognitoUserPoolsAuthorizer(
            self, 'StateAuthAuthorizer', cognito_user_pools=[self._state_auth_stack.state_auth_users]
        )

    def _create_runtime_query_definition(self):
        """Create the QueryDefinition for runtime logs after all API modules have been initialized."""
        QueryDefinition(
            self,
            'RuntimeQuery',
            query_definition_name=f'{self.node.id}/Lambdas',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'status', 'message', 'method', 'path', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=self.log_groups,
        )
