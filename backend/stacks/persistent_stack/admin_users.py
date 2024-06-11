from aws_cdk.aws_cognito import ResourceServerScope, OAuthScope
from aws_cdk.aws_kms import IKey
from constructs import Construct

from common_constructs.user_pool import UserPool


class AdminUsers(UserPool):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            cognito_domain_prefix: str,
            environment_name: str,
            encryption_key: IKey,
            removal_policy,
            **kwargs
    ):
        super().__init__(
            scope, construct_id,
            cognito_domain_prefix=cognito_domain_prefix,
            environment_name=environment_name,
            encryption_key=encryption_key,
            removal_policy=removal_policy,
            **kwargs
        )

        self._add_resource_server()
        self.ui_client = self.add_ui_client(
            ui_scopes=[
                OAuthScope.OPENID,
                OAuthScope.PROFILE,
                OAuthScope.EMAIL,
                OAuthScope.COGNITO_ADMIN,
                OAuthScope.resource_server(self.resource_server, self.scope)
            ]
        )

        # We will create some admins to get access started for the app and for support
        # for email in compact_context.get('admins', []):
        #     user = CfnUserPoolUser(
        #         self, f'Admin{email}',
        #         user_pool_id=self.user_pool_id,
        #         username=email,
        #         user_attributes=[
        #             CfnUserPoolUser.AttributeTypeProperty(
        #                 name='email',
        #                 value=email
        #             )
        #         ],
        #         desired_delivery_mediums=['EMAIL']
        #     )
        #     user.add_dependency(self.node.default_child)

    def _add_resource_server(self):
        """
        Add scopes for all compact/jurisdictions
        """
        self.scope = ResourceServerScope(scope_name='*', scope_description='Full administrator access')
        self.resource_server = self.add_resource_server(
            'Admins',
            identifier='admin',
            scopes=[self.scope]
        )
