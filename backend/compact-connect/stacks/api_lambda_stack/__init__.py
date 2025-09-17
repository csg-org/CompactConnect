from __future__ import annotations

from constructs import Construct

from common_constructs.stack import AppStack
from stacks import persistent_stack as ps
from stacks.provider_users import ProviderUsersStack

from .provider_users import ProviderUsersLambdas


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

        # Provider Users related API lambdas
        self.provider_users_lambdas = ProviderUsersLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            provider_users_stack=provider_users_stack,
        )
