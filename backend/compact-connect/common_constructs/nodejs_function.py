import os

from aws_cdk import Duration, Stack
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_nodejs import BundlingOptions, OutputFormat
from aws_cdk.aws_lambda_nodejs import NodejsFunction as CdkNodejsFunction
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from constructs import Construct


class NodejsFunction(CdkNodejsFunction):
    """Standard NodeJS lambda function"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        lambda_dir: str,
        log_retention: RetentionDays = RetentionDays.ONE_MONTH,
        alarm_topic: ITopic = None,
        **kwargs,
    ):
        defaults = {
            'timeout': Duration.seconds(28),
        }
        defaults.update(kwargs)

        lambda_dir = os.path.join('lambdas', 'nodejs', lambda_dir)

        super().__init__(
            scope,
            construct_id,
            runtime=Runtime.NODEJS_20_X,
            entry=os.path.join(lambda_dir, 'bin', 'handler.ts'),
            deps_lock_file_path=os.path.join(lambda_dir, 'package-lock.json'),
            bundling=BundlingOptions(
                format=OutputFormat.CJS,
                main_fields=['module', 'main'],
                esbuild_args={'--log-limit': '0', '--tree-shaking': 'true'},
            ),
            log_retention=log_retention,
            **defaults,
        )
        if alarm_topic is not None:
            self._add_alarms(alarm_topic)

        stack = Stack.of(self)
        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': "These lambdas are synchronous and so don't require any DLQ configuration",
                },
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'We may choose to move our lambdas into private VPC subnets in a future enhancement',
                },
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{self.node.path}/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'applies_to': [
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
                    ],
                    'reason': 'The BasicExecutionRole policy is appropriate for these lambdas',
                },
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{stack.node.path}/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'applies_to': 'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',  # noqa: E501 line-too-long
                    'reason': 'This policy is appropriate for the log retention lambda',
                },
            ],
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{stack.node.path}/LogRetentionaae0aa3c5b4d4f87b02d85b201efdd8a/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'applies_to': ['Resource::*'],
                    'reason': 'This lambda needs to be able to configure log groups across the account, though the'
                    ' actions it is allowed are scoped specifically for this task.',
                },
            ],
        )

    def _add_alarms(self, alarm_topic: ITopic):
        throttle_alarm = Alarm(
            self,
            'ThrottleAlarm',
            metric=self.metric_throttles(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{self.node.path} lambda throttles detected',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )
        throttle_alarm.add_alarm_action(SnsAction(alarm_topic))
