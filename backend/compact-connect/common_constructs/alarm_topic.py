from typing import List

from aws_cdk import Stack, ArnFormat
from aws_cdk.aws_iam import ServicePrincipal, PolicyStatement, Effect
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_sns_subscriptions import EmailSubscription
from aws_cdk.aws_sns import Topic
from constructs import Construct

from common_constructs.slack_channel_configuration import SlackChannelConfiguration


class AlarmTopic(Topic):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            master_key: IKey,
            email_subscriptions: List[str] = tuple(),
            slack_subscriptions: List[dict] = tuple(),
            **kwargs
    ):
        super().__init__(
            scope, construct_id,
            master_key=master_key,
            enforce_ssl=True,
            **kwargs
        )

        self._configure_cloudwatch_principal(master_key)
        self._configure_s3_principal(master_key)

        for email in email_subscriptions:
            self.add_subscription(EmailSubscription(email))

        self.slack_channel_integrations = {}
        for config in slack_subscriptions:
            self.slack_channel_integrations[config['channel_name']] = SlackChannelConfiguration(
                self, f'{config['channel_name']}-SlackChannelConfiguration',
                notification_topics=[self],
                workspace_id=config['workspace_id'],
                channel_id=config['channel_id']
            )

    def _configure_cloudwatch_principal(self, master_key: IKey):
        stack = Stack.of(self)
        cloudwatch_principal = ServicePrincipal('cloudwatch.amazonaws.com')

        master_key.grant_encrypt_decrypt(cloudwatch_principal)

        self.add_to_resource_policy(
            # Allow CloudWatch to publish to this topic, but only from an Alarm in this account/region
            PolicyStatement(
                effect=Effect.ALLOW,
                principals=[cloudwatch_principal],
                resources=[self.topic_arn],
                actions=['sns:Publish'],
                conditions={
                    'ArnLike': {
                        # arn:aws:cloudwatch:{stack.region}:{stack.account}:alarm:*
                        'aws:SourceArn': stack.format_arn(
                            partition=stack.partition,
                            service='cloudwatch',
                            region=stack.region,
                            account=stack.account,
                            resource='alarm',
                            resource_name='*',
                            arn_format=ArnFormat.COLON_RESOURCE_NAME
                        )
                    },
                    'StringEquals': {
                        'aws:SourceAccount': stack.account
                    }
                }
            )
        )

    def _configure_s3_principal(self, master_key: IKey):
        stack = Stack.of(self)
        s3_principal = ServicePrincipal('s3.amazonaws.com')

        master_key.grant_encrypt_decrypt(s3_principal)

        self.add_to_resource_policy(
            # Allow S3 to publish events to this topic, but only from this account
            PolicyStatement(
                effect=Effect.ALLOW,
                principals=[s3_principal],
                resources=[self.topic_arn],
                actions=['sns:Publish'],
                conditions={
                    'ArnLike': {
                        # arn:aws:s3:*:*:*
                        'aws:SourceArn': stack.format_arn(
                            partition=stack.partition,
                            service='s3',
                            region='*',
                            account='*',
                            resource='*'
                        )
                    },
                    'StringEquals': {
                        'aws:SourceAccount': stack.account
                    }
                }
            )
        )
