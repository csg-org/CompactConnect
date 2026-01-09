from __future__ import annotations

from aws_cdk.aws_apigateway import (
    AuthorizationType,
    LambdaIntegration,
    MethodResponse,
    Resource,
)

from common_constructs.cc_api import CCApi
from stacks import persistent_stack as ps
from stacks.api_lambda_stack import ApiLambdaStack

from .api_model import ApiModel


class StaffUsers:
    def __init__(
        self,
        *,
        admin_resource: Resource,
        self_resource: Resource,
        admin_scopes: list[str],
        api_lambda_stack: ApiLambdaStack,
        api_model: ApiModel,
    ):
        super().__init__()

        self.stack: ps.PersistentStack = ps.PersistentStack.of(admin_resource)
        self.admin_resource = admin_resource
        self.api: CCApi = admin_resource.api
        self.api_model = api_model

        # <base-url>/
        self._add_get_users(
            self.admin_resource,
            admin_scopes,
            api_lambda_stack=api_lambda_stack,
        )
        self._add_post_user(self.admin_resource, admin_scopes, api_lambda_stack=api_lambda_stack)

        self.user_id_resource = self.admin_resource.add_resource('{userId}')
        # <base-url>/{userId}
        self._add_get_user(self.user_id_resource, admin_scopes, api_lambda_stack=api_lambda_stack)
        self._add_patch_user(self.user_id_resource, admin_scopes, api_lambda_stack=api_lambda_stack)
        self._add_delete_user(self.user_id_resource, admin_scopes, api_lambda_stack=api_lambda_stack)

        # <base-url>/{userId}/reinvite
        self.reinvite_resource = self.user_id_resource.add_resource('reinvite')
        self._add_reinvite_user(self.reinvite_resource, admin_scopes, api_lambda_stack=api_lambda_stack)

        self.me_resource = self_resource.add_resource('me')
        # <base-url>/me
        profile_scopes = ['profile']
        self._add_get_me(self.me_resource, profile_scopes, api_lambda_stack=api_lambda_stack)
        self._add_patch_me(self.me_resource, profile_scopes, api_lambda_stack=api_lambda_stack)

    def _add_get_me(
        self,
        me_resource: Resource,
        scopes: list[str],
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.staff_users_lambdas.get_me_handler

        # Add the GET method to the me_resource
        me_resource.add_method(
            'GET',
            integration=LambdaIntegration(handler),
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

    def _add_patch_me(
        self,
        me_resource: Resource,
        scopes: list[str],
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.staff_users_lambdas.patch_me_handler

        # Add the PATCH method to the me_resource
        me_resource.add_method(
            'PATCH',
            integration=LambdaIntegration(handler),
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

    def _add_get_users(
        self,
        users_resource: Resource,
        scopes: list[str],
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.staff_users_lambdas.get_users_handler

        # Add the GET method to the users resource
        users_resource.add_method(
            'GET',
            integration=LambdaIntegration(handler),
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

    def _add_get_user(
        self,
        user_id_resource: Resource,
        scopes: list[str],
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.staff_users_lambdas.get_user_handler

        # Add the GET method to the user_id resource
        user_id_resource.add_method(
            'GET',
            integration=LambdaIntegration(handler),
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

    def _add_patch_user(
        self,
        user_resource: Resource,
        scopes: list[str],
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.staff_users_lambdas.patch_user_handler

        # Add the PATCH method to the me_resource
        user_resource.add_method(
            'PATCH',
            integration=LambdaIntegration(handler),
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

    def _add_delete_user(
        self,
        user_id_resource: Resource,
        scopes: list[str],
        *,
        api_lambda_stack: ApiLambdaStack,
    ) -> None:
        """Add DELETE method to delete a staff user's record.

        :param user_id_resource: The API Gateway Resource to add the method to
        :param scopes: List of OAuth scopes required for this endpoint
        :param env_vars: Environment variables to pass to the Lambda function
        :param persistent_stack: Stack containing persistent resources
        """
        handler = api_lambda_stack.staff_users_lambdas.delete_user_handler

        # Add the method to the resource
        user_id_resource.add_method(
            'DELETE',
            LambdaIntegration(handler),
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

    def _add_post_user(
        self,
        users_resource: Resource,
        scopes: list[str],
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.staff_users_lambdas.post_user_handler

        # Add the POST method to the me_resource
        users_resource.add_method(
            'POST',
            integration=LambdaIntegration(handler),
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

    def _add_reinvite_user(
        self,
        reinvite_resource: Resource,
        scopes: list[str],
        api_lambda_stack: ApiLambdaStack,
    ) -> None:
        handler = api_lambda_stack.staff_users_lambdas.reinvite_user_handler

        # Add the method to the resource
        reinvite_resource.add_method(
            'POST',
            LambdaIntegration(handler),
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
