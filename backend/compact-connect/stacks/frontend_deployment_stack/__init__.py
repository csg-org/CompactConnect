from common_constructs.bucket import Bucket
from common_constructs.frontend_app_config_utility import (
    PersistentStackFrontendAppConfigValues,
    UIStackFrontendAppConfigValues,
)
from common_constructs.security_profile import SecurityProfile
from common_constructs.stack import AppStack
from constructs import Construct

from stacks.frontend_deployment_stack.deployment import CompactConnectUIBucketDeployment
from stacks.frontend_deployment_stack.distribution import UIDistribution


class FrontendDeploymentStack(AppStack):
    """
    Stack for managing frontend asset deployments into the UI S3 Bucket.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_context: dict,
        environment_name: str,
        **kwargs,
    ):
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )

        # Load the app configuration if bundling is required
        persistent_stack_frontend_app_config_values = (
            PersistentStackFrontendAppConfigValues.load_persistent_stack_values_from_ssm_parameter(self)
        )
        ui_stack_frontend_app_config_values = UIStackFrontendAppConfigValues.load_ui_stack_values_from_ssm_parameter(
            self
        )

        # If either parameter could not be found, it means that the app_configuration values have not been deployed to
        # SSM we will fail the bucket deployment until the parameters have been put into place, to avoid deploying
        # without the needed values.
        if persistent_stack_frontend_app_config_values is None:
            raise ValueError(
                'Persistent Stack App Configuration not found in SSM. '
                'Make sure Persistent Stack resources have been deployed.'
            )
        if ui_stack_frontend_app_config_values is None:
            raise ValueError(
                'UI Stack App Configuration not found in SSM. Make sure UI Stack resources have been deployed.'
            )

        security_profile = SecurityProfile[environment_context.get('security_profile', 'RECOMMENDED')]


        ui_bucket = Bucket.from_bucket_arn(self, 'UIBucket', ui_stack_frontend_app_config_values.ui_bucket_arn)

        self.assets = CompactConnectUIBucketDeployment(
            self,
            'CompactConnectUIDeployment',
            ui_bucket=ui_bucket,
            environment_context=environment_context,
            ui_app_config_values=persistent_stack_frontend_app_config_values,
        )

        self.distribution = UIDistribution(
            self,
            'UIDistribution',
            ui_bucket=ui_bucket,
            security_profile=security_profile,
            persistent_stack_frontend_app_config_values=persistent_stack_frontend_app_config_values,
        )
