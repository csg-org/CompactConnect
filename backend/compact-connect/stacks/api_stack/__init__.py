from __future__ import annotations

from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps
from stacks.api_stack.cc_api import CCApi


class ApiStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        environment_context: dict,
        persistent_stack: ps.PersistentStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_context=environment_context, **kwargs)

        self.api = CCApi(self, 'LicenseApi', environment_name=environment_name, persistent_stack=persistent_stack)
