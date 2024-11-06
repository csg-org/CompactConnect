import jsii
from aws_cdk import Duration, Stack
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import BundlingOptions, ICommandHooks, PythonLayerVersion
from aws_cdk.aws_lambda_python_alpha import PythonFunction as CdkPythonFunction
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from constructs import Construct


class PythonFunction(CdkPythonFunction):
    """Standard Python lambda function that assumes unittest-compatible tests are written in the 'tests' directory.

    On bundling, this function will validate the lambda by temporarily installing dev dependencies in
    requirements-dev.txt, then executing and removing tests.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        log_retention: RetentionDays = RetentionDays.ONE_MONTH,
        alarm_topic: ITopic = None,
        layers: list[PythonLayerVersion] =None,
        **kwargs,
    ):
        defaults = {
            'timeout': Duration.seconds(28),
        }
        defaults.update(kwargs)

        super().__init__(
            scope,
            construct_id,
            bundling=BundlingOptions(command_hooks=TestingHooks()),
            runtime=Runtime.PYTHON_3_12,
            log_retention=log_retention,
            layers=layers,
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


@jsii.implements(ICommandHooks)
class TestingHooks:
    """Testing hooks that will automatically run the expected tests package to validate the lambda.

    This command hook will temporarily install dev dependencies, then execute unittest-compatible
    tests expected to be in the `tests` directory.
    """

    def after_bundling(self, input_dir: str, output_dir: str) -> list[str]:  # noqa: ARG002 unused-argument
        return [
            'mkdir _tmp_dev_deps',
            'python -m pip install -r requirements-dev.txt -t _tmp_dev_deps',
            'PYTHONPATH="$(pwd)/_tmp_dev_deps" python -m unittest discover -s tests',
            'rm -rf _tmp_dev_deps',
            'rm -rf tests',
        ]

    def before_bundling(self, input_dir: str, output_dir: str) -> list[str]:  # noqa: ARG002 unused-argument
        return []
