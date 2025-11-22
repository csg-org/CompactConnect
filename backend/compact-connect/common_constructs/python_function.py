from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_iam import IRole, Role, ServicePrincipal
from aws_cdk.aws_lambda import ILayerVersion, Runtime
from aws_cdk.aws_lambda_python_alpha import PythonFunction as CdkPythonFunction
from aws_cdk.aws_logs import ILogGroup, LogGroup, RetentionDays
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.python_common_layer_versions import PythonCommonLayerVersions


class PythonFunction(CdkPythonFunction):
    """
    Standard Python lambda function.
    """

    _common_layer_versions = None

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        lambda_dir: str,
        runtime: Runtime = Runtime.PYTHON_3_14,
        log_retention: RetentionDays = RetentionDays.INFINITE,
        alarm_topic: ITopic = None,
        role: IRole = None,
        log_group: ILogGroup = None,
        **kwargs,
    ):
        if self._common_layer_versions is None:
            raise RuntimeError(
                'The PythonCommonLayerVersions construct must be declared before these lambdas can be built'
            )

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
            runtime=runtime,
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
        return self._common_layer_versions.get_common_layer(for_function=self)

    @classmethod
    def register_layer_versions(cls, versions: PythonCommonLayerVersions):
        """
        Register the single PythonCommonLayerVersions object to use for referencing and attaching the common layer
        """
        cls._common_layer_versions = versions
