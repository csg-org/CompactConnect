import json
import re
from unittest import TestCase

from aws_cdk.assertions import Template
from aws_cdk.aws_lambda import CfnFunction

from tests.app.base import TstAppABC


def _generate_expected_secret_arn(compact: str) -> str:
    return (
        f'arn:aws:secretsmanager:us-east-1:000011112222:secret:compact-connect/env'
        f'/prod/compact/{compact}/credentials/payment-processor-??????'
    )


class TestTransactionMonitoring(TstAppABC, TestCase):
    """
    These tests verify that the transaction monitoring resources are configured as expected.

    When adding or modifying the transaction monitoring workflow definition, tests should be added to ensure that the
    steps are configured correctly.
    """

    @classmethod
    def get_context(cls):
        with open('cdk.json') as f:
            context = json.load(f)['context']

        # Suppresses lambda bundling for tests
        context['aws:cdk:bundling-stacks'] = []

        return context

    def remove_dynamic_tokens_numbers(self, definition: dict) -> dict:
        """
        Helper function to replace dynamic numbers from the tokens with static placeholders in a definition.

        Here is an example of a state machine definition that contains tokens:
        {'Next': 'TranscriberChoiceStep',
         'Parameters': {'MessageBody': {'input.$': '$', 'taskToken.$': '$$.Task.Token'},
                        'QueueUrl': '${Token[TOKEN.317]}'},
         'Resource': 'arn:${Token[AWS.Partition.8]}:states:::sqs:sendMessage.waitForTaskToken',
         'TimeoutSeconds': 1123200,
         'Type': 'Task'}

         Notice sometimes the token is embedded in a string, and sometimes it is a standalone value.
         We need to account for both cases here.

        the dynamic token numbers are removed from the string so the tests are stable.
        """
        # this matches the token pattern so we can replace the numbers
        token_pattern = re.compile(r'\$\{Token\[([^\]]+)\]\}')

        def replace_tokens(value):
            if isinstance(value, dict):
                return {k: replace_tokens(v) for k, v in value.items()}
            if isinstance(value, list):
                return [replace_tokens(v) for v in value]
            if isinstance(value, str):

                def strip_numbers(match):
                    token_content = match.group(1)
                    parts = token_content.split('.')
                    stripped_parts = [part for part in parts if not part.isdigit()]
                    return '${Token[' + '.'.join(stripped_parts) + ']}'

                return token_pattern.sub(strip_numbers, value)
            return value

        return replace_tokens(definition)

    def test_workflow_generate_process_transaction_history_lambda_with_permissions(self):
        transaction_monitoring_stack = self.app.prod_backend_pipeline_stack.prod_stage.transaction_monitoring_stack
        transaction_monitoring_stack_template = Template.from_stack(transaction_monitoring_stack)

        compacts = transaction_monitoring_stack.node.get_context('compacts')
        for compact in compacts:
            lambda_properties = self.get_resource_properties_by_logical_id(
                transaction_monitoring_stack.get_logical_id(
                    transaction_monitoring_stack.compact_state_machines[
                        compact
                    ].transaction_processor_handler.node.default_child
                ),
                transaction_monitoring_stack_template.find_resources(CfnFunction.CFN_RESOURCE_TYPE_NAME),
            )

            self.assertEqual('handlers.transaction_history.process_settled_transactions', lambda_properties['Handler'])

            handler_role_logical_id = transaction_monitoring_stack.get_logical_id(
                transaction_monitoring_stack.compact_state_machines[
                    compact
                ].transaction_processor_handler.role.node.default_child
            )
            # get the policy attached to the role using this match
            # "Roles": [
            #     {
            #         "Ref": "<role logical id>"
            #     }
            # ]
            policy = next(
                policy
                for policy_logical_id, policy in transaction_monitoring_stack_template.find_resources(
                    'AWS::IAM::Policy'
                ).items()
                if handler_role_logical_id in policy['Properties']['Roles'][0]['Ref']
            )

            # We need to ensure the lambda can only read the secret for its compact
            self.assertIn(
                {
                    'Action': 'secretsmanager:GetSecretValue',
                    'Effect': 'Allow',
                    'Resource': _generate_expected_secret_arn(compact),
                },
                policy['Properties']['PolicyDocument']['Statement'],
            )

    def test_workflow_generates_expected_process_transaction_history_lambda_invoke_step(self):
        aslp_transaction_history_proccessing_workflow = (
            self.app.prod_backend_pipeline_stack.prod_stage.transaction_monitoring_stack.compact_state_machines['aslp']
        )

        self.assertEqual(
            {
                'InputPath': '${Token[Payload]}',
                'Next': 'aslp-CheckProcessingStatus',
                'Parameters': {'FunctionName': '${Token[TOKEN]}', 'Payload.$': '$'},
                'Resource': 'arn:${Token[AWS.Partition]}:states:::lambda:invoke',
                'ResultPath': '$',
                'Retry': [
                    {
                        'BackoffRate': 2,
                        'ErrorEquals': [
                            'Lambda.ClientExecutionTimeoutException',
                            'Lambda.ServiceException',
                            'Lambda.AWSLambdaException',
                            'Lambda.SdkClientException',
                        ],
                        'IntervalSeconds': 2,
                        'MaxAttempts': 6,
                    }
                ],
                'TimeoutSeconds': 900,
                'Type': 'Task',
            },
            self.remove_dynamic_tokens_numbers(
                aslp_transaction_history_proccessing_workflow.processor_task.to_state_json()
            ),
        )

    def test_workflow_generates_expected_choice_step(self):
        aslp_transaction_history_proccessing_workflow = (
            self.app.prod_backend_pipeline_stack.prod_stage.transaction_monitoring_stack.compact_state_machines['aslp']
        )

        self.assertEqual(
            {
                'Choices': [
                    {
                        'Next': 'aslp-ProcessingComplete',
                        'StringEquals': 'COMPLETE',
                        'Variable': '$.Payload.status',
                    },
                    {
                        'Next': 'aslp-ProcessTransactionHistory',
                        'StringEquals': 'IN_PROGRESS',
                        'Variable': '$.Payload.status',
                    },
                    {
                        'Next': 'aslp-BatchFailureNotification',
                        'StringEquals': 'BATCH_FAILURE',
                        'Variable': '$.Payload.status',
                    },
                ],
                'Default': 'aslp-ProcessingFailed',
                'Type': 'Choice',
            },
            self.remove_dynamic_tokens_numbers(
                aslp_transaction_history_proccessing_workflow.check_status.to_state_json()
            ),
        )

    def test_workflow_generates_expected_batch_failure_notification_step(self):
        aslp_transaction_history_proccessing_workflow = (
            self.app.prod_backend_pipeline_stack.prod_stage.transaction_monitoring_stack.compact_state_machines['aslp']
        )

        self.assertEqual(
            {
                'Next': 'aslp-ProcessingComplete',
                'Parameters': {
                    'FunctionName': '${Token[TOKEN]}',
                    'Payload': {
                        'compact': 'aslp',
                        'recipientType': 'COMPACT_OPERATIONS_TEAM',
                        'template': 'transactionBatchSettlementFailure',
                    },
                },
                'Resource': 'arn:${Token[AWS.Partition]}:states:::lambda:invoke',
                'ResultPath': '$.notificationResult',
                'Retry': [
                    {
                        'BackoffRate': 2,
                        'ErrorEquals': [
                            'Lambda.ClientExecutionTimeoutException',
                            'Lambda.ServiceException',
                            'Lambda.AWSLambdaException',
                            'Lambda.SdkClientException',
                        ],
                        'IntervalSeconds': 2,
                        'MaxAttempts': 6,
                    }
                ],
                'TimeoutSeconds': 900,
                'Type': 'Task',
            },
            self.remove_dynamic_tokens_numbers(
                aslp_transaction_history_proccessing_workflow.email_notification_service_invoke_step.to_state_json()
            ),
        )
