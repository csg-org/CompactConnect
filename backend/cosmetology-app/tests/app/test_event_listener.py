import json
from unittest import TestCase

from aws_cdk.assertions import Template
from aws_cdk.aws_events import CfnRule
from aws_cdk.aws_lambda import CfnEventSourceMapping, CfnFunction
from aws_cdk.aws_sqs import CfnQueue

from tests.app.base import TstAppABC


class TestEventListenerStack(TstAppABC, TestCase):
    """
    Test cases for the EventListenerStack to ensure proper resource configuration
    for handling license encumbrance events.
    """

    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']
        with open('cdk.context.sandbox-example.json') as f:
            context.update(json.load(f))

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []
        return context

    def test_license_encumbrance_listener_resources_created(self):
        """
        Test that the license encumbrance listener lambda is added with a SQS queue
        and an event bridge event rule that listens for 'license.encumbrance' detail types.
        """
        event_listener_stack = self.app.sandbox_backend_stage.event_listener_stack
        event_listener_template = Template.from_stack(event_listener_stack)

        # Verify the lambda function is created
        license_encumbrance_handler_logical_id = event_listener_stack.get_logical_id(
            event_listener_stack.event_processors[
                'LicenseEncumbranceListener'
            ].queue_processor.process_function.node.default_child
        )
        license_encumbrance_handler = TestEventListenerStack.get_resource_properties_by_logical_id(
            license_encumbrance_handler_logical_id,
            resources=event_listener_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            'handlers.encumbrance_events.license_encumbrance_listener', license_encumbrance_handler['Handler']
        )

        # Verify SQS queue is created for the license encumbrance listener
        listener_queue_logical_id = event_listener_stack.get_logical_id(
            event_listener_stack.event_processors['LicenseEncumbranceListener'].queue_processor.queue.node.default_child
        )
        license_encumbrance_listener_queue = TestEventListenerStack.get_resource_properties_by_logical_id(
            listener_queue_logical_id, resources=event_listener_template.find_resources(CfnQueue.CFN_RESOURCE_TYPE_NAME)
        )

        dlq_logical_id = event_listener_stack.get_logical_id(
            event_listener_stack.event_processors['LicenseEncumbranceListener'].queue_processor.dlq.node.default_child
        )

        # remove dynamic field
        del license_encumbrance_listener_queue['KmsMasterKeyId']

        self.assertEqual(
            {
                'MessageRetentionPeriod': 43200,
                'RedrivePolicy': {'deadLetterTargetArn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}, 'maxReceiveCount': 3},
                'VisibilityTimeout': 300,
            },
            license_encumbrance_listener_queue,
        )

        # Verify EventBridge rule is created with correct detail type
        license_encumbrance_listener_event_bridge_rule = TestEventListenerStack.get_resource_properties_by_logical_id(
            event_listener_stack.get_logical_id(
                event_listener_stack.event_processors['LicenseEncumbranceListener'].event_rule.node.default_child
            ),
            resources=event_listener_template.find_resources(CfnRule.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            {
                'EventBusName': {
                    'Fn::Select': [
                        1,
                        {
                            'Fn::Split': [
                                '/',
                                {'Fn::Select': [5, {'Fn::Split': [':', {'Ref': 'DataEventBusArnParameterParameter'}]}]},
                            ]
                        },
                    ]
                },
                'EventPattern': {'detail-type': ['license.encumbrance']},
                'State': 'ENABLED',
                'Targets': [
                    {
                        'Arn': {'Fn::GetAtt': [listener_queue_logical_id, 'Arn']},
                        'DeadLetterConfig': {'Arn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}},
                        'Id': 'Target0',
                    }
                ],
            },
            license_encumbrance_listener_event_bridge_rule,
        )

        # Verify event source mapping between SQS queue and Lambda function
        event_source_mapping = TestEventListenerStack.get_resource_properties_by_logical_id(
            event_listener_stack.get_logical_id(
                event_listener_stack.event_processors[
                    'LicenseEncumbranceListener'
                ].queue_processor.event_source_mapping.node.default_child
            ),
            resources=event_listener_template.find_resources(CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME),
        )
        self.assertEqual(
            {
                'BatchSize': 10,
                'EventSourceArn': {'Fn::GetAtt': [listener_queue_logical_id, 'Arn']},
                'FunctionName': {'Ref': license_encumbrance_handler_logical_id},
                'FunctionResponseTypes': ['ReportBatchItemFailures'],
                'MaximumBatchingWindowInSeconds': 15,
            },
            event_source_mapping,
        )

    def test_license_encumbrance_lifting_listener_resources_created(self):
        """
        Test that the license encumbrance lifting listener lambda is added with a SQS queue
        and an event bridge event rule that listens for 'license.encumbranceLifted' detail types.
        """
        event_listener_stack = self.app.sandbox_backend_stage.event_listener_stack
        event_listener_template = Template.from_stack(event_listener_stack)

        # Verify the lambda function is created
        lifting_encumbrance_handler_logical_id = event_listener_stack.get_logical_id(
            event_listener_stack.event_processors[
                'LiftedLicenseEncumbranceListener'
            ].queue_processor.process_function.node.default_child
        )
        lifting_encumbrance_handler = TestEventListenerStack.get_resource_properties_by_logical_id(
            lifting_encumbrance_handler_logical_id,
            resources=event_listener_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            'handlers.encumbrance_events.license_encumbrance_lifted_listener', lifting_encumbrance_handler['Handler']
        )

        # Verify SQS queue is created for the license encumbrance lifting listener
        lifting_listener_queue_logical_id = event_listener_stack.get_logical_id(
            event_listener_stack.event_processors[
                'LiftedLicenseEncumbranceListener'
            ].queue_processor.queue.node.default_child
        )
        lifting_encumbrance_listener_queue = TestEventListenerStack.get_resource_properties_by_logical_id(
            lifting_listener_queue_logical_id,
            resources=event_listener_template.find_resources(CfnQueue.CFN_RESOURCE_TYPE_NAME),
        )

        dlq_logical_id = event_listener_stack.get_logical_id(
            event_listener_stack.event_processors[
                'LiftedLicenseEncumbranceListener'
            ].queue_processor.dlq.node.default_child
        )

        # remove dynamic field
        del lifting_encumbrance_listener_queue['KmsMasterKeyId']

        self.assertEqual(
            {
                'MessageRetentionPeriod': 43200,
                'RedrivePolicy': {'deadLetterTargetArn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}, 'maxReceiveCount': 3},
                'VisibilityTimeout': 300,
            },
            lifting_encumbrance_listener_queue,
        )

        # Verify EventBridge rule is created with correct detail type
        lifting_encumbrance_listener_event_bridge_rule = TestEventListenerStack.get_resource_properties_by_logical_id(
            event_listener_stack.get_logical_id(
                event_listener_stack.event_processors['LiftedLicenseEncumbranceListener'].event_rule.node.default_child
            ),
            resources=event_listener_template.find_resources(CfnRule.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            {
                'EventBusName': {
                    'Fn::Select': [
                        1,
                        {
                            'Fn::Split': [
                                '/',
                                {'Fn::Select': [5, {'Fn::Split': [':', {'Ref': 'DataEventBusArnParameterParameter'}]}]},
                            ]
                        },
                    ]
                },
                'EventPattern': {'detail-type': ['license.encumbranceLifted']},
                'State': 'ENABLED',
                'Targets': [
                    {
                        'Arn': {'Fn::GetAtt': [lifting_listener_queue_logical_id, 'Arn']},
                        'DeadLetterConfig': {'Arn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}},
                        'Id': 'Target0',
                    }
                ],
            },
            lifting_encumbrance_listener_event_bridge_rule,
        )

        # Verify event source mapping between SQS queue and Lambda function
        event_source_mapping = TestEventListenerStack.get_resource_properties_by_logical_id(
            event_listener_stack.get_logical_id(
                event_listener_stack.event_processors[
                    'LiftedLicenseEncumbranceListener'
                ].queue_processor.event_source_mapping.node.default_child
            ),
            resources=event_listener_template.find_resources(CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME),
        )
        self.assertEqual(
            {
                'BatchSize': 10,
                'EventSourceArn': {'Fn::GetAtt': [lifting_listener_queue_logical_id, 'Arn']},
                'FunctionName': {'Ref': lifting_encumbrance_handler_logical_id},
                'FunctionResponseTypes': ['ReportBatchItemFailures'],
                'MaximumBatchingWindowInSeconds': 15,
            },
            event_source_mapping,
        )

    def test_license_deactivation_listener_resources_created(self):
        """
        Test that the license deactivation listener lambda is added with a SQS queue
        and an event bridge event rule that listens for 'license.deactivation' detail types.
        """
        event_listener_stack = self.app.sandbox_backend_stage.event_listener_stack
        event_listener_template = Template.from_stack(event_listener_stack)

        # Verify the lambda function is created
        license_deactivation_handler_logical_id = event_listener_stack.get_logical_id(
            event_listener_stack.license_deactivation_event_listener.queue_processor.process_function.node.default_child
        )
        license_deactivation_handler = TestEventListenerStack.get_resource_properties_by_logical_id(
            license_deactivation_handler_logical_id,
            resources=event_listener_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            'handlers.license_deactivation_events.license_deactivation_listener',
            license_deactivation_handler['Handler'],
        )

        # Verify SQS queue is created for the license deactivation listener
        deactivation_listener_queue_logical_id = event_listener_stack.get_logical_id(
            event_listener_stack.license_deactivation_event_listener.queue_processor.queue.node.default_child
        )
        license_deactivation_listener_queue = TestEventListenerStack.get_resource_properties_by_logical_id(
            deactivation_listener_queue_logical_id,
            resources=event_listener_template.find_resources(CfnQueue.CFN_RESOURCE_TYPE_NAME),
        )

        dlq_logical_id = event_listener_stack.get_logical_id(
            event_listener_stack.license_deactivation_event_listener.queue_processor.dlq.node.default_child
        )

        # remove dynamic field
        del license_deactivation_listener_queue['KmsMasterKeyId']

        self.assertEqual(
            {
                'MessageRetentionPeriod': 43200,
                'RedrivePolicy': {'deadLetterTargetArn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}, 'maxReceiveCount': 3},
                'VisibilityTimeout': 300,
            },
            license_deactivation_listener_queue,
        )

        # Verify EventBridge rule is created with correct detail type
        license_deactivation_listener_event_bridge_rule = TestEventListenerStack.get_resource_properties_by_logical_id(
            event_listener_stack.get_logical_id(
                event_listener_stack.license_deactivation_event_listener.event_rule.node.default_child
            ),
            resources=event_listener_template.find_resources(CfnRule.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            {
                'EventBusName': {
                    'Fn::Select': [
                        1,
                        {
                            'Fn::Split': [
                                '/',
                                {'Fn::Select': [5, {'Fn::Split': [':', {'Ref': 'DataEventBusArnParameterParameter'}]}]},
                            ]
                        },
                    ]
                },
                'EventPattern': {'detail-type': ['license.deactivation']},
                'State': 'ENABLED',
                'Targets': [
                    {
                        'Arn': {'Fn::GetAtt': [deactivation_listener_queue_logical_id, 'Arn']},
                        'DeadLetterConfig': {'Arn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}},
                        'Id': 'Target0',
                    }
                ],
            },
            license_deactivation_listener_event_bridge_rule,
        )

        # Verify event source mapping between SQS queue and Lambda function
        event_source_mapping = TestEventListenerStack.get_resource_properties_by_logical_id(
            event_listener_stack.get_logical_id(
                event_listener_stack.license_deactivation_event_listener.queue_processor.event_source_mapping.node.default_child
            ),
            resources=event_listener_template.find_resources(CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME),
        )
        self.assertEqual(
            {
                'BatchSize': 10,
                'EventSourceArn': {'Fn::GetAtt': [deactivation_listener_queue_logical_id, 'Arn']},
                'FunctionName': {'Ref': license_deactivation_handler_logical_id},
                'FunctionResponseTypes': ['ReportBatchItemFailures'],
                'MaximumBatchingWindowInSeconds': 15,
            },
            event_source_mapping,
        )
