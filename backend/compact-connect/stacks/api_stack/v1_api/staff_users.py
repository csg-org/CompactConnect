from __future__ import annotations

from functools import cached_property
from typing import List

from aws_cdk.aws_apigateway import Resource, MethodResponse, JsonSchema, JsonSchemaType, AuthorizationType, \
    LambdaIntegration
from aws_cdk.aws_cognito import IUserPool
from aws_cdk.aws_dynamodb import ITable
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions

from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

# Importing module level to allow lazy loading for typing
from stacks import persistent_stack as ps
from .. import cc_api


class StaffUsers:
    def __init__(
            self, *,
            admin_resource: Resource,
            self_resource: Resource,
            admin_scopes: List[str],
            persistent_stack: ps.PersistentStack
    ):
        super().__init__()

        self.stack = Stack.of(admin_resource)
        self.admin_resource = admin_resource
        self.api: cc_api.CCApi = admin_resource.api

        self.log_groups = []
        env_vars = {
            **self.stack.common_env_vars,
            'USER_POOL_ID': persistent_stack.staff_users.user_pool_id,
            'USERS_TABLE_NAME': persistent_stack.staff_users.user_table.table_name,
            'FAM_GIV_INDEX_NAME': persistent_stack.staff_users.user_table.family_given_index_name
        }

        # .../
        self._add_get_users(self.admin_resource, admin_scopes, env_vars=env_vars, persistent_stack=persistent_stack)
        self._add_post_user(self.admin_resource, admin_scopes, env_vars=env_vars, persistent_stack=persistent_stack)

        user_id_resource = self.admin_resource.add_resource('{userId}')
        # .../{userId}
        self._add_get_user(user_id_resource, admin_scopes, env_vars=env_vars, persistent_stack=persistent_stack)
        self._add_patch_user(user_id_resource, admin_scopes, env_vars=env_vars, persistent_stack=persistent_stack)

        self.me_resource = self_resource.add_resource('me')
        # .../me
        profile_scopes = ['profile']
        self._add_get_me(self.me_resource, profile_scopes, env_vars=env_vars, persistent_stack=persistent_stack)
        self._add_patch_me(self.me_resource, profile_scopes, env_vars=env_vars, persistent_stack=persistent_stack)

        self.api.log_groups.extend(self.log_groups)

    def _add_get_me(
            self,
            me_resource: Resource,
            scopes: list[str],
            env_vars: dict,
            persistent_stack: ps.PersistentStack
    ):
        get_me_handler = self._get_me_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            users_table=persistent_stack.staff_users.user_table
        )

        # Add the GET method to the me_resource
        me_resource.add_method(
            'GET',
            integration=LambdaIntegration(get_me_handler),
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.get_me_model
                    },
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes
        )

    def _get_me_handler(self, env_vars: dict, data_encryption_key: IKey, users_table: ITable):
        handler = PythonFunction(
            self.stack,
            'GetMeStaffUserHandler',
            entry='lambdas/staff-users',
            index='handlers/me.py',
            handler='get_me',
            environment=env_vars
        )
        data_encryption_key.grant_decrypt(handler)
        users_table.grant_read_data(handler)

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                              'and is scoped to one table and encryption key.'
                }
            ]
        )
        return handler

    def _add_patch_me(
            self,
            me_resource: Resource,
            scopes: list[str],
            env_vars: dict,
            persistent_stack: ps.PersistentStack
    ):
        patch_me_handler = self._patch_me_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            users_table=persistent_stack.staff_users.user_table,
            user_pool=persistent_stack.staff_users
        )

        # Add the PATCH method to the me_resource
        me_resource.add_method(
            'PATCH',
            integration=LambdaIntegration(patch_me_handler),
            request_validator=self.api.parameter_body_validator,
            request_models={
                'application/json': self.patch_me_model
            },
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.get_me_model
                    },
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes
        )

    def _patch_me_handler(
            self,
            env_vars: dict,
            data_encryption_key: IKey,
            users_table: ITable,
            user_pool: IUserPool
    ):
        handler = PythonFunction(
            self.stack,
            'PatchMeStaffUserHandler',
            entry='lambdas/staff-users',
            index='handlers/me.py',
            handler='patch_me',
            environment=env_vars
        )
        data_encryption_key.grant_encrypt_decrypt(handler)
        users_table.grant_read_write_data(handler)
        user_pool.grant(handler, 'cognito-idp:AdminUpdateUserAttributes')

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                              'and is scoped to one table and encryption key.'
                }
            ]
        )
        return handler

    def _add_get_users(
            self,
            users_resource: Resource,
            scopes: List[str],
            env_vars: dict,
            persistent_stack: ps.PersistentStack
    ):
        get_users_handler = self._get_users_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            users_table=persistent_stack.staff_users.user_table
        )
        # Add the GET method to the users resource
        users_resource.add_method(
            'GET',
            integration=LambdaIntegration(get_users_handler),
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.get_staff_users_response_model
                    },
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes
        )

    def _get_users_handler(self, env_vars: dict, data_encryption_key: IKey, users_table: ITable):
        handler = PythonFunction(
            self.stack,
            'GetStaffUsersHandler',
            entry='lambdas/staff-users',
            index='handlers/users.py',
            handler='get_users',
            environment=env_vars
        )
        data_encryption_key.grant_decrypt(handler)
        users_table.grant_read_data(handler)

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                              'and is scoped to one table and encryption key.'
                }
            ]
        )
        return handler

    def _add_get_user(
            self,
            user_id_resource: Resource,
            scopes: List[str],
            env_vars: dict,
            persistent_stack: ps.PersistentStack
    ):
        get_user_handler = self._get_user_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            users_table=persistent_stack.staff_users.user_table
        )

        # Add the GET method to the user_id resource
        user_id_resource.add_method(
            'GET',
            integration=LambdaIntegration(get_user_handler),
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.get_me_model
                    },
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes
        )

    def _get_user_handler(self, env_vars: dict, data_encryption_key: IKey, users_table: ITable):
        handler = PythonFunction(
            self.stack,
            'GetStaffUserHandler',
            entry='lambdas/staff-users',
            index='handlers/users.py',
            handler='get_one_user',
            environment=env_vars
        )
        data_encryption_key.grant_decrypt(handler)
        users_table.grant_read_data(handler)

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                              'and is scoped to one table and encryption key.'
                }
            ]
        )
        return handler

    def _add_patch_user(
            self,
            user_resource: Resource,
            scopes: List[str],
            env_vars: dict,
            persistent_stack: ps.PersistentStack
    ):
        patch_user_handler = self._patch_user_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            users_table=persistent_stack.staff_users.user_table
        )

        # Add the PATCH method to the me_resource
        user_resource.add_method(
            'PATCH',
            integration=LambdaIntegration(patch_user_handler),
            request_validator=self.api.parameter_body_validator,
            request_models={
                'application/json': self.patch_user_model
            },
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.get_me_model
                    },
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes
        )

    def _patch_user_handler(self, env_vars: dict, data_encryption_key: IKey, users_table: ITable):
        handler = PythonFunction(
                self.stack, 'PatchUserHandler',
                entry='lambdas/staff-users',
                index='handlers/users.py',
                handler='patch_user',
                environment=env_vars
            )
        data_encryption_key.grant_encrypt_decrypt(handler)
        users_table.grant_read_write_data(handler)

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                              'and is scoped to one table and encryption key.'
                }
            ]
        )
        return handler

    def _add_post_user(
            self,
            users_resource: Resource,
            scopes: List[str],
            env_vars: dict,
            persistent_stack: ps.PersistentStack
    ):
        post_user_handler = self._post_user_handler(
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            users_table=persistent_stack.staff_users.user_table,
            user_pool=persistent_stack.staff_users
        )

        # Add the POST method to the me_resource
        users_resource.add_method(
            'POST',
            integration=LambdaIntegration(post_user_handler),
            request_validator=self.api.parameter_body_validator,
            request_models={
                'application/json': self.post_user_model
            },
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.get_me_model
                    },
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ],
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=scopes
        )

    def _post_user_handler(
            self,
            env_vars: dict,
            data_encryption_key: IKey,
            users_table: ITable,
            user_pool: IUserPool
    ):
        handler = PythonFunction(
            self.stack,
            'PostStaffUserHandler',
            entry='lambdas/staff-users',
            index='handlers/users.py',
            handler='post_user',
            environment=env_vars
        )
        data_encryption_key.grant_encrypt_decrypt(handler)
        users_table.grant_read_write_data(handler)
        user_pool.grant(
            handler,
            'cognito-idp:AdminCreateUser',
            'cognito-idp:AdminDeleteUser',
            'cognito-idp:AdminDisableUser',
            'cognito-idp:AdminEnableUser',
            'cognito-idp:AdminGetUser'
        )

        self.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                              'and is scoped to one table and encryption key.'
                }
            ]
        )
        return handler

    @cached_property
    def get_me_model(self):
        """
        Return the Get Me Model, which should only be created once per API
        """
        if hasattr(self.api, 'v1_get_me_model'):
            return self.api.v1_get_me_model

        self.api.v1_get_me_model = self.api.add_model(
            'V1GetMeModel',
            description='Get me response model',
            schema=self._user_response_schema
        )
        return self.api.v1_get_me_model

    @cached_property
    def get_staff_users_response_model(self):
        """
        Return the Get Users Model, which should only be created once per API
        """
        if hasattr(self.api, 'v1_get_staff_users_response_model'):
            return self.api.v1_get_staff_users_response_model

        self.api.v1_get_staff_users_response_model = self.api.add_model(
            'V1GetStaffUsersModel',
            description='Get staff users response model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                properties={
                    'users': JsonSchema(
                        type=JsonSchemaType.ARRAY,
                        items=self._user_response_schema
                    ),
                    'pagination': self._pagination_response_schema
                }
            )
        )
        return self.api.v1_get_staff_users_response_model

    @cached_property
    def patch_me_model(self):
        """
        Return the Get Me Model, which should only be created once per API
        """
        if hasattr(self.api, 'v1_patch_me_request_model'):
            return self.api.v1_patch_me_request_model

        self.api.v1_patch_me_request_model = self.api.add_model(
            'V1PatchMeRequestModel',
            description='Patch me request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                properties={
                    'attributes': self._patch_attributes_schema,
                }
            )
        )
        return self.api.v1_patch_me_request_model

    @cached_property
    def patch_user_model(self):
        """
        Return the Patch User Model, which should only be created once per API
        """
        if hasattr(self.api, 'v1_patch_user_request_model'):
            return self.api.v1_patch_user_request_model

        self.api.v1_patch_user_request_model = self.api.add_model(
            'V1PatchUserRequestModel',
            description='Patch user request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                properties={
                    'permissions': self._permissions_schema
                }
            )
        )
        return self.api.v1_patch_user_request_model

    @property
    def post_user_model(self):
        """
        Return the Post User Model, which should only be created once per API
        """
        if hasattr(self.api, 'v1_post_user_request_model'):
            return self.api.v1_post_user_request_model

        self.api.v1_post_user_request_model = self.api.add_model(
            'V1PostUserRequestModel',
            description='Post user request model',
            schema=JsonSchema(
                type=JsonSchemaType.OBJECT,
                required=[
                    'attributes',
                    'permissions'
                ],
                additional_properties=False,
                properties=self._common_user_properties
            )
        )
        return self.api.v1_post_user_request_model

    @property
    def _attributes_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            additional_properties=False,
            properties={
                'email': JsonSchema(type=JsonSchemaType.STRING, min_length=5, max_length=100),
                'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100)
            }
        )

    @property
    def _patch_attributes_schema(self):
        """
        No support for changing a user's email address.
        """
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            additional_properties=False,
            properties={
                'givenName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100),
                'familyName': JsonSchema(type=JsonSchemaType.STRING, min_length=1, max_length=100)
            }
        )

    @property
    def _permissions_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            additional_properties=JsonSchema(
                type=JsonSchemaType.OBJECT,
                additional_properties=False,
                properties={
                    'actions': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        properties={
                            'read': JsonSchema(type=JsonSchemaType.BOOLEAN),
                            'admin': JsonSchema(type=JsonSchemaType.BOOLEAN)
                        }
                    ),
                    'jurisdictions': JsonSchema(
                        type=JsonSchemaType.OBJECT,
                        additional_properties=JsonSchema(
                            type=JsonSchemaType.OBJECT,
                            properties={
                                'actions': JsonSchema(
                                    type=JsonSchemaType.OBJECT,
                                    additional_properties=False,
                                    properties={
                                        'write': JsonSchema(type=JsonSchemaType.BOOLEAN),
                                        'admin': JsonSchema(type=JsonSchemaType.BOOLEAN)
                                    }
                                )
                            }
                        )
                    )
                }
            )
        )

    @property
    def _common_user_properties(self):
        return {
            'attributes': self._attributes_schema,
            'permissions': self._permissions_schema
        }

    @property
    def _user_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            required=[
                'userId',
                'attributes',
                'permissions'
            ],
            additional_properties=False,
            properties={
                'userId': JsonSchema(type=JsonSchemaType.STRING),
                **self._common_user_properties
            }
        )

    @property
    def _pagination_response_schema(self):
        return JsonSchema(
            type=JsonSchemaType.OBJECT,
            properties={
                'lastKey': JsonSchema(
                    type=[JsonSchemaType.STRING, JsonSchemaType.NULL],
                    min_length=1,
                    max_length=1024
                ),
                'prevLastKey': JsonSchema(
                    type=[JsonSchemaType.STRING, JsonSchemaType.NULL],
                    min_length=1,
                    max_length=1024
                ),
                'pageSize': JsonSchema(type=JsonSchemaType.INTEGER, minimum=5, maximum=100)
            }
        )
