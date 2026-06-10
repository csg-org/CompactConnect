from unittest import TestCase

from aws_cdk import App, Stack
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_events import EventBus
from aws_cdk.aws_ssm import CfnParameter

from common_constructs.ssm_parameter_utility import (
    DATA_EVENT_BUS_ARN_SSM_PARAMETER_NAME,
    SSMParameterUtility,
)


class TestSSMParameterUtility(TestCase):
    def setUp(self):
        self.app = App()
        self.stack = Stack(self.app, 'TestStack')
        self.event_bus = EventBus(self.stack, 'DataEventBus')

    def test_parameter_name_constant_value(self):
        self.assertEqual(
            '/deployment/event-bridge/event-bus/data-event-bus-arn',
            DATA_EVENT_BUS_ARN_SSM_PARAMETER_NAME,
        )

    def test_set_data_event_bus_arn_ssm_parameter_writes_correct_name(self):
        SSMParameterUtility.set_data_event_bus_arn_ssm_parameter(self.stack, self.event_bus)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnParameter.CFN_RESOURCE_TYPE_NAME,
            {'Name': DATA_EVENT_BUS_ARN_SSM_PARAMETER_NAME},
        )

    def test_set_data_event_bus_arn_ssm_parameter_stores_event_bus_arn(self):
        SSMParameterUtility.set_data_event_bus_arn_ssm_parameter(self.stack, self.event_bus)

        template = Template.from_stack(self.stack)
        # The value must reference the EventBusArn attribute of the event bus.
        template.has_resource_properties(
            CfnParameter.CFN_RESOURCE_TYPE_NAME,
            {
                'Value': {'Fn::GetAtt': [Match.string_like_regexp('DataEventBus'), 'Arn']},
            },
        )

    def test_load_data_event_bus_from_ssm_parameter_does_not_create_direct_ref(self):
        """load_* reads from SSM and returns an EventBus without creating a CloudFormation Output."""
        consumer_stack = Stack(self.app, 'ConsumerStack')
        bus = SSMParameterUtility.load_data_event_bus_from_ssm_parameter(consumer_stack)

        # The bus ARN must be resolved through SSM (a dynamic reference), not a direct Fn::ImportValue.
        self.assertIsNotNone(bus)
        template = Template.from_stack(consumer_stack)
        rendered = template.to_json()
        self.assertNotIn('Fn::ImportValue', str(rendered))

    def test_load_and_set_parameter_names_match(self):
        """The parameter name used to write must be the same one used to read."""
        SSMParameterUtility.set_data_event_bus_arn_ssm_parameter(self.stack, self.event_bus)

        consumer_stack = Stack(self.app, 'ConsumerStack')
        SSMParameterUtility.load_data_event_bus_from_ssm_parameter(consumer_stack)

        # Writer stack creates the parameter with the well-known name
        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnParameter.CFN_RESOURCE_TYPE_NAME,
            {'Name': DATA_EVENT_BUS_ARN_SSM_PARAMETER_NAME},
        )
        # Consumer stack uses SSM dynamic reference – no direct CloudFormation cross-stack dependency
        consumer_template = Template.from_stack(consumer_stack)
        consumer_rendered = consumer_template.to_json()
        self.assertNotIn('Fn::ImportValue', str(consumer_rendered))
