from aws_cdk import RemovalPolicy
from common_constructs.stack import AppStack
from constructs import Construct

from stacks import persistent_stack as ps
from stacks.event_state_stack.event_state_table import EventStateTable


class EventStateStack(AppStack):
    """
    Stack for event processing state management.

    This stack contains resources for tracking the state of event-driven operations,
    particularly for maintaining idempotency across SQS message retries.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        persistent_stack: ps.PersistentStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)

        # Use same removal policy as persistent stack resources
        removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY

        self.event_state_table = EventStateTable(
            self,
            'EventStateTable',
            encryption_key=persistent_stack.shared_encryption_key,
            removal_policy=removal_policy,
        )
