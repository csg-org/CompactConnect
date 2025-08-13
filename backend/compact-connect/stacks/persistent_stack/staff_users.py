from __future__ import annotations

import json

from aws_cdk import Duration
from aws_cdk.aws_cognito import (
    ClientAttributes,
    LambdaVersion,
    SignInAliases,
    StandardAttribute,
    StandardAttributes,
    UserPoolEmail,
    UserPoolOperation,
)
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from common_constructs.cognito_user_backup import CognitoUserBackup
from common_constructs.nodejs_function import NodejsFunction
from common_constructs.python_function import PythonFunction
from common_constructs.resource_scope_mixin import ResourceScopeMixin
from common_constructs.user_pool import UserPool
from constructs import Construct

from stacks import persistent_stack as ps
from stacks.backup_infrastructure_stack import BackupInfrastructureStack
from stacks.persistent_stack.users_table import UsersTable


class StaffUsers(UserPool, ResourceScopeMixin):
    """User pool for Compact, Board, and CSG staff"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cognito_domain_prefix: str | None,
        environment_name: str,
        environment_context: dict,
        encryption_key: IKey,
        user_pool_email: UserPoolEmail,
        removal_policy,
        backup_infrastructure_stack: BackupInfrastructureStack | None,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            cognito_domain_prefix=cognito_domain_prefix,
            environment_name=environment_name,
            encryption_key=encryption_key,
            sign_in_aliases=SignInAliases(email=True, username=False),
            standard_attributes=StandardAttributes(email=StandardAttribute(required=True, mutable=True)),
            removal_policy=removal_policy,
            email=user_pool_email,
            **kwargs,
        )
        stack: ps.PersistentStack = ps.PersistentStack.of(self)

        self.user_table = UsersTable(
            self,
            'UsersTable',
            encryption_key=encryption_key,
            removal_policy=removal_policy,
            backup_infrastructure_stack=backup_infrastructure_stack,
            environment_context=environment_context,
        )
        self._add_resource_servers(stack=stack)
        self._add_scope_customization(stack=stack)
        self._add_custom_message_lambda(stack=stack)

        # Do not allow resource server scopes via the client - they are assigned via token customization
        # to allow for user attribute-based access
        self.ui_client = self.add_ui_client(
            ui_domain_name=stack.ui_domain_name,
            environment_context=environment_context,
            # We have to provide one True value or CFn will make every attribute writeable
            write_attributes=ClientAttributes().with_standard_attributes(email=True),
            # We want to limit the attributes that this app can read and write so only email is visible.
            read_attributes=ClientAttributes().with_standard_attributes(email=True),
        )

        # Check if backups are enabled for this environment
        backup_enabled = environment_context['backup_enabled']

        if backup_enabled and backup_infrastructure_stack is not None:
            # Set up Cognito backup system for this user pool
            self.backup_system = CognitoUserBackup(
                self,
                'StaffUserBackup',
                user_pool_id=self.user_pool_id,
                access_logs_bucket=stack.access_logs_bucket,
                encryption_key=encryption_key,
                removal_policy=removal_policy,
                backup_infrastructure_stack=backup_infrastructure_stack,
                alarm_topic=stack.alarm_topic,
            )
        else:
            # Create placeholder attribute for disabled state
            self.backup_system = None

    def _add_scope_customization(self, stack: ps.PersistentStack):
        """Add scopes to access tokens based on the Users table"""
        compacts = self.node.get_context('compacts')
        jurisdictions = self.node.get_context('jurisdictions')

        scope_customization_handler = PythonFunction(
            self,
            'ScopeCustomizationHandler',
            description='Auth scope customization handler',
            lambda_dir='staff-user-pre-token',
            index='main.py',
            handler='customize_scopes',
            alarm_topic=stack.alarm_topic,
            environment={
                'DEBUG': 'true',
                'USERS_TABLE_NAME': self.user_table.table_name,
                'COMPACTS': json.dumps(compacts),
                'JURISDICTIONS': json.dumps(jurisdictions),
                **stack.common_env_vars,
            },
        )
        self.user_table.grant_read_write_data(scope_customization_handler)

        NagSuppressions.add_resource_suppressions(
            scope_customization_handler,
            apply_to_children=True,
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                    This lambda role policy contains wildcards in its statements, but all of its actions
                     are limited specifically to the actions and the Table it needs read access to.
                     """,
                },
            ],
        )
        self.add_trigger(
            UserPoolOperation.PRE_TOKEN_GENERATION_CONFIG,
            scope_customization_handler,
            lambda_version=LambdaVersion.V2_0,
        )

    def _add_custom_message_lambda(self, stack: ps.PersistentStack):
        """Add a custom message lambda to the user pool"""

        from_address = 'NONE'
        if stack.hosted_zone:
            from_address = f'noreply@{stack.user_email_notifications.email_identity.email_identity_name}'

        self.custom_message_lambda = NodejsFunction(
            self,
            'CustomMessageLambda',
            description='Cognito custom message lambda',
            lambda_dir='cognito-emails',
            handler='customMessage',
            timeout=Duration.minutes(1),
            environment={
                'FROM_ADDRESS': from_address,
                'COMPACT_CONFIGURATION_TABLE_NAME': stack.compact_configuration_table.table_name,
                'UI_BASE_PATH_URL': stack.get_ui_base_path_url(),
                'USER_POOL_TYPE': 'staff',
                **stack.common_env_vars,
            },
        )

        self.add_trigger(
            UserPoolOperation.CUSTOM_MESSAGE,
            self.custom_message_lambda,
        )
