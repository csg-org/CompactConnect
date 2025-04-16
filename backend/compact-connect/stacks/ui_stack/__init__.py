from aws_cdk import RemovalPolicy
from cdk_nag import NagSuppressions
from common_constructs.bucket import Bucket
from common_constructs.frontend_app_config_utility import UIStackFrontendAppConfigUtility
from common_constructs.stack import AppStack
from constructs import Construct

from stacks.persistent_stack import PersistentStack
from stacks.ui_stack.distribution import UIDistribution


class UIStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_context: dict,
        environment_name: str,
        persistent_stack: PersistentStack,
        **kwargs,
    ):
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )

        ui_bucket = Bucket(
            self,
            'UIBucket',
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            server_access_logs_bucket=persistent_stack.access_logs_bucket,
        )
        NagSuppressions.add_resource_suppressions(
            ui_bucket,
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

        ui_app_config = UIStackFrontendAppConfigUtility()
        ui_app_config.set_ui_bucket_arn(ui_bucket.bucket_arn)
        # store the ui bucket arn in ssm parameter store for the frontend deployment stack to use
        ui_app_config.generate_ssm_parameter(self, 'UIAppConfig')
