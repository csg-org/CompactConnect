from unittest import TestCase

from aws_cdk import App, Duration, Stack
from aws_cdk.assertions import Template
from aws_cdk.aws_kms import Key
from aws_cdk.aws_lambda import CfnEventSourceMapping, Code, Function, Runtime
from aws_cdk.aws_sns import Topic
from aws_cdk.aws_sqs import CfnQueue

from common_constructs.queued_lambda_processor import QueuedLambdaProcessor


class TestQueuedLambdaProcessor(TestCase):
    def test_creates_queues_and_event_source(self):
        app = App()
        stack = Stack(app, 'Stack')

        key = Key(stack, 'Key')
        topic = Topic(stack, 'Topic')
        function = Function(
            stack,
            'Function',
            handler='handle',
            runtime=Runtime.PYTHON_3_12,
            code=Code.from_inline("""def handle(*args): return"""),
        )
        processor = QueuedLambdaProcessor(
            stack,
            'Processor',
            process_function=function,
            visibility_timeout=Duration.minutes(5),
            retention_period=Duration.hours(12),
            max_batching_window=Duration.minutes(4),
            max_receive_count=3,
            batch_size=6,
            encryption_key=key,
            alarm_topic=topic,
        )

        template = Template.from_stack(stack)
        queues = template.find_resources(
            CfnQueue.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {'KmsMasterKeyId': {'Fn::GetAtt': [stack.get_logical_id(key.node.default_child), 'Arn']}}
            },
        )
        # The DLQ and Queue should both be encrypted with the provided key
        self.assertEqual(2, len(queues))

        template.has_resource(
            CfnQueue.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'MessageRetentionPeriod': 12 * 3600,
                    'RedrivePolicy': {
                        'deadLetterTargetArn': {
                            'Fn::GetAtt': [stack.get_logical_id(processor.dlq.node.default_child), 'Arn']
                        },
                        'maxReceiveCount': 3,
                    },
                    'VisibilityTimeout': 5 * 60,
                }
            },
        )

        template.has_resource(
            CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'BatchSize': 6,
                    'EventSourceArn': {'Fn::GetAtt': [stack.get_logical_id(processor.queue.node.default_child), 'Arn']},
                    'FunctionName': {'Ref': stack.get_logical_id(function.node.default_child)},
                    'FunctionResponseTypes': ['ReportBatchItemFailures'],
                    'MaximumBatchingWindowInSeconds': 4 * 60,
                }
            },
        )
