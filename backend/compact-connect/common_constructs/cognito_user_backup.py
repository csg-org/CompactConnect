"""
Common construct for backing up a single Cognito user pool.

This construct creates all the necessary resources for exporting and backing up
a single Cognito user pool, including the Lambda function, S3 bucket, backup plan,
and EventBridge scheduling.
"""

from __future__ import annotations

import os

from aws_cdk import Duration, RemovalPolicy
from aws_cdk.aws_backup import BackupResource
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import Rule, RuleTargetInput, Schedule
from aws_cdk.aws_events_targets import LambdaFunction
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_s3 import BucketEncryption
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from constructs import Construct
from stacks.backup_infrastructure_stack import BackupInfrastructureStack

from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.backup_plan import CCBackupPlan
from common_constructs.bucket import Bucket
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack


class CognitoUserBackup(Construct):
    """
    Common construct for backing up a single Cognito user pool.

    This construct creates:
    - S3 bucket for storing exported user data
    - Lambda function for exporting user data
    - EventBridge rule for daily scheduling
    - Backup plan for cross-account replication
    - CloudWatch alarm for failure monitoring
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        user_pool_id: str,
        access_logs_bucket: AccessLogsBucket,
        encryption_key: IKey,
        removal_policy: RemovalPolicy,
        backup_infrastructure_stack: BackupInfrastructureStack,
        alarm_topic: ITopic,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.user_pool_id = user_pool_id
        self.encryption_key = encryption_key

        # Create the backup bucket for this user pool
        self.backup_bucket = self._create_backup_bucket(
            access_logs_bucket, encryption_key, removal_policy, backup_infrastructure_stack
        )

        # Create the export Lambda function
        self.export_lambda = self._create_export_lambda()

        # Create the EventBridge rule for daily scheduling
        self.backup_rule = self._create_backup_rule()

        # Create failure alarm
        self.failure_alarm = self._create_failure_alarm(alarm_topic)

    def _create_backup_bucket(
        self,
        access_logs_bucket: AccessLogsBucket,
        encryption_key: IKey,
        removal_policy: RemovalPolicy,
        backup_infrastructure_stack: BackupInfrastructureStack,
    ) -> Bucket:
        """Create S3 bucket for storing exported user data."""
        self.bucket = Bucket(
            self,
            'BackupBucket',
            encryption=BucketEncryption.KMS,
            encryption_key=encryption_key,
            server_access_logs_bucket=access_logs_bucket,
            removal_policy=removal_policy,
            versioned=False,  # Versioning is redundant with backup plan
        )

        NagSuppressions.add_resource_suppressions(
            self.bucket,
            suppressions=[
                {
                    'id': 'HIPAA.Security-S3BucketVersioningEnabled',
                    'reason': 'This bucket has recovery points saved by AWS Backup, so versioning is redundant.',
                },
                {
                    'id': 'HIPAA.Security-S3BucketReplicationEnabled',
                    'reason': 'This bucket stores Cognito user exports that are backed up to cross-account vault via '
                    'AWS Backup. Replication is handled by backup infrastructure rather than S3 replication.',
                },
            ],
        )

        # Set up backup plan using the general_data backup category
        self.backup_plan = CCBackupPlan(
            self.bucket,
            'BackupPlan',
            backup_plan_name_prefix=f'{self.bucket.bucket_name}-cognito-backup',
            backup_resources=[BackupResource.from_arn(self.bucket.bucket_arn)],
            backup_vault=backup_infrastructure_stack.local_backup_vault,
            backup_service_role=backup_infrastructure_stack.backup_service_role,
            cross_account_backup_vault=backup_infrastructure_stack.cross_account_backup_vault,
            # We'll force a single backup policy for all Cognito user pools
            # So that we can synchronize the backup timing with the export Lambda timing.
            backup_policy={
                'schedule': {
                    'year': '*',
                    'month': '*',
                    'day': '*',
                    'hour': '6',  # One hour after the export Lambda runs
                    'minute': '0',
                },
                'delete_after_days': 730,
                'cold_storage_after_days': 30,
            },
        )

        return self.bucket

    def _create_export_lambda(self) -> PythonFunction:
        """Create Lambda function for exporting user data."""
        # Get stack to access common environment variables
        stack = Stack.of(self)

        lambda_function = PythonFunction(
            self,
            'ExportLambda',
            description='Export user pool data for backup purposes',
            lambda_dir='cognito-backup',
            index=os.path.join('handlers', 'cognito_backup.py'),
            handler='backup_handler',
            timeout=Duration.minutes(15),  # Allow time for large user pools
            memory_size=512,  # Sufficient memory for processing and S3 uploads
        )

        # Grant the Lambda permissions to access Cognito and S3
        lambda_function.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'cognito-idp:ListUsers',
                    'cognito-idp:DescribeUserPool',
                ],
                resources=[
                    stack.format_arn(
                        partition=stack.partition,
                        service='cognito-idp',
                        region=stack.region,
                        account=stack.account,
                        resource='userpool',
                        resource_name=self.user_pool_id,
                    ),
                ],
            )
        )

        # Grant S3 permissions
        self.backup_bucket.grant_write(lambda_function)
        self.encryption_key.grant_encrypt_decrypt(lambda_function)

        # Add CDK NAG suppressions for the Lambda IAM permissions
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{lambda_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'Lambda requires read access to specific Cognito user pool and write access to '
                    'the backup S3 bucket. Permissions are scoped to specific resources where possible.',
                },
            ],
        )

        return lambda_function

    def _create_backup_rule(self) -> Rule:
        """Create EventBridge rule for daily execution."""
        # Schedule at 2 AM UTC to avoid conflicts with other backup operations
        # Pass the required parameters as part of the event
        return Rule(
            self,
            'DailyExportRule',
            description='Daily schedule for user pool backup export',
            schedule=Schedule.cron(week_day='*', year='*', month='*', hour='5', minute='0'),
            targets=[
                LambdaFunction(
                    self.export_lambda,
                    event=RuleTargetInput.from_object(
                        {
                            'user_pool_id': self.user_pool_id,
                            'backup_bucket_name': self.backup_bucket.bucket_name,
                        }
                    ),
                )
            ],
        )

    def _create_failure_alarm(self, alarm_topic: ITopic) -> Alarm:
        """Create CloudWatch alarm for backup failures."""
        alarm = Alarm(
            self,
            'BackupFailureAlarm',
            metric=self.export_lambda.metric_errors(),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description='User pool backup export Lambda has failed. User data backup may be incomplete.',
        )
        alarm.add_alarm_action(SnsAction(alarm_topic))

        return alarm
