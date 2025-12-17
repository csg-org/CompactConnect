from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodOptions, MethodResponse, Resource
from aws_cdk.aws_cloudwatch import (
    Alarm,
    ComparisonOperator,
    Metric,
    TreatMissingData,
)
from aws_cdk.aws_cloudwatch_actions import SnsAction

from common_constructs.cc_api import CCApi
from common_constructs.python_function import PythonFunction
from stacks.api_lambda_stack import ApiLambdaStack

from .api_model import ApiModel


class ProviderManagement:
    """
    These endpoints are used by staff users to view and manage provider records
    """

    def __init__(
        self,
        *,
        resource: Resource,
        method_options: MethodOptions,
        admin_method_options: MethodOptions,
        ssn_method_options: MethodOptions,
        api_model: ApiModel,
        privilege_history_function: PythonFunction,
        api_lambda_stack: ApiLambdaStack,
    ):
        super().__init__()

        self.resource = resource
        self.api: CCApi = resource.api
        self.api_model = api_model

        # Create the nested resources used by endpoints
        self.provider_resource = self.resource.add_resource('{providerId}')
        self.privileges_resource = self.provider_resource.add_resource('privileges')
        self.privilege_jurisdiction_resource = self.privileges_resource.add_resource('jurisdiction').add_resource(
            '{jurisdiction}'
        )
        self.privilege_jurisdiction_license_type_resource = self.privilege_jurisdiction_resource.add_resource(
            'licenseType'
        ).add_resource('{licenseType}')

        self.licenses_resource = self.provider_resource.add_resource('licenses')
        self.license_jurisdiction_resource = self.licenses_resource.add_resource('jurisdiction').add_resource(
            '{jurisdiction}'
        )
        self.license_jurisdiction_license_type_resource = self.license_jurisdiction_resource.add_resource(
            'licenseType'
        ).add_resource('{licenseType}')

        self._add_query_providers(
            method_options=method_options,
            query_providers_handler=api_lambda_stack.provider_management_lambdas.query_providers_handler,
        )
        self._add_get_provider(
            method_options=method_options,
            get_provider_handler=api_lambda_stack.provider_management_lambdas.get_provider_handler,
        )
        self._add_get_provider_ssn(
            method_options=ssn_method_options,
            get_provider_ssn_handler=api_lambda_stack.provider_management_lambdas.get_provider_ssn_handler,
        )
        self._add_deactivate_privilege(
            method_options=admin_method_options,
            deactivate_privilege_handler=api_lambda_stack.provider_management_lambdas.deactivate_privilege_handler,
        )

        self._add_encumber_privilege(
            method_options=admin_method_options,
            provider_encumbrance_handler=api_lambda_stack.provider_management_lambdas.provider_encumbrance_handler,
        )

        self._add_encumber_license(
            method_options=admin_method_options,
            provider_encumbrance_handler=api_lambda_stack.provider_management_lambdas.provider_encumbrance_handler,
        )

        self._add_investigation_privilege(
            method_options=admin_method_options,
            investigation_handler=api_lambda_stack.provider_management_lambdas.provider_investigation_handler,
        )

        self._add_investigation_license(
            method_options=admin_method_options,
            investigation_handler=api_lambda_stack.provider_management_lambdas.provider_investigation_handler,
        )

        self._add_get_privilege_history(
            method_options=method_options,
            privilege_history_function=privilege_history_function,
        )

        self._add_military_audit(
            method_options=admin_method_options,
            military_audit_handler=api_lambda_stack.provider_management_lambdas.military_audit_handler,
        )

    def _add_get_provider(
        self,
        method_options: MethodOptions,
        get_provider_handler: PythonFunction,
    ):
        self.provider_resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.provider_response_model},
                ),
            ],
            integration=LambdaIntegration(get_provider_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _add_query_providers(
        self,
        method_options: MethodOptions,
        query_providers_handler: PythonFunction,
    ):
        query_resource = self.resource.add_resource('query')

        query_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.query_providers_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.query_providers_response_model},
                ),
            ],
            integration=LambdaIntegration(query_providers_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _add_get_provider_ssn(
        self,
        method_options: MethodOptions,
        get_provider_ssn_handler: PythonFunction,
    ):
        """Add GET /providers/{providerId}/ssn endpoint to retrieve a provider's SSN."""
        # Add the SSN endpoint as a sub-resource of the provider
        self.ssn_resource = self.provider_resource.add_resource('ssn')
        self.ssn_resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.get_provider_ssn_response_model},
                ),
            ],
            integration=LambdaIntegration(get_provider_ssn_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

        # Add an alarm for 4xx responses from the SSN endpoint
        self.ssn_api_throttling_alarm = Alarm(
            self.api,
            'SSNApi4XXAlarm',
            alarm_description=f'{self.api.node.path} SECURITY ALERT: Potential abuse detected - '
            'Excessive 4xx errors triggered on GET provider SSN endpoint. '
            'Immediate investigation required.',
            metric=Metric(
                namespace='AWS/ApiGateway',
                metric_name='4XXError',
                dimensions_map={
                    'ApiName': self.api.rest_api_name,
                    'Stage': self.api.deployment_stage.stage_name,
                    'Resource': self.ssn_resource.path,
                    'Method': 'GET',
                },
                statistic='Sum',
                period=Duration.minutes(5),
            ),
            evaluation_periods=1,
            threshold=100,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )
        self.ssn_api_throttling_alarm.add_alarm_action(SnsAction(self.api.alarm_topic))

    def _add_deactivate_privilege(
        self,
        method_options: MethodOptions,
        deactivate_privilege_handler: PythonFunction,
    ):
        """Add POST /providers/{providerId}/privileges/jurisdiction/{jurisdiction}
        /licenseType/{licenseType}/deactivate endpoint."""
        deactivate_resource = self.privilege_jurisdiction_license_type_resource.add_resource('deactivate')

        # Create a metric to track privilege deactivation notification failures
        privilege_deactivation_notification_failed_metric = Metric(
            namespace='compact-connect',
            metric_name='privilege-deactivation-notification-failed',
            statistic='Sum',
            period=Duration.minutes(5),
            dimensions_map={'service': 'common'},
        )

        # Create an alarm that will fire if any privilege deactivation notification fails
        self.privilege_deactivation_notification_failed_alarm = Alarm(
            self.api,
            'PrivilegeDeactivationNotificationFailedAlarm',
            metric=privilege_deactivation_notification_failed_metric,
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=f'{self.api.node.path} Privilege deactivation notification failed. '
            f'One or more notifications to providers or jurisdictions failed to send during privilege deactivation. '
            f'Investigation required to ensure all parties have been properly notified.',
        )
        self.privilege_deactivation_notification_failed_alarm.add_alarm_action(SnsAction(self.api.alarm_topic))

        deactivate_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_privilege_deactivation_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(deactivate_privilege_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _add_encumber_privilege(
        self,
        method_options: MethodOptions,
        provider_encumbrance_handler: PythonFunction,
    ):
        """Add POST /providers/{providerId}/privileges/jurisdiction/{jurisdiction}
        /licenseType/{licenseType}/encumbrance endpoint."""
        self.encumbrance_privilege_resource = self.privilege_jurisdiction_license_type_resource.add_resource(
            'encumbrance'
        )
        self.encumbrance_privilege_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_privilege_encumbrance_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(provider_encumbrance_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

        # Add PATCH method for lifting privilege encumbrances - now with encumbranceId in path
        self.encumbrance_privilege_id_resource = self.encumbrance_privilege_resource.add_resource('{encumbranceId}')
        self.encumbrance_privilege_id_resource.add_method(
            'PATCH',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.patch_privilege_encumbrance_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(provider_encumbrance_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _add_encumber_license(
        self,
        method_options: MethodOptions,
        provider_encumbrance_handler: PythonFunction,
    ):
        """Add POST /providers/{providerId}/licenses/jurisdiction/{jurisdiction}
        /licenseType/{licenseType}/encumbrance endpoint."""
        self.encumbrance_license_resource = self.license_jurisdiction_license_type_resource.add_resource('encumbrance')
        self.encumbrance_license_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_license_encumbrance_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(provider_encumbrance_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

        # Add PATCH method for lifting license encumbrances - now with encumbranceId in path
        self.encumbrance_license_id_resource = self.encumbrance_license_resource.add_resource('{encumbranceId}')
        self.encumbrance_license_id_resource.add_method(
            'PATCH',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.patch_license_encumbrance_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(provider_encumbrance_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _add_investigation_privilege(
        self,
        method_options: MethodOptions,
        investigation_handler: PythonFunction,
    ):
        """Add POST /providers/{providerId}/privileges/jurisdiction/{jurisdiction}
        /licenseType/{licenseType}/investigation endpoint."""
        self.investigation_privilege_resource = self.privilege_jurisdiction_license_type_resource.add_resource(
            'investigation'
        )
        self.investigation_privilege_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_privilege_investigation_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(investigation_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

        # Add PATCH method for closing privilege investigations - now with investigationId in path
        self.investigation_privilege_id_resource = self.investigation_privilege_resource.add_resource(
            '{investigationId}'
        )
        self.investigation_privilege_id_resource.add_method(
            'PATCH',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.patch_privilege_investigation_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(investigation_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _add_investigation_license(
        self,
        method_options: MethodOptions,
        investigation_handler: PythonFunction,
    ):
        """Add POST /providers/{providerId}/licenses/jurisdiction/{jurisdiction}
        /licenseType/{licenseType}/investigation endpoint."""
        self.investigation_license_resource = self.license_jurisdiction_license_type_resource.add_resource(
            'investigation'
        )
        self.investigation_license_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.post_license_investigation_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(investigation_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

        # Add PATCH method for closing license investigations - now with investigationId in path
        self.investigation_license_id_resource = self.investigation_license_resource.add_resource('{investigationId}')
        self.investigation_license_id_resource.add_method(
            'PATCH',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.patch_license_investigation_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(investigation_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _add_get_privilege_history(
        self,
        method_options: MethodOptions,
        privilege_history_function: PythonFunction,
    ):
        self.privilege_history_resource = self.privilege_jurisdiction_license_type_resource.add_resource('history')

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
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _add_military_audit(
        self,
        method_options: MethodOptions,
        military_audit_handler: PythonFunction,
    ):
        """Add PATCH /providers/{providerId}/militaryAudit endpoint for compact admins to audit
        military affiliation records."""
        self.military_audit_resource = self.provider_resource.add_resource('militaryAudit')
        self.military_audit_resource.add_method(
            'PATCH',
            request_validator=self.api.parameter_body_validator,
            request_models={'application/json': self.api_model.patch_military_audit_request_model},
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.message_response_model},
                ),
            ],
            integration=LambdaIntegration(military_audit_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )
