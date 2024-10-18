from __future__ import annotations

from constructs import Construct

from common_constructs.security_profile import SecurityProfile
from common_constructs.stack import AppStack
from stacks.api_stack.cc_api import CCApi
from stacks import persistent_stack as ps


class ApiStack(AppStack):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            environment_name: str,
            environment_context: dict,
            persistent_stack: ps.PersistentStack,
            **kwargs
    ):
        super().__init__(scope, construct_id, environment_context=environment_context, **kwargs)

        security_profile = SecurityProfile[environment_context.get('security_profile', 'RECOMMENDED')]

        self.api = CCApi(
            self, 'LicenseApi',
            environment_name=environment_name,
            security_profile=security_profile,
            persistent_stack=persistent_stack
        )
