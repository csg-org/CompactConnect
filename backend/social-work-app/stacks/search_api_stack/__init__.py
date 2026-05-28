from __future__ import annotations

from common_constructs.security_profile import SecurityProfile
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack, search_persistent_stack

from .api import SearchApi


class SearchApiStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        environment_context: dict,
        persistent_stack: persistent_stack.PersistentStack,
        search_persistent_stack: search_persistent_stack.SearchPersistentStack,
        **kwargs,
    ):
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )

        security_profile = SecurityProfile[environment_context.get('security_profile', 'RECOMMENDED')]

        self.api = SearchApi(
            self,
            'SearchApi',
            environment_name=environment_name,
            security_profile=security_profile,
            persistent_stack=persistent_stack,
            search_persistent_stack=search_persistent_stack,
            domain_name=self.search_api_domain_name,
        )
