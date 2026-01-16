from aws_cdk import RemovalPolicy
from aws_cdk.aws_kms import Key
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.base_pipeline_stack import DEPLOY_ENVIRONMENT_NAME
from common_constructs.ssm_context import SSMContext
from common_constructs.stack import Stack


class DeploymentResourcesStack(Stack):
    """Stack that manages all shared resources for all pipeline stacks."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        pipeline_context_parameter_name: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name='deploy', **kwargs)

        ssm_context = SSMContext(
            self,
            'PipelineContext',
            pipeline_context_parameter_name,
            f'cdk.context.{DEPLOY_ENVIRONMENT_NAME}-example.json',
        )
        self.parameter = ssm_context.parameter
        self.ssm_context = ssm_context.context

        self.deploy_environment_context = self.ssm_context['environments'][DEPLOY_ENVIRONMENT_NAME]

        self.pipeline_shared_encryption_key = Key(
            self,
            'PipelineSharedEncryptionKey',
            enable_key_rotation=True,
            alias=f'{self.node.path}-shared-encryption-key',
            removal_policy=RemovalPolicy.RETAIN,
        )

        notifications = self.deploy_environment_context.get('notifications', {})
        self.pipeline_alarm_topic = AlarmTopic(
            self,
            'AlarmTopic',
            master_key=self.pipeline_shared_encryption_key,
            email_subscriptions=notifications.get('email', []),
            slack_subscriptions=notifications.get('slack', []),
        )

        self.pipeline_access_logs_bucket = AccessLogsBucket(
            self,
            'AccessLogsBucket',
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{self.pipeline_access_logs_bucket.node.path}/Resource',
            suppressions=[
                {
                    'id': 'HIPAA.Security-S3BucketLoggingEnabled',
                    'reason': 'This is the access logging bucket.',
                },
            ],
        )
