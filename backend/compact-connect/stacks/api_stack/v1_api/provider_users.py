from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodResponse, Resource
from cdk_nag import NagSuppressions
from common_constructs.cc_api import CCApi
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

from stacks.api_lambda_stack import ApiLambdaStack

from .api_model import ApiModel


class ProviderUsers:
    def __init__(
        self,
        *,
        resource: Resource,
        api_model: ApiModel,
        privilege_history_function: PythonFunction,
        api_lambda_stack: ApiLambdaStack,
    ):
        super().__init__()
        # /v1/provider-users
        self.provider_users_resource = resource
        self.api_model = api_model
        self.api: CCApi = resource.api

        # /v1/provider-users/registration
        self.provider_users_registration_resource = self.provider_users_resource.add_resource('registration')
        self._add_provider_registration(
            api_lambda_stack=api_lambda_stack,
        )

        # /v1/provider-users/initiateRecovery
        # /v1/provider-users/verifyRecovery
        self.account_recovery_initiate_resource = self.provider_users_resource.add_resource('initiateRecovery')
        self.account_recovery_verify_resource = self.provider_users_resource.add_resource('verifyRecovery')
        self._add_account_recovery_endpoints(
            api_lambda_stack=api_lambda_stack,
        )

        # /v1/provider-users/me
        self.provider_users_me_resource = self.provider_users_resource.add_resource('me')

        # Reference the shared lambda handler for all provider-users/me endpoints from api_lambda_stack
        self.provider_users_me_handler = api_lambda_stack.provider_users_lambdas.provider_users_me_handler

        # Add the GET method for /v1/provider-users/me
        self._add_get_provider_user_me()

        # /v1/provider-users/me/military-affiliation
        self.provider_users_me_military_affiliation_resource = self.provider_users_me_resource.add_resource(
            'military-affiliation'
        )

        # Add the POST and PATCH methods for /v1/provider-users/me/military-affiliation
        self._add_provider_user_me_military_affiliation()

        # /v1/provider-users/me/home-jurisdiction
        self.provider_users_me_home_jurisdiction_resource = self.provider_users_me_resource.add_resource(
            'home-jurisdiction'
        )

        # Add the PUT method for /v1/provider-users/me/home-jurisdiction
        self._add_provider_user_me_home_jurisdiction()

        # /v1/provider-users/me/email
        self.provider_users_me_email_resource = self.provider_users_me_resource.add_resource('email')
        self._add_provider_user_me_email()

        # /v1/provider-users/me/email/verify
        self.provider_users_me_email_verify_resource = self.provider_users_me_email_resource.add_resource('verify')
        self._add_provider_user_me_email_verify()

        self.provider_jurisdiction_resource = self.provider_users_me_resource.add_resource('jurisdiction').add_resource(
            '{jurisdiction}'
        )
        self.provider_jurisdiction_license_type_resource = self.provider_jurisdiction_resource.add_resource(
            'licenseType'
        ).add_resource('{licenseType}')

        self._add_get_privilege_history(
            privilege_history_function=privilege_history_function,
        )

    def _add_get_provider_user_me(self):
        self.provider_users_me_resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.provider_response_model},
                ),
            ],
            integration=LambdaIntegration(self.provider_users_me_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

    def _add_provider_user_me_military_affiliation(self):
        self.provider_users_me_military_affiliation_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_provider_user_military_affiliation_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={
                        'application/json': self.api_model.post_provider_military_affiliation_response_model
                    },
                ),
            ],
            integration=LambdaIntegration(self.provider_users_me_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

        self.provider_users_me_military_affiliation_resource.add_method(
            'PATCH',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.patch_provider_user_military_affiliation_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(self.provider_users_me_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

    def _add_provider_user_me_home_jurisdiction(self):
        self.provider_users_me_home_jurisdiction_resource.add_method(
            'PUT',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.put_provider_home_jurisdiction_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(self.provider_users_me_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

    def _add_provider_user_me_email(self):
        self.provider_users_me_email_resource.add_method(
            'PATCH',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.patch_provider_email_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(self.provider_users_me_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

    def _add_provider_user_me_email_verify(self):
        self.provider_users_me_email_verify_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_provider_email_verify_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(self.provider_users_me_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

    def _add_provider_registration(
        self,
        api_lambda_stack: ApiLambdaStack,
    ):
        stack = Stack.of(self.provider_users_resource)

        self.api.log_groups.append(api_lambda_stack.provider_users_lambdas.provider_registration_handler.log_group)

        registration_method = self.provider_users_registration_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.provider_registration_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(
                api_lambda_stack.provider_users_lambdas.provider_registration_handler,
                timeout=Duration.seconds(29),
            ),
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{registration_method.node.path}',
            suppressions=[
                {
                    'id': 'AwsSolutions-APIG4',
                    'reason': 'This is a public registration endpoint that needs to be accessible without '
                    'authorization',
                },
                {
                    'id': 'AwsSolutions-COG4',
                    'reason': 'This is a public registration endpoint that needs to be accessible without Cognito '
                    'authorization',
                },
            ],
        )

    def _add_get_privilege_history(
        self,
        privilege_history_function: PythonFunction,
    ):
        self.privilege_history_resource = self.provider_jurisdiction_license_type_resource.add_resource('history')

        self.privilege_history_resource.add_method(
            'GET',
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.privilege_history_response_model},
                ),
            ],
            integration=LambdaIntegration(privilege_history_function, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

    def _add_account_recovery_endpoints(self, *, api_lambda_stack: ApiLambdaStack):
        stack = Stack.of(self.provider_users_resource)

        initiate_account_recovery_method = self.account_recovery_initiate_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.provider_account_recovery_initiate_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200', response_models={'application/json': self.api_model.message_response_model}
                ),
            ],
            integration=LambdaIntegration(
                api_lambda_stack.provider_users_lambdas.account_recovery_initiate_function, timeout=Duration.seconds(29)
            ),
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{initiate_account_recovery_method.node.path}',
            suppressions=[
                {
                    'id': 'AwsSolutions-APIG4',
                    'reason': 'This is a public account recovery endpoint that needs to be accessible without '
                    'authorization',
                },
                {
                    'id': 'AwsSolutions-COG4',
                    'reason': 'This is a public account recovery endpoint that needs to be accessible without Cognito '
                    'authorization',
                },
            ],
        )

        verify_account_recovery_method = self.account_recovery_verify_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.provider_account_recovery_verify_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200', response_models={'application/json': self.api_model.message_response_model}
                ),
            ],
            integration=LambdaIntegration(
                api_lambda_stack.provider_users_lambdas.account_recovery_verify_function, timeout=Duration.seconds(29)
            ),
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{verify_account_recovery_method.node.path}',
            suppressions=[
                {
                    'id': 'AwsSolutions-APIG4',
                    'reason': 'This is a public account recovery endpoint that needs to be accessible without '
                    'authorization',
                },
                {
                    'id': 'AwsSolutions-COG4',
                    'reason': 'This is a public account recovery endpoint that needs to be accessible without Cognito '
                    'authorization',
                },
            ],
        )
