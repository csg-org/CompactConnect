"""
Test suite for the CognitoUserBackup common construct.

This module tests the CognitoUserBackup construct to ensure it creates all necessary
resources with proper configuration, including the S3 bucket, Lambda function,
EventBridge rule, CloudWatch alarm, and backup plan.
"""

from unittest import TestCase

from aws_cdk import App, RemovalPolicy, Stack
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_backup import CfnBackupPlan, CfnBackupSelection
from aws_cdk.aws_cloudwatch import CfnAlarm
from aws_cdk.aws_events import CfnRule
from aws_cdk.aws_iam import CfnPolicy
from aws_cdk.aws_kms import Key
from aws_cdk.aws_lambda import CfnFunction
from aws_cdk.aws_s3 import CfnBucket
from aws_cdk.aws_sns import Topic
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.cognito_user_backup import CognitoUserBackup
from stacks.backup_infrastructure_stack import BackupInfrastructureStack


class TestCognitoUserBackup(TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test infrastructure."""
        cls.app = App()
        cls.stack = Stack(cls.app, 'TestStack')

        # Create required dependencies
        cls.encryption_key = Key(cls.stack, 'TestKey')
        cls.alarm_topic = Topic(cls.stack, 'AlarmTopic', master_key=cls.encryption_key)
        cls.access_logs_bucket = AccessLogsBucket(cls.stack, 'AccessLogsBucket', removal_policy=RemovalPolicy.DESTROY)

        # Mock backup infrastructure components
        cls.mock_backup_config = {
            'backup_account_id': '123456789012',
            'backup_region': 'us-east-1',
            'general_vault_name': 'test-general-vault',
            'ssn_vault_name': 'test-ssn-vault',
        }

        # Create backup infrastructure stack for dependencies
        cls.backup_infrastructure_stack = BackupInfrastructureStack(
            cls.stack,
            'BackupInfrastructure',
            environment_name='test',
            backup_config=cls.mock_backup_config,
            alarm_topic=cls.alarm_topic,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Create the construct under test
        cls.cognito_backup = CognitoUserBackup(
            cls.stack,
            'TestCognitoBackup',
            user_pool_id='us-east-1_TestPool123',
            access_logs_bucket=cls.access_logs_bucket,
            encryption_key=cls.encryption_key,
            removal_policy=RemovalPolicy.DESTROY,
            backup_infrastructure_stack=cls.backup_infrastructure_stack,
            alarm_topic=cls.alarm_topic,
        )

        cls.template = Template.from_stack(cls.stack)

    def test_creates_s3_backup_bucket(self):
        """Test that the S3 backup bucket is created with proper configuration."""
        # Should create an S3 bucket with KMS encryption
        self.template.has_resource_properties(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            {
                'BucketEncryption': {
                    'ServerSideEncryptionConfiguration': [
                        {
                            'ServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'aws:kms',
                                'KMSMasterKeyID': {
                                    'Fn::GetAtt': [
                                        self.stack.get_logical_id(self.encryption_key.node.default_child),
                                        'Arn',
                                    ]
                                },
                            }
                        }
                    ]
                },
                'LoggingConfiguration': {
                    'DestinationBucketName': {
                        'Ref': self.stack.get_logical_id(self.access_logs_bucket.node.default_child)
                    }
                },
                'PublicAccessBlockConfiguration': {
                    'BlockPublicAcls': True,
                    'BlockPublicPolicy': True,
                    'IgnorePublicAcls': True,
                    'RestrictPublicBuckets': True,
                },
            },
        )

    def test_creates_lambda_function(self):
        """Test that the Lambda function is created with proper configuration."""
        # Find the Lambda function
        lambda_functions = self.template.find_resources(
            CfnFunction.CFN_RESOURCE_TYPE_NAME,
            {
                'Properties': {
                    'Handler': 'handlers.cognito_backup.backup_handler',
                    'Description': 'Export user pool data for backup purposes',
                }
            },
        )
        self.assertEqual(len(lambda_functions), 1, 'Should have exactly one Cognito backup Lambda function')

        lambda_logical_id = list(lambda_functions.keys())[0]
        lambda_props = lambda_functions[lambda_logical_id]['Properties']

        # Verify function configuration
        self.assertEqual(lambda_props['Runtime'], 'python3.12')
        self.assertEqual(lambda_props['Timeout'], 900)  # 15 minutes
        self.assertEqual(lambda_props['MemorySize'], 512)

    def test_creates_iam_permissions_for_lambda(self):
        """Test that the Lambda function has proper IAM permissions."""
        # Should have policies for Cognito access
        self.template.has_resource(
            CfnPolicy.CFN_RESOURCE_TYPE_NAME,
            {
                'Properties': {
                    'PolicyDocument': {
                        'Statement': Match.array_with(
                            [
                                Match.object_like(
                                    {
                                        'Effect': 'Allow',
                                        'Action': ['cognito-idp:ListUsers', 'cognito-idp:DescribeUserPool'],
                                        'Resource': {
                                            'Fn::Join': [
                                                '',
                                                [
                                                    'arn:',
                                                    {'Ref': 'AWS::Partition'},
                                                    ':cognito-idp:',
                                                    {'Ref': 'AWS::Region'},
                                                    ':',
                                                    {'Ref': 'AWS::AccountId'},
                                                    ':userpool/us-east-1_TestPool123',
                                                ],
                                            ]
                                        },
                                    }
                                )
                            ]
                        )
                    }
                }
            },
        )

        # Should have policies for S3 access
        self.template.has_resource(
            CfnPolicy.CFN_RESOURCE_TYPE_NAME,
            {
                'Properties': {
                    'PolicyDocument': {
                        'Statement': Match.array_with(
                            [
                                Match.object_like(
                                    {
                                        'Effect': 'Allow',
                                        'Action': Match.array_with([Match.string_like_regexp(r's3:.*')]),
                                        'Resource': Match.any_value(),
                                    }
                                ),
                            ]
                        )
                    }
                }
            },
        )

    def test_creates_eventbridge_rule(self):
        """Test that the EventBridge rule is created for daily scheduling."""
        backup_bucket_logical_id = self.stack.get_logical_id(self.cognito_backup.backup_bucket.node.default_child)

        # Find EventBridge rules
        self.template.has_resource(
            CfnRule.CFN_RESOURCE_TYPE_NAME,
            {
                'Properties': {
                    'Description': 'Daily schedule for user pool backup export',
                    'ScheduleExpression': 'cron(0 5 ? * * *)',  # 5 AM UTC daily
                    'State': 'ENABLED',
                    'Targets': [
                        Match.object_like(
                            {
                                'Arn': Match.any_value(),
                                'Input': {
                                    'Fn::Join': [
                                        '',
                                        [
                                            '{"user_pool_id":"us-east-1_TestPool123","backup_bucket_name":"',
                                            {'Ref': backup_bucket_logical_id},
                                            '"}',
                                        ],
                                    ]
                                },
                            }
                        )
                    ],
                }
            },
        )

    def test_creates_cloudwatch_alarm(self):
        """Test that the CloudWatch alarm is created with proper configuration."""
        alarm_topic_logical_id = self.stack.get_logical_id(self.alarm_topic.node.default_child)

        # Find CloudWatch alarms
        self.template.has_resource(
            CfnAlarm.CFN_RESOURCE_TYPE_NAME,
            {
                'Properties': {
                    'AlarmDescription': (
                        'User pool backup export Lambda has failed. User data backup may be incomplete.'
                    ),
                    'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                    'Threshold': 1,
                    'EvaluationPeriods': 1,
                    'TreatMissingData': 'notBreaching',
                    'AlarmActions': [{'Ref': alarm_topic_logical_id}],
                    'Namespace': 'AWS/Lambda',
                    'MetricName': 'Errors',
                }
            },
        )

    def test_creates_backup_plan(self):
        """Test that the backup plan is created for the bucket."""
        backup_bucket_logical_id = self.stack.get_logical_id(self.cognito_backup.backup_bucket.node.default_child)

        # Should create a backup plan
        self.template.has_resource(
            CfnBackupPlan.CFN_RESOURCE_TYPE_NAME,
            {
                'Properties': {
                    'BackupPlan': {
                        'BackupPlanName': {
                            'Fn::Join': [
                                '',
                                [
                                    {'Ref': backup_bucket_logical_id},
                                    '-cognito-backup-BackupPlan',
                                ],
                            ]
                        }
                    }
                }
            },
        )

        # Should create a backup selection
        self.template.has_resource(
            CfnBackupSelection.CFN_RESOURCE_TYPE_NAME,
            {
                'Properties': {
                    'BackupSelection': {
                        'SelectionName': Match.any_value(),
                        'IamRoleArn': {
                            'Fn::GetAtt': [
                                self.stack.get_logical_id(self.backup_infrastructure_stack.node.default_child),
                                Match.string_like_regexp(
                                    r'Outputs\.TestStackBackupInfrastructureBackupServiceRole.*Arn'
                                ),
                            ],
                        },
                        'Resources': [
                            {
                                'Fn::GetAtt': [
                                    backup_bucket_logical_id,
                                    'Arn',
                                ],
                            },
                        ],
                    }
                }
            },
        )
