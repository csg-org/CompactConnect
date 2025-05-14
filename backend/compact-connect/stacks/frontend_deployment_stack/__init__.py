from aws_cdk import RemovalPolicy
from cdk_nag import NagSuppressions
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.bucket import Bucket
from common_constructs.frontend_app_config_utility import (
    PersistentStackFrontendAppConfigValues,
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

        # If we delete this stack, retain the resource (orphan but prevent data loss) or destroy it (clean up)?
        removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY

        # Load the app configuration if bundling is required
        persistent_stack_frontend_app_config_values = (
            PersistentStackFrontendAppConfigValues.load_persistent_stack_values_from_ssm_parameter(self)
        )

        # If this parameter could not be found, it means that the app_configuration values have not been deployed to
        # SSM we will fail the bucket deployment until the parameters have been put into place, to avoid deploying
        # without the needed values.
        if persistent_stack_frontend_app_config_values is None:
            raise ValueError(
                'Persistent Stack App Configuration not found in SSM. '
                'Make sure Persistent Stack resources have been deployed.'
            )

        security_profile = SecurityProfile[environment_context.get('security_profile', 'RECOMMENDED')]

        self.frontend_access_logs_bucket = AccessLogsBucket(
            self,
            'UIAccessLogsBucket',
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY,
        )

        self.ui_bucket = Bucket(
            self,
            'UIBucket',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            server_access_logs_bucket=self.frontend_access_logs_bucket,
        )
        NagSuppressions.add_resource_suppressions(
            self.ui_bucket,
            suppressions=[
                {
                    'id': 'HIPAA.Security-S3BucketReplicationEnabled',
                    'reason': 'This bucket contains built files that are replaced each deploy of the UI. We have no'
                    ' desire for the resilience of bucket replication for this data.',
                },
                {
                    'id': 'HIPAA.Security-S3DefaultEncryptionKMS',
                    'reason': 'The data in this bucket is public web app static files. Default S3 encryption is'
                    ' more than enough for protecting this data.',
                },
                {
                    'id': 'HIPAA.Security-S3BucketVersioningEnabled',
                    'reason': 'This bucket contains built files that are replaced each deploy. We have no '
                    'desire for the resilience of versioning',
                },
            ],
        )

        self.assets = CompactConnectUIBucketDeployment(
            self,
            'CompactConnectUIDeployment',
            ui_bucket=self.ui_bucket,
            environment_context=environment_context,
            ui_app_config_values=persistent_stack_frontend_app_config_values,
        )

        self.distribution = UIDistribution(
            self,
            'UIDistribution',
            ui_bucket=self.ui_bucket,
            security_profile=security_profile,
            access_logs_bucket=self.frontend_access_logs_bucket,
            persistent_stack_frontend_app_config_values=persistent_stack_frontend_app_config_values,
        )
