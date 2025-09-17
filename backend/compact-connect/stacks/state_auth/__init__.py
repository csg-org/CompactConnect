from aws_cdk import RemovalPolicy
from constructs import Construct

from common_constructs.stack import AppStack
from stacks.persistent_stack import PersistentStack
from stacks.state_auth.state_auth_users import StateAuthUsers


class StateAuthStack(AppStack):
    """
    Stack containing the state API authentication resources (machine-to-machine user pool).

    This stack is separate from the persistent stack to allow for easier management
    and reduce risk of cognito putting our persistent stack in an irrecoverable state.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        app_name: str,
        environment_name: str,
        environment_context: dict,
        persistent_stack: PersistentStack,
        **kwargs,
    ) -> None:
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )

        self.persistent_stack = persistent_stack

        # If we delete this stack, retain the resource (orphan but prevent data loss) or destroy it (clean up)?
        removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY

        # Set up state auth domain prefix
        state_auth_prefix = f'{app_name}-state-auth'
        state_auth_prefix = (
            state_auth_prefix if environment_name == 'prod' else f'{state_auth_prefix}-{environment_name}'
        )

        # Create the state auth user pool for machine-to-machine authentication
        self.state_auth_users = StateAuthUsers(
            self,
            'StateAuthUsers',
            cognito_domain_prefix=state_auth_prefix,
            persistent_stack=persistent_stack,
            removal_policy=removal_policy,
        )
