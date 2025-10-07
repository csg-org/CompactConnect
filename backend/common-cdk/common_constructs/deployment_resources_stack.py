import json

from aws_cdk import RemovalPolicy
from aws_cdk.aws_kms import Key
from aws_cdk.aws_ssm import StringParameter
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.base_pipeline_stack import DEPLOY_ENVIRONMENT_NAME, CCPipelineType
from common_constructs.stack import Stack


class DeploymentResourcesStack(Stack):
    """Stack that manages all shared resources for all pipeline stacks."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        pipeline_type: CCPipelineType,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name='deploy', **kwargs)

        if pipeline_type == CCPipelineType.BACKEND:
            pipeline_context_parameter_name = f'{DEPLOY_ENVIRONMENT_NAME}-compact-connect-context'
        else:
            pipeline_context_parameter_name = f'{DEPLOY_ENVIRONMENT_NAME}-ui-compact-connect-context'

        # Fetch ssm_context if not provided locally
        self.parameter = StringParameter.from_string_parameter_name(
            self,
            'PipelineContext',
            string_parameter_name=pipeline_context_parameter_name,
        )
        value = StringParameter.value_from_lookup(self, self.parameter.parameter_name)
        # When CDK runs for the first time, it synthesizes fully without actually retrieving the SSM Parameter
        # value. It, instead, populates parameters and other look-ups with dummy values, synthesizes, collects all
        # the look-ups together, populates them for real, then re-synthesizes with real values.
        # To accommodate this pattern, we have to replace this dummy value with one that will actually
        # let CDK complete its first round of synthesis, so that it can get to its second, real, synthesis.
        if value != f'dummy-value-for-{pipeline_context_parameter_name}':
            self.ssm_context = json.loads(value)
        else:
            with open(f'cdk.context.{DEPLOY_ENVIRONMENT_NAME}-example.json') as f:
                self.ssm_context = json.load(f)['ssm_context']

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
