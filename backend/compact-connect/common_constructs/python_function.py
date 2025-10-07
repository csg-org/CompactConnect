from __future__ import annotations

import os

from aws_cdk import Duration, Stack
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_iam import IRole, Role, ServicePrincipal
from aws_cdk.aws_lambda import ILayerVersion, LoggingFormat, Runtime
from aws_cdk.aws_lambda_python_alpha import PythonFunction as CdkPythonFunction
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import ILogGroup, LogGroup, RetentionDays
from aws_cdk.aws_sns import ITopic
from aws_cdk.aws_ssm import StringParameter
from cdk_nag import NagSuppressions
from constructs import Construct

COMMON_PYTHON_LAMBDA_LAYER_SSM_PARAMETER_NAME = '/deployment/lambda/layers/common-python-layer-arn'


class PythonFunction(CdkPythonFunction):
    """
    Standard Python lambda function.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        lambda_dir: str,
        log_retention: RetentionDays = RetentionDays.INFINITE,
        alarm_topic: ITopic = None,
        role: IRole = None,
        log_group: ILogGroup = None,
        **kwargs,
    ):
        defaults = {
            'timeout': Duration.seconds(28),
        }
        defaults.update(kwargs)

        if not log_group:
            log_group = LogGroup(
                scope,
                f'{construct_id}LogGroup',
                retention=log_retention,
            )
            NagSuppressions.add_resource_suppressions(
                log_group,
                suppressions=[
                    {
                        'id': 'HIPAA.Security-CloudWatchLogGroupEncrypted',
                        'reason': 'We do not log sensitive data to CloudWatch, and operational visibility of system'
                        ' logs to operators with credentials for the AWS account is desired. Encryption is not'
                        ' appropriate here.',
                    },
                ],
            )
            if log_retention == RetentionDays.INFINITE:
                NagSuppressions.add_resource_suppressions(
                    log_group,
                    suppressions=[
                        {
                            'id': 'HIPAA.Security-CloudWatchLogGroupRetentionPeriod',
                            'reason': 'We are deliberately retaining logs indefinitely here.',
                        },
                    ],
                )

        if not role:
            role = Role(
                scope,
                f'{construct_id}Role',
                assumed_by=ServicePrincipal('lambda.amazonaws.com'),
            )
            log_group.grant_write(role)
        # We can't directly grant a provided role permission to log to our log group, since that could create a
        # circular dependency with the stack the role came from. The role creator will have to be responsible for
        # setting its permissions.

        super().__init__(
            scope,
            construct_id,
            entry=os.path.join('lambdas', 'python', lambda_dir),
            runtime=Runtime.PYTHON_3_13,
            logging_format=LoggingFormat.TEXT,
            log_group=log_group,
            role=role,
            **defaults,
        )
        self.add_layers(self._get_common_layer())

        if alarm_topic is not None:
            self._add_alarms(alarm_topic)

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
                {
                    'id': 'AwsSolutions-L1',
                    'reason': 'We will assess migrating to the 3.13 runtime '
                    'after the runtime has had time to stabilize',
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
        # Move to local import to avoid circular import
        from stacks import persistent_stack as ps

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
