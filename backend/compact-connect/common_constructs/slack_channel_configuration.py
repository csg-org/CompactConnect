from typing import List

from aws_cdk import Stack, ArnFormat
from aws_cdk.aws_chatbot import SlackChannelConfiguration as CdkSlackChannelConfiguration
from aws_cdk.aws_iam import ManagedPolicy, PolicyStatement, Effect
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from constructs import Construct


class SlackChannelConfiguration(CdkSlackChannelConfiguration):
    """
    Simplified Chatbot configuration for our use
    """
    def __init__(
            self, scope: Construct, construct_id: str, *,
            workspace_id: str,
            channel_id: str,
            notification_topics: List[ITopic]
    ):
        super().__init__(
            scope, construct_id,
            slack_channel_configuration_name=f'{scope.node.id}-{construct_id}',
            slack_workspace_id=workspace_id,
            slack_channel_id=channel_id,
            notification_topics=notification_topics
        )

        self._configure_chatbot_role()

    def _configure_chatbot_role(self):
        stack = Stack.of(self)
        self.role.add_managed_policy(ManagedPolicy.from_aws_managed_policy_name('job-function/ViewOnlyAccess'))
        NagSuppressions.add_resource_suppressions(
            self.role,
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'appliesTo': ['Policy::arn:<AWS::Partition>:iam::aws:policy/job-function/ViewOnlyAccess'],
                    'reason': 'This role is general-purpose for operations integration and the AWS-managed '
                              'ViewOnlyAccess policy is suitable'
                },
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'This role is intended to be able to query logs across teh account to facilitate '
                              'operational support, which requires log group wildcard resources.'
                }
            ]
        )

        # Enable the CloudWatch querying feature in the Alarm integration
        self.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'logs:StartQuery',
                    'logs:GetQueryResults'
                ],
                resources=[
                    stack.format_arn(
                        partition=stack.partition,
                        service='logs',
                        region=stack.region,
                        account=stack.account,
                        resource='log-group',
                        resource_name='*',
                        arn_format=ArnFormat.COLON_RESOURCE_NAME
                    )
                ]
            )
        )

        # Allow basic operational log/metric viewing
        self.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=[
                    'cloudwatch:DescribeAlarmHistory',
                    'cloudwatch:GetDashboard',
                    'cloudwatch:GenerateQuery',
                    'cloudwatch:GetMetricData',
                    'cloudwatch:ListDashboards',
                    'cloudwatch:ListMetrics'
                ],
                resources=['*']
            )
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'This role is intended to be able to query logs across the account to facilitate '
                              'operational support, which requires log group wildcard resources.'
                }
            ]
        )
