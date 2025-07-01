from unittest import TestCase

from aws_cdk import App, Duration, Stack
from aws_cdk.assertions import Template
from aws_cdk.aws_cloudwatch import CfnAlarm
from aws_cdk.aws_events import CfnRule, EventBus
from aws_cdk.aws_kms import Key
from aws_cdk.aws_lambda import CfnEventSourceMapping, Code, Function, Runtime
from aws_cdk.aws_sns import Topic
from aws_cdk.aws_sqs import CfnQueue
from common_constructs.queue_event_listener import QueueEventListener


class TestQueueEventListener(TestCase):
    def setUp(self):
        self.app = App()
        self.stack = Stack(self.app, 'TestStack')

        # Create test dependencies
        self.key = Key(self.stack, 'TestKey')
        self.topic = Topic(self.stack, 'TestTopic')
        self.event_bus = EventBus(self.stack, 'TestEventBus')
        self.function = Function(
            self.stack,
            'TestFunction',
            handler='handle',
            runtime=Runtime.PYTHON_3_12,
            code=Code.from_inline("""def handle(*args): return"""),
        )

    def test_creates_queue_event_listener_with_default_parameters(self):
        """Test that QueueEventListener creates all required resources with default parameters."""
        listener = QueueEventListener(
            self.stack,
            'TestListener',
            data_event_bus=self.event_bus,
            listener_function=self.function,
            listener_detail_type='test.event',
            encryption_key=self.key,
            alarm_topic=self.topic,
        )

        template = Template.from_stack(self.stack)

        # Verify the lambda function failure alarm is created
        template.has_resource(
            CfnAlarm.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'AlarmDescription': f'{self.function.node.path} failed to process a message',
                    'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                    'EvaluationPeriods': 1,
                    'Threshold': 1,
                    'TreatMissingData': 'notBreaching',
                }
            },
        )

        # Verify the QueuedLambdaProcessor components are created (SQS queues)
        queues = template.find_resources(
            CfnQueue.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'KmsMasterKeyId': {'Fn::GetAtt': [self.stack.get_logical_id(self.key.node.default_child), 'Arn']}
                }
            },
        )
        # Should have 2 queues: main queue and DLQ
        self.assertEqual(2, len(queues))

        # Verify the main queue has correct configuration
        template.has_resource(
            CfnQueue.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'MessageRetentionPeriod': 12 * 3600,  # 12 hours (default)
                    'RedrivePolicy': {
                        'deadLetterTargetArn': {
                            'Fn::GetAtt': [
                                self.stack.get_logical_id(listener.queue_processor.dlq.node.default_child),
                                'Arn',
                            ]
                        },
                        'maxReceiveCount': 3,  # default
                    },
                    'VisibilityTimeout': 5 * 60,  # 5 minutes (default)
                }
            },
        )

        # Verify EventBridge rule is created
        template.has_resource(
            CfnRule.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'EventBusName': {'Ref': self.stack.get_logical_id(self.event_bus.node.default_child)},
                    'EventPattern': {'detail-type': ['test.event']},
                    'State': 'ENABLED',
                    'Targets': [
                        {
                            'Arn': {
                                'Fn::GetAtt': [
                                    self.stack.get_logical_id(listener.queue_processor.queue.node.default_child),
                                    'Arn',
                                ]
                            },
                            'DeadLetterConfig': {
                                'Arn': {
                                    'Fn::GetAtt': [
                                        self.stack.get_logical_id(listener.queue_processor.dlq.node.default_child),
                                        'Arn',
                                    ]
                                }
                            },
                            'Id': 'Target0',
                        }
                    ],
                }
            },
        )

        # Verify EventBridge rule failure alarm is created
        template.has_resource(
            CfnAlarm.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'MetricName': 'FailedInvocations',
                    'Namespace': 'AWS/Events',
                    'ComparisonOperator': 'GreaterThanOrEqualToThreshold',
                    'EvaluationPeriods': 1,
                    'Threshold': 1,
                    'TreatMissingData': 'notBreaching',
                }
            },
        )

        # Verify event source mapping is created
        template.has_resource(
            CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'BatchSize': 10,  # default
                    'EventSourceArn': {
                        'Fn::GetAtt': [
                            self.stack.get_logical_id(listener.queue_processor.queue.node.default_child),
                            'Arn',
                        ]
                    },
                    'FunctionName': {'Ref': self.stack.get_logical_id(self.function.node.default_child)},
                    'FunctionResponseTypes': ['ReportBatchItemFailures'],
                    'MaximumBatchingWindowInSeconds': 15,  # default
                }
            },
        )

    def test_creates_queue_event_listener_with_custom_parameters(self):
        """Test that QueueEventListener respects custom parameters."""
        listener = QueueEventListener(
            self.stack,
            'CustomListener',
            data_event_bus=self.event_bus,
            listener_function=self.function,
            listener_detail_type='custom.event',
            encryption_key=self.key,
            alarm_topic=self.topic,
            visibility_timeout=Duration.minutes(10),
            retention_period=Duration.hours(24),
            max_batching_window=Duration.seconds(30),
            max_receive_count=5,
            batch_size=20,
            dlq_count_alarm_threshold=5,
        )

        template = Template.from_stack(self.stack)

        # Verify the main queue has custom configuration
        template.has_resource(
            CfnQueue.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'MessageRetentionPeriod': 24 * 3600,  # 24 hours (custom)
                    'RedrivePolicy': {
                        'deadLetterTargetArn': {
                            'Fn::GetAtt': [
                                self.stack.get_logical_id(listener.queue_processor.dlq.node.default_child),
                                'Arn',
                            ]
                        },
                        'maxReceiveCount': 5,  # custom
                    },
                    'VisibilityTimeout': 10 * 60,  # 10 minutes (custom)
                }
            },
        )

        # Verify event source mapping has custom configuration
        template.has_resource(
            CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'BatchSize': 20,  # custom
                    'EventSourceArn': {
                        'Fn::GetAtt': [
                            self.stack.get_logical_id(listener.queue_processor.queue.node.default_child),
                            'Arn',
                        ]
                    },
                    'FunctionName': {'Ref': self.stack.get_logical_id(self.function.node.default_child)},
                    'FunctionResponseTypes': ['ReportBatchItemFailures'],
                    'MaximumBatchingWindowInSeconds': 30,  # custom
                }
            },
        )

        # Verify EventBridge rule with custom detail type
        template.has_resource(
            CfnRule.CFN_RESOURCE_TYPE_NAME,
            props={
                'Properties': {
                    'EventBusName': {'Ref': self.stack.get_logical_id(self.event_bus.node.default_child)},
                    'EventPattern': {'detail-type': ['custom.event']},
                    'State': 'ENABLED',
                }
            },
        )

    def test_exposes_expected_attributes(self):
        """Test that QueueEventListener exposes the expected public attributes."""
        listener = QueueEventListener(
            self.stack,
            'AttributeTestListener',
            data_event_bus=self.event_bus,
            listener_function=self.function,
            listener_detail_type='attribute.test',
            encryption_key=self.key,
            alarm_topic=self.topic,
        )

        # Verify all expected attributes are accessible
        self.assertIsNotNone(listener.lambda_failure_alarm)
        self.assertIsNotNone(listener.queue_processor)
        self.assertIsNotNone(listener.event_rule)
        self.assertIsNotNone(listener.event_bridge_failure_alarm)

        # Verify that queue_processor exposes expected attributes
        self.assertIsNotNone(listener.queue_processor.queue)
        self.assertIsNotNone(listener.queue_processor.dlq)
        self.assertIsNotNone(listener.queue_processor.process_function)
        self.assertIsNotNone(listener.queue_processor.event_source_mapping)

    def test_alarms_count(self):
        """Test that the correct number of alarms are created."""
        QueueEventListener(
            self.stack,
            'AlarmTestListener',
            data_event_bus=self.event_bus,
            listener_function=self.function,
            listener_detail_type='alarm.test',
            encryption_key=self.key,
            alarm_topic=self.topic,
        )

        template = Template.from_stack(self.stack)

        # Should create 4 alarms total:
        # 1. Lambda failure alarm (from QueueEventListener)
        # 2. EventBridge rule failure alarm (from QueueEventListener)
        # 3. Queue message age alarm (from QueuedLambdaProcessor)
        # 4. DLQ message count alarm (from QueuedLambdaProcessor)
        alarms = template.find_resources(CfnAlarm.CFN_RESOURCE_TYPE_NAME)
        self.assertEqual(4, len(alarms))

    def test_construct_id_propagation(self):
        """Test that construct_id is properly propagated to child constructs."""
        listener = QueueEventListener(
            self.stack,
            'PropagationTest',
            data_event_bus=self.event_bus,
            listener_function=self.function,
            listener_detail_type='propagation.test',
            encryption_key=self.key,
            alarm_topic=self.topic,
        )

        # Check that the construct IDs are properly formed
        self.assertTrue(listener.lambda_failure_alarm.node.id.startswith('PropagationTest'))
        self.assertTrue(listener.queue_processor.node.id.startswith('PropagationTest'))
        self.assertTrue(listener.event_rule.node.id.startswith('PropagationTest'))
        self.assertTrue(listener.event_bridge_failure_alarm.node.id.startswith('PropagationTest'))
