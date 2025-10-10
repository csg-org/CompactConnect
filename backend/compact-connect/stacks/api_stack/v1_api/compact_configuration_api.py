from __future__ import annotations

from aws_cdk.aws_apigateway import LambdaIntegration, MethodOptions, MethodResponse, Resource
from cdk_nag import NagSuppressions

from common_constructs.cc_api import CCApi
from common_constructs.python_function import PythonFunction
from stacks.api_lambda_stack import ApiLambdaStack

from .api_model import ApiModel


class CompactConfigurationApi:
    """
    This class manages all the endpoints related to reading compact configuration data for both compacts and their
    associated jurisdictions.
    """

    def __init__(
        self,
        *,
        api: CCApi,
        compact_resource: Resource,
        jurisdictions_resource: Resource,
        public_jurisdictions_resource: Resource,
        jurisdiction_resource: Resource,
        general_read_method_options: MethodOptions,
        admin_method_options: MethodOptions,
        api_model: ApiModel,
        api_lambda_stack: ApiLambdaStack,
    ):
        super().__init__()

        self.api = api
        # /v1/compacts/{compact}
        self.staff_users_compact_resource = compact_resource
        # /v1/compacts/{compact}/jurisdictions
        self.staff_users_jurisdictions_resource = jurisdictions_resource
        # /v1/compacts/{compact}/jurisdictions/{jurisdiction}
        self.staff_users_jurisdiction_resource = jurisdiction_resource
        # /v1/public/compacts/{compact}/jurisdictions
        self.public_jurisdictions_resource = public_jurisdictions_resource
        self.api_model = api_model

        # Create the compact configration api lambda function that will be shared by all compact configuration
        # related endpoints
        compact_configuration_api_function = (
            api_lambda_stack.compact_configuration_lambdas.compact_configuration_api_handler
        )

        self._add_staff_users_get_compact_jurisdictions_endpoint(
            compact_configuration_api_handler=compact_configuration_api_function,
            general_read_method_options=general_read_method_options,
        )

        self._add_public_get_compact_jurisdictions_endpoint(
            compact_configuration_api_handler=compact_configuration_api_function,
        )

        self._add_staff_users_get_compact_configuration_endpoint(
            compact_configuration_api_handler=compact_configuration_api_function,
            general_read_method_options=general_read_method_options,
        )

        self._add_staff_users_put_compact_configuration_endpoint(
            compact_configuration_api_handler=compact_configuration_api_function,
            admin_method_options=admin_method_options,
        )

        self._add_staff_users_get_jurisdiction_configuration_endpoint(
            compact_configuration_api_handler=compact_configuration_api_function,
            general_read_method_options=general_read_method_options,
        )

        self._add_staff_users_put_jurisdiction_configuration_endpoint(
            compact_configuration_api_handler=compact_configuration_api_function,
            admin_method_options=admin_method_options,
        )

    def _add_staff_users_get_compact_jurisdictions_endpoint(
        self, compact_configuration_api_handler: PythonFunction, general_read_method_options: MethodOptions
    ):
        self.staff_users_jurisdictions_resource.add_method(
            'GET',
            LambdaIntegration(compact_configuration_api_handler),
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_compact_jurisdictions_response_model},
                ),
            ],
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=general_read_method_options.authorization_type,
            authorizer=general_read_method_options.authorizer,
            authorization_scopes=general_read_method_options.authorization_scopes,
        )

    def _add_public_get_compact_jurisdictions_endpoint(self, compact_configuration_api_handler: PythonFunction):
        public_get_compact_jurisdictions_method = self.public_jurisdictions_resource.add_method(
            'GET',
            LambdaIntegration(compact_configuration_api_handler),
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_compact_jurisdictions_response_model},
                ),
            ],
        )

        # Add suppressions for the public GET endpoint
        NagSuppressions.add_resource_suppressions(
            public_get_compact_jurisdictions_method,
            suppressions=[
                {
                    'id': 'AwsSolutions-APIG4',
                    'reason': 'This is a public endpoint that intentionally does not require authorization',
                },
                {
                    'id': 'AwsSolutions-COG4',
                    'reason': 'This is a public endpoint that intentionally '
                    'does not use a Cognito user pool authorizer',
                },
            ],
        )

    def _add_staff_users_get_compact_configuration_endpoint(
        self, compact_configuration_api_handler: PythonFunction, general_read_method_options: MethodOptions
    ):
        """Add GET endpoint for /v1/compacts/{compact}"""
        self.staff_users_compact_resource.add_method(
            'GET',
            LambdaIntegration(compact_configuration_api_handler),
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_compact_configuration_response_model},
                ),
            ],
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=general_read_method_options.authorization_type,
            authorizer=general_read_method_options.authorizer,
            authorization_scopes=general_read_method_options.authorization_scopes,
        )

    def _add_staff_users_put_compact_configuration_endpoint(
        self, compact_configuration_api_handler: PythonFunction, admin_method_options: MethodOptions
    ):
        """Add PUT endpoint for /v1/compacts/{compact}"""
        self.staff_users_compact_resource.add_method(
            'PUT',
            LambdaIntegration(compact_configuration_api_handler),
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            request_parameters={'method.request.header.Authorization': True},
            request_models={'application/json': self.api_model.put_compact_request_model},
            authorization_type=admin_method_options.authorization_type,
            authorizer=admin_method_options.authorizer,
            authorization_scopes=admin_method_options.authorization_scopes,
        )

    def _add_staff_users_get_jurisdiction_configuration_endpoint(
        self, compact_configuration_api_handler: PythonFunction, general_read_method_options: MethodOptions
    ):
        """Add GET endpoint for /v1/compacts/{compact}/jurisdictions/{jurisdiction}"""
        self.staff_users_jurisdiction_resource.add_method(
            'GET',
            LambdaIntegration(compact_configuration_api_handler),
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_jurisdiction_response_model},
                ),
            ],
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=general_read_method_options.authorization_type,
            authorizer=general_read_method_options.authorizer,
            authorization_scopes=general_read_method_options.authorization_scopes,
        )

    def _add_staff_users_put_jurisdiction_configuration_endpoint(
        self, compact_configuration_api_handler: PythonFunction, admin_method_options: MethodOptions
    ):
        """Add PUT endpoint for /v1/compacts/{compact}/jurisdictions/{jurisdiction}"""
        self.staff_users_jurisdiction_resource.add_method(
            'PUT',
            LambdaIntegration(compact_configuration_api_handler),
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            request_parameters={'method.request.header.Authorization': True},
            request_models={'application/json': self.api_model.put_jurisdiction_request_model},
            authorization_type=admin_method_options.authorization_type,
            authorizer=admin_method_options.authorizer,
            authorization_scopes=admin_method_options.authorization_scopes,
        )
