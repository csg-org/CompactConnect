from __future__ import annotations

import json
import os
from functools import cached_property
from typing import List

from aws_cdk.aws_apigateway import Resource, MethodResponse, JsonSchema, \
    JsonSchemaType, MockIntegration, IntegrationResponse, AuthorizationType, LambdaIntegration

from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
# Importing module level to allow lazy loading for typing
from .. import cc_api


class StaffUsers:
    def __init__(
            self, *,
            resource: Resource,
            admin_scopes: List[str]
    ):
        super().__init__()

        self.stack = Stack.of(resource)
        self.resource = resource
        self.api: cc_api.CCApi = resource.api
        self.log_groups = []

        # .../
        self._add_get_users(self.resource, admin_scopes)
        self._add_post_user(self.resource, admin_scopes)

        user_id_resource = self.resource.add_resource('{userId}')
        # .../{userId}
        self._add_get_user(user_id_resource, admin_scopes)
        self._add_patch_user(user_id_resource, admin_scopes)

        me_resource = self.resource.add_resource('me')
        # .../me
        self._add_get_me(me_resource)
        self._add_patch_me(me_resource)

        self.api.log_groups.extend(self.log_groups)

    def _add_get_me(self, me_resource: Resource):
        with open(os.path.join('lambdas', 'staff-users', 'tests', 'resources', 'api', 'user-response.json')) as f:
            response_template = f.read()

        me_resource.add_method(
            'GET',
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
            integration=MockIntegration(
                integration_responses=[
                    IntegrationResponse(
                        status_code='200',
                        response_templates={
                            'application/json': response_template
                        },
                        response_parameters={
                            'method.response.header.Access-Control-Allow-Origin': "'*'"
                        }
                    )
                ],
                request_templates={
                    'application/json': json.dumps({'statusCode': 200})
                }
            ),
            request_parameters={
                'method.request.header.Authorization': True
            },
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            authorization_scopes=['profile']
        )

    def _add_patch_me(self, me_resource: Resource):
        with open(os.path.join('lambdas', 'staff-users', 'tests', 'resources', 'api', 'user-response.json')) as f:
            response_template = f.read()

        me_resource.add_method(
            'PATCH',
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
            integration=MockIntegration(
                integration_responses=[
                    IntegrationResponse(
                        status_code='200',
                        response_templates={
                            'application/json': response_template
                        },
                        response_parameters={
                            'method.response.header.Access-Control-Allow-Origin': "'*'"
                        }
                    )
                ],
                request_templates={
                    'application/json': json.dumps({'statusCode': 200})
                }
            ),
            request_parameters={
                'method.request.header.Authorization': True
            },
            authorization_type=AuthorizationType.COGNITO,
            authorizer=self.api.staff_users_authorizer,
            # This is the same scope that Cognito requires for editing its own user attributes, so we will follow suit.
            authorization_scopes=['aws.cognito.signin.user.admin']
        )

    def _add_get_users(self, users_resource: Resource, admin_scopes: List[str]):
        # Create a PythonFunction for the get_users handler
        get_users_handler = PythonFunction(
            users_resource,
            'GetUsersHandler',
            entry='lambdas/staff-users',
            index='handlers/users.py',
            handler='get_users',
            environment={
                **self.stack.common_env_vars
            }
        )

        # Create a LambdaIntegration
        lambda_integration = LambdaIntegration(get_users_handler)

        # Add the GET method to the users resource
        users_resource.add_method(
            'GET',
            integration=lambda_integration,
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
            authorization_scopes=admin_scopes
        )

    def _add_get_user(self, user_id_resource: Resource, admin_scopes: List[str]):
        # Create a PythonFunction for the get_user handler
        get_user_handler = PythonFunction(
            user_id_resource,
            'GetUserHandler',
            entry='lambdas/staff-users',
            index='handlers/users.py',
            handler='get_user',
            environment={
                **self.stack.common_env_vars
            }
        )

        # Create a LambdaIntegration
        lambda_integration = LambdaIntegration(get_user_handler)

        # Add the GET method to the user_id resource
        user_id_resource.add_method(
            'GET',
            integration=lambda_integration,
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
            authorization_scopes=admin_scopes
        )

    def _add_patch_user(self, user_resource: Resource, admin_scopes: List[str]):
        patch_user_handler = PythonFunction(
            user_resource, 'PatchUserHandler',
            entry='lambdas/staff-users',
            index='handlers/users.py',
            handler='patch_user',
            environment={
                **self.stack.common_env_vars
            }
        )

        # Create a LambdaIntegration
        lambda_integration = LambdaIntegration(patch_user_handler)

        # Add the PATCH method to the me_resource
        user_resource.add_method(
            'PATCH',
            integration=lambda_integration,
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
            authorization_scopes=admin_scopes
        )

    def _add_post_user(self, users_resource: Resource, admin_scopes: List[str]):
        post_user_handler = PythonFunction(
            users_resource,
            'PostUserHandler',
            entry='lambdas/staff-users',
            index='handlers/users.py',
            handler='post_user',
            environment={
                **self.stack.common_env_vars
            }
        )

        # Create a LambdaIntegration
        lambda_integration = LambdaIntegration(post_user_handler)

        # Add the POST method to the me_resource
        users_resource.add_method(
            'POST',
            integration=lambda_integration,
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
            authorization_scopes=admin_scopes
        )

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
