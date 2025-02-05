from __future__ import annotations

import os

from aws_cdk.aws_apigateway import (
    AuthorizationType,
    LambdaIntegration,
    MethodResponse,
    Resource,
)
from aws_cdk.aws_cognito import IUserPool
from aws_cdk.aws_dynamodb import ITable
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction

# Importing module level to allow lazy loading for typing
from stacks import persistent_stack as ps

from .. import cc_api
from .api_model import ApiModel


class StaffUsers:
    def __init__(
        self,
        *,
        admin_resource: Resource,
        self_resource: Resource,
        admin_scopes: list[str],
        persistent_stack: ps.PersistentStack,
        api_model: ApiModel,
    ):
        super().__init__()

        self.stack: ps.PersistentStack = ps.PersistentStack.of(admin_resource)
        self.admin_resource = admin_resource
        self.api: cc_api.CCApi = admin_resource.api
        self.api_model = api_model

        self.log_groups = []
        env_vars = {
            **self.stack.common_env_vars,
            'USER_POOL_ID': persistent_stack.staff_users.user_pool_id,
            'USERS_TABLE_NAME': persistent_stack.staff_users.user_table.table_name,
            'FAM_GIV_INDEX_NAME': persistent_stack.staff_users.user_table.family_given_index_name,
        }

        # <base-url>/
        self._add_get_users(self.admin_resource, admin_scopes, env_vars=env_vars, persistent_stack=persistent_stack)
        self._add_post_user(self.admin_resource, admin_scopes, env_vars=env_vars, persistent_stack=persistent_stack)

        self.user_id_resource = self.admin_resource.add_resource('{userId}')
        # <base-url>/{userId}
        self._add_get_user(self.user_id_resource, admin_scopes, env_vars=env_vars, persistent_stack=persistent_stack)
        self._add_patch_user(self.user_id_resource, admin_scopes, env_vars=env_vars, persistent_stack=persistent_stack)
        self._add_delete_user(self.user_id_resource, admin_scopes, env_vars=env_vars, persistent_stack=persistent_stack)

        # <base-url>/{userId}/reinvite
        self.reinvite_resource = self.user_id_resource.add_resource('reinvite')
        self._add_reinvite_user(
            self.reinvite_resource, admin_scopes, env_vars=env_vars, persistent_stack=persistent_stack
        )

        self.me_resource = self_resource.add_resource('me')
        # <base-url>/me
        profile_scopes = ['profile']
        self._add_get_me(self.me_resource, profile_scopes, env_vars=env_vars, persistent_stack=persistent_stack)
        self._add_patch_me(self.me_resource, profile_scopes, env_vars=env_vars, persistent_stack=persistent_stack)

        self.api.log_groups.extend(self.log_groups)

    def _add_get_me(
        self,
        me_resource: Resource,
        scopes: list[str],
        env_vars: dict,
        persistent_stack: ps.PersistentStack,
    ):
        get_me_handler = self._get_me_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
        )

        # Add the GET method to the me_resource
        me_resource.add_method(
            'GET',
            integration=LambdaIntegration(get_me_handler),
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_staff_user_me_model},
                    response_parameters={'method.response.header.Access-Control-Allow-Origin': True},
                ),
                MethodResponse(
                    status_code='404',
                    response_models={
                        'application/json': self.api_model.message_response_model,
                    },
                ),
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes,
        )

    def _get_me_handler(self, env_vars: dict, data_encryption_key: IKey, user_table: ITable):
        handler = PythonFunction(
            self.stack,
            'GetMeStaffUserHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'me.py'),
            handler='get_me',
            environment=env_vars,
        )
        data_encryption_key.grant_decrypt(handler)
        user_table.grant_read_data(handler)

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler

    def _add_patch_me(
        self,
        me_resource: Resource,
        scopes: list[str],
        env_vars: dict,
        persistent_stack: ps.PersistentStack,
    ):
        patch_me_handler = self._patch_me_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
            user_pool=persistent_stack.staff_users,
        )

        # Add the PATCH method to the me_resource
        me_resource.add_method(
            'PATCH',
            integration=LambdaIntegration(patch_me_handler),
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.patch_staff_user_me_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_staff_user_me_model},
                    response_parameters={'method.response.header.Access-Control-Allow-Origin': True},
                ),
                MethodResponse(
                    status_code='404',
                    response_models={
                        'application/json': self.api_model.message_response_model,
                    },
                ),
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes,
        )

    def _patch_me_handler(self, env_vars: dict, data_encryption_key: IKey, user_table: ITable, user_pool: IUserPool):
        handler = PythonFunction(
            self.stack,
            'PatchMeStaffUserHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'me.py'),
            handler='patch_me',
            environment=env_vars,
        )
        data_encryption_key.grant_encrypt_decrypt(handler)
        user_table.grant_read_write_data(handler)
        user_pool.grant(handler, 'cognito-idp:AdminUpdateUserAttributes')

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler

    def _add_get_users(
        self,
        users_resource: Resource,
        scopes: list[str],
        env_vars: dict,
        persistent_stack: ps.PersistentStack,
    ):
        get_users_handler = self._get_users_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
        )
        # Add the GET method to the users resource
        users_resource.add_method(
            'GET',
            integration=LambdaIntegration(get_users_handler),
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_staff_users_response_model},
                    response_parameters={'method.response.header.Access-Control-Allow-Origin': True},
                ),
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes,
        )

    def _get_users_handler(self, env_vars: dict, data_encryption_key: IKey, user_table: ITable):
        handler = PythonFunction(
            self.stack,
            'GetStaffUsersHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='get_users',
            environment=env_vars,
        )
        data_encryption_key.grant_decrypt(handler)
        user_table.grant_read_data(handler)

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler

    def _add_get_user(
        self,
        user_id_resource: Resource,
        scopes: list[str],
        env_vars: dict,
        persistent_stack: ps.PersistentStack,
    ):
        get_user_handler = self._get_user_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
        )

        # Add the GET method to the user_id resource
        user_id_resource.add_method(
            'GET',
            integration=LambdaIntegration(get_user_handler),
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_staff_user_me_model},
                    response_parameters={'method.response.header.Access-Control-Allow-Origin': True},
                ),
                MethodResponse(
                    status_code='404',
                    response_models={
                        'application/json': self.api_model.message_response_model,
                    },
                ),
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes,
        )

    def _get_user_handler(self, env_vars: dict, data_encryption_key: IKey, user_table: ITable):
        handler = PythonFunction(
            self.stack,
            'GetStaffUserHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='get_one_user',
            environment=env_vars,
        )
        data_encryption_key.grant_decrypt(handler)
        user_table.grant_read_data(handler)

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler

    def _add_patch_user(
        self,
        user_resource: Resource,
        scopes: list[str],
        env_vars: dict,
        persistent_stack: ps.PersistentStack,
    ):
        self.patch_user_handler = self._patch_user_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
        )

        # Add the PATCH method to the me_resource
        user_resource.add_method(
            'PATCH',
            integration=LambdaIntegration(self.patch_user_handler),
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.patch_staff_user_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_staff_user_me_model},
                    response_parameters={'method.response.header.Access-Control-Allow-Origin': True},
                ),
                MethodResponse(
                    status_code='404',
                    response_models={
                        'application/json': self.api_model.message_response_model,
                    },
                ),
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes,
        )

    def _patch_user_handler(self, env_vars: dict, data_encryption_key: IKey, user_table: ITable):
        handler = PythonFunction(
            self.stack,
            'PatchUserHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='patch_user',
            environment=env_vars,
        )
        data_encryption_key.grant_encrypt_decrypt(handler)
        user_table.grant_read_write_data(handler)

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler

    def _add_delete_user(
        self,
        user_id_resource: Resource,
        scopes: list[str],
        *,
        env_vars: dict[str, str],
        persistent_stack: ps.PersistentStack,
    ) -> None:
        """Add DELETE method to delete a staff user's record.

        Args:
            user_id_resource: The API Gateway Resource to add the method to
            scopes: List of OAuth scopes required for this endpoint
            env_vars: Environment variables to pass to the Lambda function
            persistent_stack: Stack containing persistent resources
        """
        self.delete_user_handler = self._delete_user_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
        )

        # Add the method to the resource
        user_id_resource.add_method(
            'DELETE',
            LambdaIntegration(self.delete_user_handler),
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.api_model.message_response_model,
                    },
                ),
                MethodResponse(
                    status_code='404',
                    response_models={
                        'application/json': self.api_model.message_response_model,
                    },
                ),
            ],
        )

        # Add the function's log group to the list for retention setting
        self.log_groups.append(self.delete_user_handler.log_group)

    def _delete_user_handler(self, env_vars: dict, data_encryption_key: IKey, user_table: ITable):
        handler = PythonFunction(
            self.stack,
            'DeleteStaffUserFunction',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='delete_user',
            environment=env_vars,
        )

        # Grant permissions to the function
        data_encryption_key.grant_encrypt_decrypt(handler)
        user_table.grant_read_write_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler

    def _add_post_user(
        self,
        users_resource: Resource,
        scopes: list[str],
        env_vars: dict,
        persistent_stack: ps.PersistentStack,
    ):
        self.post_user_handler = self._post_user_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
            user_pool=persistent_stack.staff_users,
        )

        # Add the POST method to the me_resource
        users_resource.add_method(
            'POST',
            integration=LambdaIntegration(self.post_user_handler),
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_staff_user_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_staff_user_me_model},
                    response_parameters={'method.response.header.Access-Control-Allow-Origin': True},
                ),
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes,
        )

    def _post_user_handler(self, env_vars: dict, data_encryption_key: IKey, user_table: ITable, user_pool: IUserPool):
        handler = PythonFunction(
            self.stack,
            'PostStaffUserHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='post_user',
            environment=env_vars,
        )
        data_encryption_key.grant_encrypt_decrypt(handler)
        user_table.grant_read_write_data(handler)
        user_pool.grant(
            handler,
            'cognito-idp:AdminCreateUser',
            'cognito-idp:AdminDeleteUser',
            'cognito-idp:AdminDisableUser',
            'cognito-idp:AdminEnableUser',
            'cognito-idp:AdminGetUser',
        )

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler

    def _add_reinvite_user(
        self,
        reinvite_resource: Resource,
        scopes: list[str],
        env_vars: dict,
        persistent_stack: ps.PersistentStack,
    ) -> None:
        self.reinvite_user_handler = self._reinvite_user_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
            user_pool=persistent_stack.staff_users,
        )

        # Add the method to the resource
        reinvite_resource.add_method(
            'POST',
            LambdaIntegration(self.reinvite_user_handler),
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.api_model.message_response_model,
                    },
                ),
                MethodResponse(
                    status_code='404',
                    response_models={
                        'application/json': self.api_model.message_response_model,
                    },
                ),
            ],
        )

        # Add the function's log group to the list for retention setting
        self.log_groups.append(self.reinvite_user_handler.log_group)

    def _reinvite_user_handler(
        self, env_vars: dict, data_encryption_key: IKey, user_table: ITable, user_pool: IUserPool
    ):
        handler = PythonFunction(
            self.stack,
            'ReinviteStaffUserFunction',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='reinvite_user',
            environment=env_vars,
        )

        # Grant permissions to the function
        data_encryption_key.grant_encrypt_decrypt(handler)
        user_table.grant_read_write_data(handler)
        user_pool.grant(
            handler,
            'cognito-idp:AdminGetUser',
            'cognito-idp:AdminResetUserPassword',
            'cognito-idp:AdminSetUserPassword',
            'cognito-idp:AdminCreateUser',
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return handler
