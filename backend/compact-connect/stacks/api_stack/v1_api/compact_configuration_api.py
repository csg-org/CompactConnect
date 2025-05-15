from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodOptions, MethodResponse, Resource
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

from stacks import persistent_stack as ps

# Importing module level to allow lazy loading for typing
from stacks.api_stack import cc_api

from .api_model import ApiModel


class CompactConfigurationApi:
    """
    This class manages all the endpoints related to reading compact configuration data for both compacts and their
    associated jurisdictions.
    """

    def __init__(
        self,
        *,
        api: cc_api.CCApi,
        compact_resource: Resource,
        jurisdictions_resource: Resource,
        public_jurisdictions_resource: Resource,
        jurisdiction_resource: Resource,
        general_read_method_options: MethodOptions,
        admin_method_options: MethodOptions,
        persistent_stack: ps.PersistentStack,
        api_model: ApiModel,
    ):
        """
        Initializes the CompactConfigurationApi, setting up API Gateway endpoints and a shared Lambda
        function for managing compact configuration and jurisdiction data.
        
        Configures resources, authorization, request/response models, and permissions for endpoints
        supporting both staff and public access to compact and jurisdiction configuration data.
        """
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

        stack: Stack = Stack.of(jurisdictions_resource)
        lambda_environment = {
            'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
            **stack.common_env_vars,
        }

        # Create the compact configration api lambda function that will be shared by all compact configuration
        # related endpoints
        self.compact_configuration_api_function = PythonFunction(
            self.api,
            'CompactConfigurationApiFunction',
            index=os.path.join('handlers', 'compact_configuration.py'),
            lambda_dir='compact-configuration',
            handler='compact_configuration_api_handler',
            environment=lambda_environment,
            timeout=Duration.seconds(30),
        )
        persistent_stack.shared_encryption_key.grant_decrypt(self.compact_configuration_api_function)
        persistent_stack.compact_configuration_table.grant_read_write_data(self.compact_configuration_api_function)
        self.api.log_groups.append(self.compact_configuration_api_function.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{self.compact_configuration_api_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )

        self._add_staff_users_get_compact_jurisdictions_endpoint(
            compact_configuration_api_handler=self.compact_configuration_api_function,
            general_read_method_options=general_read_method_options,
        )

        self._add_public_get_compact_jurisdictions_endpoint(
            compact_configuration_api_handler=self.compact_configuration_api_function,
        )

        self._add_staff_users_get_compact_configuration_endpoint(
            compact_configuration_api_handler=self.compact_configuration_api_function,
            general_read_method_options=general_read_method_options,
        )

        self._add_staff_users_put_compact_configuration_endpoint(
            compact_configuration_api_handler=self.compact_configuration_api_function,
            admin_method_options=admin_method_options,
        )

        self._add_staff_users_get_jurisdiction_configuration_endpoint(
            compact_configuration_api_handler=self.compact_configuration_api_function,
            general_read_method_options=general_read_method_options,
        )

        self._add_staff_users_put_jurisdiction_configuration_endpoint(
            compact_configuration_api_handler=self.compact_configuration_api_function,
            admin_method_options=admin_method_options,
        )

    def _add_staff_users_get_compact_jurisdictions_endpoint(
        self, compact_configuration_api_handler: PythonFunction, general_read_method_options: MethodOptions
    ):
        """
        Adds a GET endpoint for staff users to retrieve jurisdictions for a specific compact.
        
        Configures the API Gateway resource to require authorization and respond with a JSON model representing compact jurisdictions.
        """
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
        """
        Adds a public GET endpoint for retrieving jurisdictions associated with a compact.
        
        This endpoint is accessible without authorization and returns a JSON response
        containing jurisdiction data for a specified compact.
        """
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
        """
        Adds a GET endpoint for staff users to retrieve compact configuration data.
        
        Configures the /v1/compacts/{compact} API path with Lambda integration, requiring authorization and returning a JSON response model for compact configuration.
        """
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
        """
        Adds a PUT endpoint for staff users to update compact configuration.
        
        Configures the /v1/compacts/{compact} PUT method with Lambda integration, requiring admin authorization and a validated JSON request body for updating compact configuration. Responds with a generic message model on success.
        """
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
        """
        Adds a GET endpoint for staff users to retrieve jurisdiction configuration for a specific compact.
        
        Configures the /v1/compacts/{compact}/jurisdictions/{jurisdiction} GET method with Lambda integration, authorization, and response modeling.
        """
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
        """
        Adds a PUT endpoint for updating jurisdiction configuration for a specific compact.
        
        Configures the /v1/compacts/{compact}/jurisdictions/{jurisdiction} path to allow staff users with admin authorization to update jurisdiction configuration using a validated JSON request body. Responds with a generic message response model upon success.
        """
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
