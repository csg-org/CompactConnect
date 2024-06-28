import os

from aws_cdk import Stack
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_s3 import BucketEncryption, EventType, CorsRule, HttpMethods
from aws_cdk.aws_s3_notifications import LambdaDestination
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.bucket import Bucket
from common_constructs.python_function import PythonFunction


class BulkUploadsBucket(Bucket):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            access_logs_bucket: AccessLogsBucket,
            encryption_key: IKey,
            mock_bucket: bool = False,
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

        if mock_bucket:
            self._add_delete_object_events()

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
        # Delete any objects that get uploaded - for mock api purposes
        """
        delete_objects_handler = PythonFunction(
            self, 'DeleteObjectsHandler',
            entry=os.path.join('lambdas', 'delete-objects'),
            index='main.py',
            handler='delete_objects'
        )
        self.grant_delete(delete_objects_handler)
        self.add_event_notification(
            event=EventType.OBJECT_CREATED,
            dest=LambdaDestination(delete_objects_handler)
        )
        stack = Stack.of(self)
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
