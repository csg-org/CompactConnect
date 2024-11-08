from __future__ import annotations

import stacks.persistent_stack as ps
from aws_cdk import Duration, Stack
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_lambda import ILayerVersion, Runtime
from aws_cdk.aws_lambda_python_alpha import BundlingOptions, PythonLayerVersion
from aws_cdk.aws_lambda_python_alpha import PythonFunction as CdkPythonFunction
from aws_cdk.aws_logs import RetentionDays
from aws_cdk.aws_sns import ITopic
from aws_cdk.aws_ssm import StringParameter
from cdk_nag import NagSuppressions
from constructs import Construct

COMMON_PYTHON_LAMBDA_LAYER_SSM_PARAMETER_NAME = '/deployment/lambda/layers/common-python-layer-arn'


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
        **kwargs,
    ):
        defaults = {
            'timeout': Duration.seconds(28),
        }
        defaults.update(kwargs)

        super().__init__(
            scope,
            construct_id,
            runtime=Runtime.PYTHON_3_12,
            log_retention=log_retention,
            **defaults,
        )
        self.add_layers(self._get_common_layer())

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

    def _get_common_layer(self) -> ILayerVersion:
        common_layer_construct_id = 'CommonPythonLayer'
        stack = Stack.of(self)
        # Outside the Persistent stack, we look up the layer via an SSM parameter to avoid cross-stack references in
        # this case.
        if isinstance(stack, ps.PersistentStack):
            return stack.common_python_lambda_layer
        # We only want to do this look-up once per stack, so we'll first check if it's already been done for the
        # stack before creating a new one
        common_layer_version: ILayerVersion = stack.node.try_find_child(common_layer_construct_id)
        if common_layer_version is not None:
            return common_layer_version
        # Fetch the value from SSM parameter
        common_python_lambda_layer_parameter = StringParameter.from_string_parameter_name(
            stack,
            'CommonPythonLayerParameter',
            string_parameter_name=COMMON_PYTHON_LAMBDA_LAYER_SSM_PARAMETER_NAME,
        )
        return PythonLayerVersion.from_layer_version_arn(
            stack, common_layer_construct_id, common_python_lambda_layer_parameter.string_value
        )
