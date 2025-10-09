from __future__ import annotations

from common_constructs.stack import AppStack
from constructs import Construct

from common_constructs.ssm_parameter_utility import SSMParameterUtility
from stacks import persistent_stack as ps
from stacks.provider_users import ProviderUsersStack

from .feature_flags import FeatureFlagsLambdas
from .provider_management import ProviderManagementLambdas
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

        data_event_bus = SSMParameterUtility.load_data_event_bus_from_ssm_parameter(self)

        # we only pass the API_BASE_URL env var if the API_DOMAIN_NAME is set
        # this is because the API_BASE_URL is used by the feature flag client to call the flag check endpoint
        if persistent_stack.api_domain_name:
            self.common_env_vars.update({'API_BASE_URL': f'https://{persistent_stack.api_domain_name}'})

        # Feature Flags related API lambdas
        self.feature_flags_lambdas = FeatureFlagsLambdas(
            scope=self,
            persistent_stack=persistent_stack,
        )

        # Provider Users related API lambdas
        self.provider_users_lambdas = ProviderUsersLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            provider_users_stack=provider_users_stack,
        )

        # Provider Management related API lambdas
        self.provider_management_lambdas = ProviderManagementLambdas(
            scope=self,
            persistent_stack=persistent_stack,
            data_event_bus=data_event_bus,
        )
