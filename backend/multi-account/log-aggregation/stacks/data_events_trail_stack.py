from aws_cdk import Environment, RemovalPolicy, Stack
from aws_cdk.aws_cloudtrail import Trail
from aws_cdk.aws_iam import Effect, PolicyStatement, ServicePrincipal, StarPrincipal
from aws_cdk.aws_kms import Key
from aws_cdk.aws_s3 import Bucket
from constructs import Construct


class DataEventsTrailStack(Stack):
    """Stack for CloudTrail resources in the management account."""

    def __init__(
        self, scope: Construct, construct_id: str, env: Environment, cloudtrail_logs_bucket_name: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, env=env, **kwargs)

        # Reference the existing bucket in the logs account
        logs_bucket = Bucket.from_bucket_name(self, 'CloudTrailLogsBucket', cloudtrail_logs_bucket_name)

        # Create a KMS key for CloudTrail encryption
        self.cloudtrail_key = Key(
            self,
            'CloudTrailKey',
            alias='alias/cloudtrail-data-events-key',
            description='KMS key for CloudTrail data events encryption',
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,
        )
        # This explicitly blocks any principals other than CloudTrail itself (including account admins) from reading
        # or writing data encrypted with this key. We're using a 'break glass in case of emergency' approach here,
        # where nobody has read access to the key but we can grant access by specifically modifying the resource
        # policy, if we have a need to do an audit or post-incident forensic analysis.
        self.cloudtrail_key.add_to_resource_policy(
            PolicyStatement(
                effect=Effect.DENY,
                actions=['kms:Decrypt', 'kms:Encrypt', 'kms:GenerateDataKey*', 'kms:ReEncrypt*'],
                principals=[StarPrincipal()],
                resources=['*'],
                conditions={
                    'StringNotEquals': {
                        'aws:PrincipalServiceName': ['cloudtrail.amazonaws.com'],
                    }
                },
            )
        )

        # Include region in trail name to avoid conflicts with trails in other regions
        trail_name = f'data-events-trail-{self.region}'

        # Create the CloudTrail trail
        trail = Trail(
            self,
            'DataEventsTrail',
            trail_name=trail_name,
            bucket=logs_bucket,
            s3_key_prefix='DataEvents',
            include_global_service_events=True,
            is_multi_region_trail=False,  # Single region trail
            is_organization_trail=True,
            enable_file_validation=True,
            send_to_cloud_watch_logs=False,
            encryption_key=self.cloudtrail_key,
        )

        # Construct the CloudTrail ARN pattern for the encryption context
        cloudtrail_arn_pattern = Stack.format_arn(
            self,
            service='cloudtrail',
            resource='trail/*',
            # Explicitly setting this account is critical to prevent confused deputy attacks from other accounts.
            account=self.account,
            region='*',
            partition=self.partition,
        )

        # Add CloudTrail service principal to the key policy with conditions to prevent confused deputy attacks
        self.cloudtrail_key.add_to_resource_policy(
            PolicyStatement(
                sid='AllowCloudTrailToEncryptLogs',
                effect=Effect.ALLOW,
                principals=[ServicePrincipal('cloudtrail.amazonaws.com')],
                actions=['kms:GenerateDataKey*', 'kms:Decrypt'],
                resources=['*'],
                conditions={
                    'StringLike': {
                        'aws:SourceArn': cloudtrail_arn_pattern,
                        'kms:EncryptionContext:aws:cloudtrail:arn': cloudtrail_arn_pattern,
                    }
                },
            )
        )

        # We can't do this with the L2 construct yet, so let's use the lower-level CloudFormation resource to
        # configure the trail with advanced event selectors
        trail.node.default_child.add_property_override(
            'AdvancedEventSelectors',
            [
                {
                    'Name': 'DynamoDataEventsLog',
                    'FieldSelectors': [
                        {'Field': 'eventCategory', 'Equals': ['Data']},
                        {'Field': 'resources.type', 'Equals': ['AWS::DynamoDB::Table']},
                        # We only want to include data events for tables that have
                        # 'opted in' by adding a -DataEventsLog suffix to the table name
                        {'Field': 'resources.ARN', 'EndsWith': ['-DataEventsLog']},
                        # If we include write events in this trail, we'll be guaranteed to include
                        # social security numbers in the trail, which makes this trail just as sensitive
                        # as our SSN table. We'll reduce that sensitivity by only including read events.
                        {'Field': 'readOnly', 'Equals': ['true']},
                    ],
                }
            ],
        )
