from __future__ import annotations

from common_constructs.stack import AppStack
from constructs import Construct

from stacks.feature_flag_stack.feature_flag_resource import FeatureFlagResource


class FeatureFlagStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)

        # Feature Flags are deployed through a custom resource
        # one per flag
        self.test_flag = FeatureFlagResource(
            self,
            'ExampleFlag',
            flag_name='example-flag',
            # This causes the flag to automatically be set to enabled for every environment in the list
            auto_enable_envs=['test', 'beta', 'prod'],
            # Note that flags are not updated once set and must be manually updated through the console
            custom_attributes={'compact': ['coun']},
            environment_name=environment_name,
        )
