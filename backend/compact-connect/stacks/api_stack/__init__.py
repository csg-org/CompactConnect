from __future__ import annotations
from constructs import Construct

from common_constructs.stack import Stack
from stacks.api_stack.license_api import LicenseApi
from stacks import persistent_stack as ps


class ApiStack(Stack):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            environment_name: str,
            persistent_stack: ps.PersistentStack,
            **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)
        self.license_api = LicenseApi(
            self, 'LicenseApi',
            environment_name=environment_name,
            persistent_stack=persistent_stack
        )
