import os

from aws_cdk.aws_cognito import StringAttribute, ResourceServerScope, UserPoolOperation, LambdaVersion
from aws_cdk.aws_kms import IKey
from constructs import Construct

from common_constructs.python_function import PythonFunction
from common_constructs.user_pool import UserPool


class BoardUsers(UserPool):
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
            custom_attributes={
                'jurisdiction': StringAttribute(
                    min_len=2,
                    max_len=4,
                    mutable=False
                ),
                'compact': StringAttribute(
                    min_len=2,
                    max_len=20
                )
            },
            **kwargs
        )

        self._add_resource_servers()
        self._add_scope_customization()
        # Do not allow resource server scopes via the client - they are assigned via token customization
        # to allow for user attribute-based access
        self.ui_client = self.add_ui_client()

    def _add_resource_servers(self):
        """
        Add scopes for all compact/jurisdictions
        """
        self.scopes = {
            jurisdiction: ResourceServerScope(
                scope_name=jurisdiction,
                scope_description=f'Write access for {jurisdiction}'
            )
            for jurisdiction in self.node.get_context('jurisdictions')
        }
        self.resource_servers = {
            compact: self.add_resource_server(
                f'LicenseData-{compact}',
                identifier=compact,
                scopes=list(self.scopes.values())
            )
            for compact in self.node.get_context('compacts')
        }

    def _add_scope_customization(self):
        """
        Add scopes to access tokens based on compact/jurisdiction
        """
        scope_customization_handler = PythonFunction(
            self, 'ScopeCustomizationHandler',
            entry=os.path.join('lambdas', 'board-user-pre-token'),
            index='main.py',
            handler='customize_scopes',
            environment={
                'DEBUG': 'true'
            }
        )
        self.add_trigger(
            UserPoolOperation.PRE_TOKEN_GENERATION_CONFIG,
            scope_customization_handler,
            lambda_version=LambdaVersion.V2_0
        )
