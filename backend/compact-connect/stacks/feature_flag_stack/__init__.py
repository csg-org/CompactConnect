from __future__ import annotations

from common_constructs.stack import AppStack
from constructs import Construct
from feature_flag_stack.feature_flag_resource import FeatureFlagResource


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
            custom_attributes={'hello': 'world'},
            environment_name=environment_name,
        )
