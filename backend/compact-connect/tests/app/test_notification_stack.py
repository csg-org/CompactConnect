import json
from unittest import TestCase

from aws_cdk.assertions import Template
from aws_cdk.aws_events import CfnRule
from aws_cdk.aws_lambda import CfnEventSourceMapping, CfnFunction
from aws_cdk.aws_sqs import CfnQueue

from tests.app.base import TstAppABC


class TestNotificationStack(TstAppABC, TestCase):
    """
    Test cases for the NotificationStack to ensure proper resource configuration
    for handling notification events that require SES integration.
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

    def test_privilege_purchase_notification_resources_created(self):
        """
        Test that the privilege purchase notification lambda is added with a SQS queue
        and an event bridge event rule that listens for 'privilege.purchase' detail types.
        """
        notification_stack = self.app.sandbox_backend_stage.notification_stack
        notification_template = Template.from_stack(notification_stack)

        # Verify the lambda function is created
        privilege_purchase_handler_logical_id = notification_stack.get_logical_id(
            notification_stack.privilege_purchase_processor.process_function.node.default_child
        )
        privilege_purchase_handler = TestNotificationStack.get_resource_properties_by_logical_id(
            privilege_purchase_handler_logical_id,
            resources=notification_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            'handlers.privileges.privilege_purchase_message_handler', privilege_purchase_handler['Handler']
        )

        # Verify SQS queue is created for the privilege purchase processor
        privilege_purchase_queue_logical_id = notification_stack.get_logical_id(
            notification_stack.privilege_purchase_processor.queue.node.default_child
        )
        privilege_purchase_queue = TestNotificationStack.get_resource_properties_by_logical_id(
            privilege_purchase_queue_logical_id,
            resources=notification_template.find_resources(CfnQueue.CFN_RESOURCE_TYPE_NAME),
        )

        dlq_logical_id = notification_stack.get_logical_id(
            notification_stack.privilege_purchase_processor.dlq.node.default_child
        )

        # remove dynamic field
        del privilege_purchase_queue['KmsMasterKeyId']

        self.assertEqual(
            {
                'MessageRetentionPeriod': 43200,
                'RedrivePolicy': {'deadLetterTargetArn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}, 'maxReceiveCount': 3},
                'VisibilityTimeout': 300,
            },
            privilege_purchase_queue,
        )

        # Verify EventBridge rule is created with correct detail type
        privilege_purchase_rule = TestNotificationStack.get_resource_properties_by_logical_id(
            notification_stack.get_logical_id(notification_stack.privilege_purchase_rule.node.default_child),
            resources=notification_template.find_resources(CfnRule.CFN_RESOURCE_TYPE_NAME),
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
                'EventPattern': {'detail-type': ['privilege.purchase']},
                'State': 'ENABLED',
                'Targets': [
                    {
                        'Arn': {'Fn::GetAtt': [privilege_purchase_queue_logical_id, 'Arn']},
                        'DeadLetterConfig': {'Arn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}},
                        'Id': 'Target0',
                    }
                ],
            },
            privilege_purchase_rule,
        )

        # Verify event source mapping between SQS queue and Lambda function
        event_source_mapping = TestNotificationStack.get_resource_properties_by_logical_id(
            notification_stack.get_logical_id(
                notification_stack.privilege_purchase_processor.event_source_mapping.node.default_child
            ),
            resources=notification_template.find_resources(CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME),
        )
        self.assertEqual(
            {
                'BatchSize': 10,
                'EventSourceArn': {'Fn::GetAtt': [privilege_purchase_queue_logical_id, 'Arn']},
                'FunctionName': {'Ref': privilege_purchase_handler_logical_id},
                'FunctionResponseTypes': ['ReportBatchItemFailures'],
                'MaximumBatchingWindowInSeconds': 15,
            },
            event_source_mapping,
        )

    def test_license_encumbrance_notification_listener_resources_created(self):
        """
        Test that the license encumbrance notification listener lambda is added with a SQS queue
        and an event bridge event rule that listens for 'license.encumbrance' detail types.
        """
        notification_stack = self.app.sandbox_backend_stage.notification_stack
        notification_template = Template.from_stack(notification_stack)

        # Verify the lambda function is created
        license_encumbrance_notification_handler_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'LicenseEncumbranceNotificationListener'
            ].queue_processor.process_function.node.default_child
        )
        license_encumbrance_notification_handler = TestNotificationStack.get_resource_properties_by_logical_id(
            license_encumbrance_notification_handler_logical_id,
            resources=notification_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            'handlers.encumbrance_events.license_encumbrance_notification_listener',
            license_encumbrance_notification_handler['Handler'],
        )

        # Verify SQS queue is created for the license encumbrance notification listener
        notification_listener_queue_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'LicenseEncumbranceNotificationListener'
            ].queue_processor.queue.node.default_child
        )
        license_encumbrance_notification_listener_queue = TestNotificationStack.get_resource_properties_by_logical_id(
            notification_listener_queue_logical_id,
            resources=notification_template.find_resources(CfnQueue.CFN_RESOURCE_TYPE_NAME),
        )

        dlq_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'LicenseEncumbranceNotificationListener'
            ].queue_processor.dlq.node.default_child
        )

        # remove dynamic field
        del license_encumbrance_notification_listener_queue['KmsMasterKeyId']

        self.assertEqual(
            {
                'MessageRetentionPeriod': 43200,
                'RedrivePolicy': {'deadLetterTargetArn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}, 'maxReceiveCount': 3},
                'VisibilityTimeout': 300,
            },
            license_encumbrance_notification_listener_queue,
        )

        # Verify EventBridge rule is created with correct detail type
        license_encumbrance_notification_listener_event_bridge_rule = (
            TestNotificationStack.get_resource_properties_by_logical_id(
                notification_stack.get_logical_id(
                    notification_stack.event_processors[
                        'LicenseEncumbranceNotificationListener'
                    ].event_rule.node.default_child
                ),
                resources=notification_template.find_resources(CfnRule.CFN_RESOURCE_TYPE_NAME),
            )
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
                        'Arn': {'Fn::GetAtt': [notification_listener_queue_logical_id, 'Arn']},
                        'DeadLetterConfig': {'Arn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}},
                        'Id': 'Target0',
                    }
                ],
            },
            license_encumbrance_notification_listener_event_bridge_rule,
        )

        # Verify event source mapping between SQS queue and Lambda function
        event_source_mapping = TestNotificationStack.get_resource_properties_by_logical_id(
            notification_stack.get_logical_id(
                notification_stack.event_processors[
                    'LicenseEncumbranceNotificationListener'
                ].queue_processor.event_source_mapping.node.default_child
            ),
            resources=notification_template.find_resources(CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME),
        )
        self.assertEqual(
            {
                'BatchSize': 10,
                'EventSourceArn': {'Fn::GetAtt': [notification_listener_queue_logical_id, 'Arn']},
                'FunctionName': {'Ref': license_encumbrance_notification_handler_logical_id},
                'FunctionResponseTypes': ['ReportBatchItemFailures'],
                'MaximumBatchingWindowInSeconds': 15,
            },
            event_source_mapping,
        )

    def test_license_encumbrance_lifting_notification_listener_resources_created(self):
        """
        Test that the license encumbrance lifting notification listener lambda is added with a SQS queue
        and an event bridge event rule that listens for 'license.encumbranceLifted' detail types.
        """
        notification_stack = self.app.sandbox_backend_stage.notification_stack
        notification_template = Template.from_stack(notification_stack)

        # Verify the lambda function is created
        license_encumbrance_lifting_notification_handler_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'LicenseEncumbranceLiftingNotificationListener'
            ].queue_processor.process_function.node.default_child
        )
        license_encumbrance_lifting_notification_handler = TestNotificationStack.get_resource_properties_by_logical_id(
            license_encumbrance_lifting_notification_handler_logical_id,
            resources=notification_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            'handlers.encumbrance_events.license_encumbrance_lifting_notification_listener',
            license_encumbrance_lifting_notification_handler['Handler'],
        )

        # Verify SQS queue is created for the license encumbrance lifting notification listener
        lifting_notification_listener_queue_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'LicenseEncumbranceLiftingNotificationListener'
            ].queue_processor.queue.node.default_child
        )
        license_encumbrance_lifting_notification_listener_queue = (
            TestNotificationStack.get_resource_properties_by_logical_id(
                lifting_notification_listener_queue_logical_id,
                resources=notification_template.find_resources(CfnQueue.CFN_RESOURCE_TYPE_NAME),
            )
        )

        dlq_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'LicenseEncumbranceLiftingNotificationListener'
            ].queue_processor.dlq.node.default_child
        )

        # remove dynamic field
        del license_encumbrance_lifting_notification_listener_queue['KmsMasterKeyId']

        self.assertEqual(
            {
                'MessageRetentionPeriod': 43200,
                'RedrivePolicy': {'deadLetterTargetArn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}, 'maxReceiveCount': 3},
                'VisibilityTimeout': 300,
            },
            license_encumbrance_lifting_notification_listener_queue,
        )

        # Verify EventBridge rule is created with correct detail type
        license_encumbrance_lifting_notification_listener_event_bridge_rule = (
            TestNotificationStack.get_resource_properties_by_logical_id(
                notification_stack.get_logical_id(
                    notification_stack.event_processors[
                        'LicenseEncumbranceLiftingNotificationListener'
                    ].event_rule.node.default_child
                ),
                resources=notification_template.find_resources(CfnRule.CFN_RESOURCE_TYPE_NAME),
            )
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
                        'Arn': {'Fn::GetAtt': [lifting_notification_listener_queue_logical_id, 'Arn']},
                        'DeadLetterConfig': {'Arn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}},
                        'Id': 'Target0',
                    }
                ],
            },
            license_encumbrance_lifting_notification_listener_event_bridge_rule,
        )

        # Verify event source mapping between SQS queue and Lambda function
        event_source_mapping = TestNotificationStack.get_resource_properties_by_logical_id(
            notification_stack.get_logical_id(
                notification_stack.event_processors[
                    'LicenseEncumbranceLiftingNotificationListener'
                ].queue_processor.event_source_mapping.node.default_child
            ),
            resources=notification_template.find_resources(CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME),
        )
        self.assertEqual(
            {
                'BatchSize': 10,
                'EventSourceArn': {'Fn::GetAtt': [lifting_notification_listener_queue_logical_id, 'Arn']},
                'FunctionName': {'Ref': license_encumbrance_lifting_notification_handler_logical_id},
                'FunctionResponseTypes': ['ReportBatchItemFailures'],
                'MaximumBatchingWindowInSeconds': 15,
            },
            event_source_mapping,
        )

    def test_privilege_encumbrance_notification_listener_resources_created(self):
        """
        Test that the privilege encumbrance notification listener lambda is added with a SQS queue
        and an event bridge event rule that listens for 'privilege.encumbrance' detail types.
        """
        notification_stack = self.app.sandbox_backend_stage.notification_stack
        notification_template = Template.from_stack(notification_stack)

        # Verify the lambda function is created
        privilege_encumbrance_handler_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'PrivilegeEncumbranceNotificationListener'
            ].queue_processor.process_function.node.default_child
        )
        privilege_encumbrance_handler = TestNotificationStack.get_resource_properties_by_logical_id(
            privilege_encumbrance_handler_logical_id,
            resources=notification_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            'handlers.encumbrance_events.privilege_encumbrance_notification_listener',
            privilege_encumbrance_handler['Handler'],
        )

        # Verify SQS queue is created for the privilege encumbrance notification listener
        listener_queue_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'PrivilegeEncumbranceNotificationListener'
            ].queue_processor.queue.node.default_child
        )
        privilege_encumbrance_listener_queue = TestNotificationStack.get_resource_properties_by_logical_id(
            listener_queue_logical_id, resources=notification_template.find_resources(CfnQueue.CFN_RESOURCE_TYPE_NAME)
        )

        dlq_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'PrivilegeEncumbranceNotificationListener'
            ].queue_processor.dlq.node.default_child
        )

        # remove dynamic field
        del privilege_encumbrance_listener_queue['KmsMasterKeyId']

        self.assertEqual(
            {
                'MessageRetentionPeriod': 43200,
                'RedrivePolicy': {'deadLetterTargetArn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}, 'maxReceiveCount': 3},
                'VisibilityTimeout': 300,
            },
            privilege_encumbrance_listener_queue,
        )

        # Verify EventBridge rule is created with correct detail type
        privilege_encumbrance_listener_event_bridge_rule = TestNotificationStack.get_resource_properties_by_logical_id(
            notification_stack.get_logical_id(
                notification_stack.event_processors[
                    'PrivilegeEncumbranceNotificationListener'
                ].event_rule.node.default_child
            ),
            resources=notification_template.find_resources(CfnRule.CFN_RESOURCE_TYPE_NAME),
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
                'EventPattern': {'detail-type': ['privilege.encumbrance']},
                'State': 'ENABLED',
                'Targets': [
                    {
                        'Arn': {'Fn::GetAtt': [listener_queue_logical_id, 'Arn']},
                        'DeadLetterConfig': {'Arn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}},
                        'Id': 'Target0',
                    }
                ],
            },
            privilege_encumbrance_listener_event_bridge_rule,
        )

        # Verify event source mapping between SQS queue and Lambda function
        event_source_mapping = TestNotificationStack.get_resource_properties_by_logical_id(
            notification_stack.get_logical_id(
                notification_stack.event_processors[
                    'PrivilegeEncumbranceNotificationListener'
                ].queue_processor.event_source_mapping.node.default_child
            ),
            resources=notification_template.find_resources(CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME),
        )
        self.assertEqual(
            {
                'BatchSize': 10,
                'EventSourceArn': {'Fn::GetAtt': [listener_queue_logical_id, 'Arn']},
                'FunctionName': {'Ref': privilege_encumbrance_handler_logical_id},
                'FunctionResponseTypes': ['ReportBatchItemFailures'],
                'MaximumBatchingWindowInSeconds': 15,
            },
            event_source_mapping,
        )

    def test_privilege_encumbrance_lifting_notification_listener_resources_created(self):
        """
        Test that the privilege encumbrance lifting notification listener lambda is added with a SQS queue
        and an event bridge event rule that listens for 'privilege.encumbranceLifted' detail types.
        """
        notification_stack = self.app.sandbox_backend_stage.notification_stack
        notification_template = Template.from_stack(notification_stack)

        # Verify the lambda function is created
        privilege_encumbrance_lifting_handler_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'PrivilegeEncumbranceLiftingNotificationListener'
            ].queue_processor.process_function.node.default_child
        )
        privilege_encumbrance_lifting_handler = TestNotificationStack.get_resource_properties_by_logical_id(
            privilege_encumbrance_lifting_handler_logical_id,
            resources=notification_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
        )

        self.assertEqual(
            'handlers.encumbrance_events.privilege_encumbrance_lifting_notification_listener',
            privilege_encumbrance_lifting_handler['Handler'],
        )

        # Verify SQS queue is created for the privilege encumbrance lifting notification listener
        lifting_listener_queue_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'PrivilegeEncumbranceLiftingNotificationListener'
            ].queue_processor.queue.node.default_child
        )
        privilege_encumbrance_lifting_listener_queue = TestNotificationStack.get_resource_properties_by_logical_id(
            lifting_listener_queue_logical_id,
            resources=notification_template.find_resources(CfnQueue.CFN_RESOURCE_TYPE_NAME),
        )

        dlq_logical_id = notification_stack.get_logical_id(
            notification_stack.event_processors[
                'PrivilegeEncumbranceLiftingNotificationListener'
            ].queue_processor.dlq.node.default_child
        )

        # remove dynamic field
        del privilege_encumbrance_lifting_listener_queue['KmsMasterKeyId']

        self.assertEqual(
            {
                'MessageRetentionPeriod': 43200,
                'RedrivePolicy': {'deadLetterTargetArn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}, 'maxReceiveCount': 3},
                'VisibilityTimeout': 300,
            },
            privilege_encumbrance_lifting_listener_queue,
        )

        # Verify EventBridge rule is created with correct detail type
        privilege_encumbrance_lifting_listener_event_bridge_rule = (
            TestNotificationStack.get_resource_properties_by_logical_id(
                notification_stack.get_logical_id(
                    notification_stack.event_processors[
                        'PrivilegeEncumbranceLiftingNotificationListener'
                    ].event_rule.node.default_child
                ),
                resources=notification_template.find_resources(CfnRule.CFN_RESOURCE_TYPE_NAME),
            )
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
                'EventPattern': {'detail-type': ['privilege.encumbranceLifted']},
                'State': 'ENABLED',
                'Targets': [
                    {
                        'Arn': {'Fn::GetAtt': [lifting_listener_queue_logical_id, 'Arn']},
                        'DeadLetterConfig': {'Arn': {'Fn::GetAtt': [dlq_logical_id, 'Arn']}},
                        'Id': 'Target0',
                    }
                ],
            },
            privilege_encumbrance_lifting_listener_event_bridge_rule,
        )

        # Verify event source mapping between SQS queue and Lambda function
        event_source_mapping = TestNotificationStack.get_resource_properties_by_logical_id(
            notification_stack.get_logical_id(
                notification_stack.event_processors[
                    'PrivilegeEncumbranceLiftingNotificationListener'
                ].queue_processor.event_source_mapping.node.default_child
            ),
            resources=notification_template.find_resources(CfnEventSourceMapping.CFN_RESOURCE_TYPE_NAME),
        )
        self.assertEqual(
            {
                'BatchSize': 10,
                'EventSourceArn': {'Fn::GetAtt': [lifting_listener_queue_logical_id, 'Arn']},
                'FunctionName': {'Ref': privilege_encumbrance_lifting_handler_logical_id},
                'FunctionResponseTypes': ['ReportBatchItemFailures'],
                'MaximumBatchingWindowInSeconds': 15,
            },
            event_source_mapping,
        )
