import json
from unittest import TestCase

from app import LogAggregationApp
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_cloudtrail import CfnTrail
from aws_cdk.aws_s3 import CfnBucket
from stacks.stages import LogsAccountStage, ManagementAccountStage


class TestSynth(TestCase):
    def test_synth(self):
        # Load the example context file
        with open('cdk.context.example.json') as f:
            test_context = json.load(f)

        # Create the app with our test context
        app = LogAggregationApp(context=test_context)

        # Synthesize the app to ensure it builds without errors
        app.synth()

        # Inspect the logs account stage
        self._inspect_logs_account_stage(app.logs_stage)

        # Inspect the management account stage
        self._inspect_management_account_stage(app.management_stage)

    def _inspect_logs_account_stage(self, stage: LogsAccountStage):
        """Inspect the LogsAccountStage and its resources."""
        logs_stack = stage.logs_stack
        template = Template.from_stack(logs_stack)

        # Check that we have the expected number of S3 buckets
        template.resource_count_is(CfnBucket.CFN_RESOURCE_TYPE_NAME, 2)

        # Verify the CloudTrail logs bucket with all its expected properties
        template.has_resource_properties(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            {
                'BucketName': Match.string_like_regexp('.*-cloudtrail-data-events-.*'),
                'VersioningConfiguration': {'Status': 'Enabled'},
                'PublicAccessBlockConfiguration': {
                    'BlockPublicAcls': True,
                    'BlockPublicPolicy': True,
                    'IgnorePublicAcls': True,
                    'RestrictPublicBuckets': True,
                },
                'ObjectLockEnabled': True,
                'OwnershipControls': {'Rules': [{'ObjectOwnership': 'BucketOwnerEnforced'}]},
            },
        )
        # Verify CloudTrail bucket policy has a statement allowing CloudTrail service principal
        template.has_resource_properties(
            'AWS::S3::BucketPolicy',
            {
                'Bucket': {'Ref': logs_stack.get_logical_id(logs_stack.cloudtrail_logs_bucket.node.default_child)},
                'PolicyDocument': {
                    'Statement': Match.array_with(
                        [Match.object_like({'Effect': 'Allow', 'Principal': {'Service': 'cloudtrail.amazonaws.com'}})]
                    )
                },
            },
        )

        # Verify the Access Logs bucket with all its expected properties
        template.has_resource_properties(
            CfnBucket.CFN_RESOURCE_TYPE_NAME,
            {
                'BucketName': Match.string_like_regexp('.*-access-logs-.*'),
                'VersioningConfiguration': {'Status': 'Enabled'},
                'LifecycleConfiguration': {
                    'Rules': Match.array_with(
                        [
                            Match.object_like(
                                {
                                    'Status': 'Enabled',
                                    'Transitions': Match.array_with(
                                        [Match.object_like({'StorageClass': 'GLACIER_IR'})]
                                    ),
                                }
                            )
                        ]
                    )
                },
                'PublicAccessBlockConfiguration': {
                    'BlockPublicAcls': True,
                    'BlockPublicPolicy': False,  # This is intentionally false to allow org-based policies
                    'IgnorePublicAcls': True,
                    'RestrictPublicBuckets': True,
                },
            },
        )
        # Verify access logs bucket policy has a statement with organization ID condition
        template.has_resource_properties(
            'AWS::S3::BucketPolicy',
            {
                'Bucket': {'Ref': logs_stack.get_logical_id(logs_stack.s3_access_logs_bucket.node.default_child)},
                'PolicyDocument': {
                    'Statement': Match.array_with(
                        [
                            Match.object_like(
                                {
                                    'Effect': 'Allow',
                                    'Condition': {'StringEquals': {'aws:PrincipalOrgID': Match.any_value()}},
                                }
                            )
                        ]
                    )
                },
            },
        )

    def _inspect_management_account_stage(self, stage: ManagementAccountStage):
        trail_stack = stage.trail_stack
        template = Template.from_stack(trail_stack)
        # Check the properties that are most critical to us
        template.has_resource_properties(
            CfnTrail.CFN_RESOURCE_TYPE_NAME,
            {
                'IsMultiRegionTrail': False,  # controls cost
                'IsOrganizationTrail': True,  # includes all accounts in the organization
                'EnableLogFileValidation': True,  # validates the integrity of the log files
                # CloudTrail will validate that it can write to this bucket
                # So we just need to check that it is pointed to a bucket
                'S3BucketName': Match.any_value(),
                # Encryption is critical, since this trail can include sensitive data
                'KMSKeyId': {
                    'Fn::GetAtt': [trail_stack.get_logical_id(trail_stack.cloudtrail_key.node.default_child), 'Arn']
                },
                # This controls what events are included
                'AdvancedEventSelectors': [
                    {
                        'Name': 'DynamoDataEventsLog',
                        'FieldSelectors': [
                            {'Field': 'eventCategory', 'Equals': ['Data']},
                            {'Field': 'resources.type', 'Equals': ['AWS::DynamoDB::Table']},
                            {'Field': 'resources.ARN', 'EndsWith': ['-DataEventsLog']},
                            {'Field': 'readOnly', 'Equals': ['true']},
                        ],
                    }
                ],
            },
        )
