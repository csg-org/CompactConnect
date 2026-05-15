import json
import os

from aws_cdk import CustomResource, Duration
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_logs import LogGroup, RetentionDays
from aws_cdk.custom_resources import Provider
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct

from common_constructs.python_function import PythonFunction

from .compact_configuration_table import CompactConfigurationTable


class CompactConfigurationUpload(Construct):
    """Custom resource to upload active member jurisdictions data to the compact configuration table."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        table: CompactConfigurationTable,
        master_key: IKey,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        stack: Stack = Stack.of(self)

        self.compact_configuration_upload_function = PythonFunction(
            scope,
            'CompactConfigurationUploadFunction',
            lambda_dir='custom-resources',
            index=os.path.join('handlers', 'compact_config_uploader.py'),
            handler='on_event',
            description='Uploads active member jurisdictions to the compact configuration Dynamo table',
            timeout=Duration.minutes(5),
            log_retention=RetentionDays.THREE_MONTHS,
            environment={'COMPACT_CONFIGURATION_TABLE_NAME': table.table_name, **stack.common_env_vars},
        )

        # grant lambda access to the compact configuration table
        table.grant_read_write_data(self.compact_configuration_upload_function)
        # grant lambda access to the KMS key
        master_key.grant_encrypt_decrypt(self.compact_configuration_upload_function)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            path=f'{self.compact_configuration_upload_function.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )

        compact_configuration_upload_provider_log_group = LogGroup(
            scope,
            'CompactConfigurationUploadProviderLogGroup',
            retention=RetentionDays.ONE_DAY,
        )
        NagSuppressions.add_resource_suppressions(
            compact_configuration_upload_provider_log_group,
            suppressions=[
                {
                    'id': 'HIPAA.Security-CloudWatchLogGroupEncrypted',
                    'reason': 'We do not log sensitive data to CloudWatch, and operational visibility of system'
                    ' logs to operators with credentials for the AWS account is desired. Encryption is not appropriate'
                    ' here.',
                },
            ],
        )
        self.compact_configuration_upload_provider = Provider(
            scope,
            'CompactConfigurationUploadProvider',
            on_event_handler=self.compact_configuration_upload_function,
            log_group=compact_configuration_upload_provider_log_group,
        )
        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            f'{self.compact_configuration_upload_provider.node.path}/framework-onEvent/Resource',
            [
                {'id': 'AwsSolutions-L1', 'reason': 'We do not control this runtime'},
                {
                    'id': 'HIPAA.Security-LambdaConcurrency',
                    'reason': 'This function is only run at deploy time, by CloudFormation and has no need for '
                    'concurrency limits.',
                },
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': 'This is a synchronous function run at deploy time. It does not need a DLQ',
                },
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'We may choose to move our lambdas into private VPC subnets in a future enhancement',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            path=f'{self.compact_configuration_upload_provider.node.path}'
            f'/framework-onEvent/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            path=f'{self.compact_configuration_upload_provider.node.path}/framework-onEvent/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'appliesTo': [
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    ],  # noqa: E501 line-too-long
                    'reason': 'This policy is appropriate for the log retention lambda',
                },
            ],
        )

        self.compact_configuration_uploader_custom_resource = CustomResource(
            scope,
            'CompactConfigurationUploadCustomResource',
            resource_type='Custom::CompactConfigurationUpload',
            service_token=self.compact_configuration_upload_provider.service_token,
            properties={
                'active_compact_member_jurisdictions': json.dumps(
                    self.node.get_context('active_compact_member_jurisdictions')
                ),
            },
        )
