from __future__ import annotations

from common_constructs.security_profile import SecurityProfile
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps
from stacks.state_auth import StateAuthStack

from .api import StateApi


class StateApiStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        environment_context: dict,
        persistent_stack: ps.PersistentStack,
        state_auth_stack: StateAuthStack,
        **kwargs,
    ):
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )

        security_profile = SecurityProfile[environment_context.get('security_profile', 'RECOMMENDED')]

        self.api = StateApi(
            self,
            'StateApi',
            environment_name=environment_name,
            security_profile=security_profile,
            persistent_stack=persistent_stack,
            state_auth_stack=state_auth_stack,
            domain_name=self.state_api_domain_name,
        )
