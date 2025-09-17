from unittest import TestCase

from aws_cdk import App, Stack
from aws_cdk.assertions import Template
from aws_cdk.aws_chatbot import CfnSlackChannelConfiguration
from aws_cdk.aws_kms import Key
from aws_cdk.aws_sns import CfnSubscription, CfnTopic

from common_constructs.alarm_topic import AlarmTopic


class TestQueuedLambdaProcessor(TestCase):
    def test_creates_topic(self):
        app = App()
        stack = Stack(app, 'Stack')

        key = Key(stack, 'Key')
        topic = AlarmTopic(
            stack,
            'Topic',
            master_key=key,
            email_subscriptions=['justin@example.com'],
            slack_subscriptions=[
                {
                    'channel_name': 'example_channel',
                    'channel_id': 'C012345ABCD',
                    'workspace_id': 'T01234ABC',
                }
            ],
        )

        template = Template.from_stack(stack)

        # Ensure we're making a topic, encrypted as we expect
        template.has_resource(
            type=CfnTopic.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {'KmsMasterKeyId': {'Fn::GetAtt': [stack.get_logical_id(key.node.default_child), 'Arn']}}
            },
        )

        # Ensure we have email subscription we expect
        template.has_resource(
            type=CfnSubscription.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'Endpoint': 'justin@example.com',
                    'Protocol': 'email',
                    'TopicArn': {'Ref': stack.get_logical_id(topic.node.default_child)},
                }
            },
        )

        # Ensure we have the slack channel configuration we expect
        template.has_resource(
            type=CfnSlackChannelConfiguration.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'SlackChannelId': 'C012345ABCD',
                    'SlackWorkspaceId': 'T01234ABC',
                    'SnsTopicArns': [{'Ref': stack.get_logical_id(topic.node.default_child)}],
                }
            },
        )
