from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import EventBus
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_logs import QueryDefinition, QueryString
from aws_cdk.aws_s3 import BucketEncryption, CorsRule, EventType, HttpMethods
from aws_cdk.aws_s3_notifications import LambdaDestination
from cdk_nag import NagSuppressions
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.bucket import Bucket
from common_constructs.python_function import PythonFunction
from constructs import Construct

import stacks.persistent_stack as ps


class BulkUploadsBucket(Bucket):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            access_logs_bucket: AccessLogsBucket,
            encryption_key: IKey,
            mock_bucket: bool = False,
            event_bus: EventBus,
            **kwargs
    ):
        super().__init__(
            scope, construct_id,
            encryption=BucketEncryption.KMS,
            encryption_key=encryption_key,
            server_access_logs_bucket=access_logs_bucket,
            versioned=False,
            cors=[
                 CorsRule(
                     allowed_methods=[HttpMethods.GET, HttpMethods.POST],
                     allowed_origins=['*'],
                     allowed_headers=['*']
                 )
             ],
            **kwargs
        )
        self.log_groups = []

        if mock_bucket:
            self._add_delete_object_events()
        else:
            self._add_v1_ingest_object_events(event_bus)

        QueryDefinition(
            self, 'RuntimeQuery',
            query_definition_name=f'{construct_id}/Lambdas',
            query_string=QueryString(
                fields=[
                    '@timestamp',
                    '@log',
                    'level',
                    'status',
                    'message',
                    '@message'
                ],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc'
            ),
            log_groups=self.log_groups
        )

        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'HIPAA.Security-S3BucketReplicationEnabled',
                    'reason': 'This bucket houses transitory data only, so replication to a backup bucket is'
                    ' unhelpful.'
                },
                {
                    'id': 'HIPAA.Security-S3BucketVersioningEnabled',
                    'reason': 'This bucket houses transitory data only, so storing of version history is unhelpful.'
                }
            ]
        )

    def _add_delete_object_events(self):
        """
        Delete any objects that get uploaded - for mock api purposes
        """
        stack: ps.PersistentStack = ps.PersistentStack.of(self)

        delete_objects_handler = PythonFunction(
            self, 'DeleteObjectsHandler',
            description='Delete S3 objects handler',
            entry=os.path.join('lambdas', 'delete-objects'),
            index='main.py',
            handler='delete_objects',
            alarm_topic=stack.alarm_topic
        )
        self.grant_delete(delete_objects_handler)
        self.add_event_notification(
            event=EventType.OBJECT_CREATED,
            dest=LambdaDestination(delete_objects_handler)
        )
        self.log_groups.append(delete_objects_handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{delete_objects_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions and resource have wildcards but are still scoped to this bucket and'
                              ' only the actions needed to perform its function'
                }
            ]
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{stack.node.path}/BucketNotificationsHandler050a0587b7544547bf325f094a3db834/'
                 'Role/DefaultPolicy/Resource',
            suppressions=[{
                'id': 'AwsSolutions-IAM5',
                'applies_to': [
                    'Resource::*'
                ],
                'reason': 'The lambda policy is scoped specifically to the PutBucketNotification action, which suits'
                          ' its purpose.'
            }]
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{stack.node.path}/BucketNotificationsHandler050a0587b7544547bf325f094a3db834/'
                 'Role/Resource',
            suppressions=[{
                'id': 'AwsSolutions-IAM4',
                'applies_to': [
                    'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                ],
                'reason': 'The BasicExecutionRole policy is appropriate for this lambda'
            }]
        )

    def _add_v1_ingest_object_events(self, event_bus: EventBus):
        """
        Read any objects that get uploaded and trigger ingest events
        """
        stack: ps.PersistentStack = ps.PersistentStack.of(self)
        parse_objects_handler = PythonFunction(
            self, 'V1ParseObjectsHandler',
            description='Parse s3 objects handler',
            entry=os.path.join('lambdas', 'provider-data-v1'),
            index=os.path.join('handlers', 'bulk_upload.py'),
            handler='parse_bulk_upload_file',
            timeout=Duration.minutes(15),
            alarm_topic=stack.alarm_topic,
            memory_size=1024,
            environment={
                'EVENT_BUS_NAME': event_bus.event_bus_name,
                **stack.common_env_vars
            }
        )
        self.grant_delete(parse_objects_handler)
        self.grant_read(parse_objects_handler)
        event_bus.grant_put_events_to(parse_objects_handler)
        self.log_groups.append(parse_objects_handler.log_group)

        # We should specifically set an alarm for any failures of this handler, since it could otherwise go unnoticed.
        Alarm(
            self, 'V1ParserFailureAlarm',
            metric=parse_objects_handler.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{parse_objects_handler.node.path} failed to process a bulk upload',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING
        ).add_alarm_action(SnsAction(stack.alarm_topic))

        self.add_event_notification(
            event=EventType.OBJECT_CREATED,
            dest=LambdaDestination(parse_objects_handler)
        )
        stack = ps.PersistentStack.of(self)
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{parse_objects_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions and resource have wildcards but are still scoped to this bucket and'
                              ' only the actions needed to perform its function'
                }
            ]
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{stack.node.path}/BucketNotificationsHandler050a0587b7544547bf325f094a3db834/'
                 'Role/DefaultPolicy/Resource',
            suppressions=[{
                'id': 'AwsSolutions-IAM5',
                'applies_to': [
                    'Resource::*'
                ],
                'reason': 'The lambda policy is scoped specifically to the PutBucketNotification action, which suits'
                          ' its purpose.'
            }]
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{stack.node.path}/BucketNotificationsHandler050a0587b7544547bf325f094a3db834/'
                 'Role/Resource',
            suppressions=[{
                'id': 'AwsSolutions-IAM4',
                'applies_to': [
                    'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                ],
                'reason': 'The BasicExecutionRole policy is appropriate for this lambda'
            }]
        )
