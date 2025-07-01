from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_backup import BackupResource
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_logs import QueryDefinition, QueryString
from aws_cdk.aws_s3 import BucketEncryption, CorsRule, EventType, HttpMethods
from aws_cdk.aws_s3_notifications import LambdaDestination
from cdk_nag import NagSuppressions
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.backup_plan import CCBackupPlan
from common_constructs.bucket import Bucket
from common_constructs.python_function import PythonFunction
from constructs import Construct

import stacks.persistent_stack as ps
from stacks.backup_infrastructure_stack import BackupInfrastructureStack


class ProviderUsersBucket(Bucket):
    """
    S3 bucket to house provider documents such as military affiliation records.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        access_logs_bucket: AccessLogsBucket,
        encryption_key: IKey,
        provider_table: Table,
        backup_infrastructure_stack: BackupInfrastructureStack,
        environment_context: dict,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            encryption=BucketEncryption.KMS,
            encryption_key=encryption_key,
            server_access_logs_bucket=access_logs_bucket,
            versioned=True,
            cors=[
                CorsRule(
                    allowed_methods=[HttpMethods.GET, HttpMethods.POST],
                    allowed_origins=['*'],
                    allowed_headers=['*'],
                ),
            ],
            **kwargs,
        )
        self.log_groups = []

        self._add_v1_object_events(provider_table, encryption_key)

        self.backup_plan = CCBackupPlan(
            self,
            'ProviderUsersBucketBackup',
            backup_plan_name_prefix=self.bucket_name,
            backup_resources=[BackupResource.from_arn(self.bucket_arn)],
            backup_vault=backup_infrastructure_stack.local_backup_vault,
            backup_service_role=backup_infrastructure_stack.backup_service_role,
            cross_account_backup_vault=backup_infrastructure_stack.cross_account_backup_vault,
            backup_policy=environment_context['backup_policies']['general_data'],
        )

        QueryDefinition(
            self,
            'RuntimeQuery',
            query_definition_name=f'{construct_id}/Lambdas',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'status', 'message', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=self.log_groups,
        )

        NagSuppressions.add_resource_suppressions(
            self,
            [
                {
                    'id': 'HIPAA.Security-S3BucketReplicationEnabled',
                    'reason': (
                        'This bucket is protected by AWS Backup with cross-account replication for disaster recovery.'
                    ),
                },
            ],
        )

    def _add_v1_object_events(self, provider_table: Table, encryption_key: IKey):
        """Read any objects that get uploaded and trigger update events"""
        stack: ps.PersistentStack = ps.PersistentStack.of(self)
        self.process_events_handler = PythonFunction(
            self,
            'V1ProcessProviderS3EventsHandler',
            description='Process updates to provider s3 objects handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'provider_s3_events.py'),
            handler='process_provider_s3_events',
            # we currently don't expect update events to take more than a minute
            # though this may need to be adjusted in the future
            timeout=Duration.minutes(1),
            alarm_topic=stack.alarm_topic,
            memory_size=1024,
            environment={'PROVIDER_TABLE_NAME': provider_table.table_name, **stack.common_env_vars},
        )
        self.grant_read(self.process_events_handler)
        encryption_key.grant_encrypt_decrypt(self.process_events_handler)
        provider_table.grant_read_write_data(self.process_events_handler)
        self.log_groups.append(self.process_events_handler.log_group)

        # We should specifically set an alarm for any failures of this handler, since it could otherwise go unnoticed.
        Alarm(
            self,
            'V1ProcessProviderS3EventsFailureAlarm',
            metric=self.process_events_handler.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{self.process_events_handler.node.path} failed to process an update event',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(stack.alarm_topic))

        self.add_event_notification(event=EventType.OBJECT_CREATED, dest=LambdaDestination(self.process_events_handler))
        stack = ps.PersistentStack.of(self)
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{self.process_events_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions and resource have wildcards but are still scoped to this bucket and'
                    'the table as needed to perform its function',
                },
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{stack.node.path}/BucketNotificationsHandler050a0587b7544547bf325f094a3db834/'
            'Role/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'appliesTo': ['Resource::*'],
                    'reason': """
                    The lambda policy is scoped specifically to the PutBucketNotification action, which
                    suits its purpose.
                    """,
                },
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{stack.node.path}/BucketNotificationsHandler050a0587b7544547bf325f094a3db834/Role/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'appliesTo': [
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
                    ],
                    'reason': 'The BasicExecutionRole policy is appropriate for this lambda',
                },
            ],
        )
