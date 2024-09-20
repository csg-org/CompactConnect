from __future__ import annotations

from aws_cdk.aws_cognito import UserPoolEmail
from aws_cdk.aws_kms import IKey
from constructs import Construct

from common_constructs.user_pool import UserPool
from stacks import persistent_stack as ps


class ProviderUsers(UserPool):
    """
    User pool for medical providers (aka Licensees)
    """
    def __init__(
            self, scope: Construct, construct_id: str, *,
            cognito_domain_prefix: str,
            environment_name: str,
            environment_context: dict,
            encryption_key: IKey,
            user_pool_email: UserPoolEmail,
            removal_policy,
            **kwargs
    ):
        super().__init__(
            scope, construct_id,
            cognito_domain_prefix=cognito_domain_prefix,
            environment_name=environment_name,
            encryption_key=encryption_key,
            removal_policy=removal_policy,
            email=user_pool_email,
            **kwargs
        )
        stack: ps.PersistentStack = ps.PersistentStack.of(self)

        callback_urls = []
        if stack.ui_domain_name is not None:
            callback_urls.append(f'https://{stack.ui_domain_name}/auth/callback')
        # This toggle will allow front-end devs to point their local UI at this environment's user pool to support
        # authenticated actions.
        if environment_context.get('allow_local_ui', False):
            local_ui_port = environment_context.get('local_ui_port', '3018')
            callback_urls.append(f'http://localhost:{local_ui_port}/auth/callback')
        if not callback_urls:
            raise ValueError(
                "This app requires a callback url for its authentication path. Either provide 'domain_name' or set "
                "'allow_local_ui' to true in this environment's context.")

        # Create an app client to allow the front-end to authenticate.
        self.ui_client = self.add_ui_client(callback_urls=callback_urls)
