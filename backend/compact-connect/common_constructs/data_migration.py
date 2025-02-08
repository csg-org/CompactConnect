import os

import jsii
from aws_cdk import CustomResource, Duration, Stack
from aws_cdk.aws_iam import IGrantable, IRole
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.custom_resources import Provider
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.python_function import PythonFunction


@jsii.implements(IGrantable)
class DataMigration(Construct):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        migration_dir: str,
        lambda_environment: dict,
        role: IRole = None,
        custom_resource_properties: dict = None,
    ):
        super().__init__(scope, construct_id)
        self.migration_function = PythonFunction(
            scope,
            'MigrationFunction',
            index=os.path.join(migration_dir, 'main.py'),
            lambda_dir='migration',
            handler='on_event',
            role=role,
            environment=lambda_environment,
            timeout=Duration.minutes(15),
        )
        self.provider = Provider(
            scope,
            'Provider',
            on_event_handler=self.migration_function,
            log_retention=RetentionDays.ONE_DAY,
        )
        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(scope),
            f'{self.provider.node.path}/framework-onEvent/Resource',
            [
                {
                    'id': 'AwsSolutions-L1',
                    'reason': 'We do not control this runtime',
                },
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
            path=f'{self.provider.node.path}/framework-onEvent/ServiceRole/DefaultPolicy/Resource',
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
            path=f'{self.provider.node.path}/framework-onEvent/ServiceRole/Resource',
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

        self.custom_resource = CustomResource(
            scope,
            'CustomResource',
            resource_type='Custom::DataMigration',
            service_token=self.provider.service_token,
            properties=custom_resource_properties,
        )

    @property
    def grant_principal(self):
        return self.migration_function.grant_principal
