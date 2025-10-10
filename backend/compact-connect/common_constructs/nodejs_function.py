import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_iam import IRole, Role, ServicePrincipal
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_nodejs import BundlingOptions, OutputFormat
from aws_cdk.aws_lambda_nodejs import NodejsFunction as CdkNodejsFunction
from aws_cdk.aws_logs import LogGroup, RetentionDays
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
        role: IRole = None,
        **kwargs,
    ):
        defaults = {
            'timeout': Duration.seconds(28),
        }
        defaults.update(kwargs)

        nodejs_dir = os.path.join('lambdas', 'nodejs')
        lambda_dir = os.path.join(nodejs_dir, lambda_dir)

        log_group = LogGroup(
            scope,
            f'{construct_id}LogGroup',
            retention=log_retention,
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
        NagSuppressions.add_resource_suppressions(
            log_group,
            suppressions=[
                {
                    'id': 'HIPAA.Security-CloudWatchLogGroupEncrypted',
                    'reason': 'We do not log sensitive data to CloudWatch, and operational visibility of system'
                    ' logs to operators with credentials for the AWS account is desired. Encryption is not appropriate'
                    ' here.',
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

        super().__init__(
            scope,
            construct_id,
            runtime=Runtime.NODEJS_22_X,
            entry=os.path.join(lambda_dir, 'handler.ts'),
            deps_lock_file_path=os.path.join(nodejs_dir, 'yarn.lock'),
            bundling=BundlingOptions(
                format=OutputFormat.CJS,
                main_fields=['module', 'main'],
                esbuild_args={'--log-limit': '0', '--tree-shaking': 'true'},
                force_docker_bundling=True,
            ),
            log_group=log_group,
            role=role,
            **defaults,
        )
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
