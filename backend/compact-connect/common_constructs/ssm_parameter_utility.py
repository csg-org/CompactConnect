from aws_cdk.aws_events import EventBus
from aws_cdk.aws_ssm import StringParameter
from constructs import Construct

DATA_EVENT_BUS_ARN_SSM_PARAMETER_NAME = '/deployment/event-bridge/event-bus/data-event-bus-arn'


class SSMParameterUtility:
    """
    Utility class for SSM parameter operations.

    This class provides static methods for common SSM parameter operations,
    such as loading resources from SSM parameters to bypass cross-stack references.
    """

    @staticmethod
    def set_data_event_bus_arn_ssm_parameter(scope: Construct, data_event_bus: EventBus) -> StringParameter:
        return StringParameter(
            scope,
            'DataEventBusArnParameter',
            parameter_name=DATA_EVENT_BUS_ARN_SSM_PARAMETER_NAME,
            string_value=data_event_bus.event_bus_arn,
        )

    @staticmethod
    def load_data_event_bus_from_ssm_parameter(scope: Construct) -> EventBus:
        """
        Load the data event bus from an SSM parameter.

        This pattern breaks cross-stack references by storing and retrieving
        the event bus ARN in SSM Parameter Store rather than using a direct reference,
        which helps avoid issues with CloudFormation stack updates.

        :param scope: The CDK construct scope
        :return: The EventBus construct
        """
        data_event_bus_arn = StringParameter.from_string_parameter_name(
            scope,
            'DataEventBusArnParameter',
            string_parameter_name=DATA_EVENT_BUS_ARN_SSM_PARAMETER_NAME,
        )

        return EventBus.from_event_bus_arn(scope, 'DataEventBus', event_bus_arn=data_event_bus_arn.string_value)
