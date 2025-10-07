from __future__ import annotations

from aws_cdk.aws_apigateway import LambdaIntegration, MethodResponse, Resource

from common_constructs.cc_api import CCApi
from stacks.api_lambda_stack import ApiLambdaStack

from .api_model import ApiModel


class Attestations:
    def __init__(
        self,
        *,
        resource: Resource,
        api_lambda_stack: ApiLambdaStack,
        api_model: ApiModel,
    ):
        super().__init__()

        self.resource = resource
        self.api: CCApi = resource.api
        self.api_model = api_model
        self.log_groups = []

        # GET /v1/compacts/{compact}/attestations/{attestationId}
        self.attestation_id_resource = self.resource.add_resource('{attestationId}')
        self._add_get_attestation(
            api_lambda_stack=api_lambda_stack,
        )

        self.api.log_groups.extend(self.log_groups)

    def _add_get_attestation(
        self,
        api_lambda_stack: ApiLambdaStack,
    ):
        handler = api_lambda_stack.attestations_lambdas.attestations_handler
        self.log_groups.append(handler.log_group)

        self.attestation_id_resource.add_method(
            'GET',
            LambdaIntegration(handler),
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_attestations_response_model},
                ),
            ],
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )
