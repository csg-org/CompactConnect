from __future__ import annotations

from common_constructs.cc_api import CCApi
from common_constructs.security_profile import SecurityProfile
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps
from stacks.provider_users import ProviderUsersStack

from .v1_api import V1Api


class _StateApi(CCApi):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        persistent_stack: ps.PersistentStack,
        provider_users_stack: ProviderUsersStack,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            persistent_stack=persistent_stack,
            provider_users_stack=provider_users_stack,
            **kwargs,
        )
        self.v1_api = V1Api(self.root, persistent_stack=persistent_stack)


class StateApiStack(AppStack):
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
    ):
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )

        security_profile = SecurityProfile[environment_context.get('security_profile', 'RECOMMENDED')]

        self.api = _StateApi(
            self,
            'StateApi',
            environment_name=environment_name,
            security_profile=security_profile,
            persistent_stack=persistent_stack,
            provider_users_stack=provider_users_stack,
            domain_name=self.state_api_domain_name,
        )
