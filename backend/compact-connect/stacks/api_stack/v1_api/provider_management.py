from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodOptions, MethodResponse, Resource
from aws_cdk.aws_cloudwatch import (
    Alarm,
    CfnAlarm,
    ComparisonOperator,
    Metric,
    TreatMissingData,
)
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_events import EventBus
from aws_cdk.aws_iam import Policy, PolicyStatement
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from common_constructs.nodejs_function import NodejsFunction
from common_constructs.python_function import PythonFunction
from common_constructs.ssm_parameter_utility import SSMParameterUtility
from common_constructs.stack import Stack

from stacks import persistent_stack as ps

# Importing module level to allow lazy loading for typing
from stacks.api_stack import cc_api
from stacks.persistent_stack import ProviderTable, RateLimitingTable, SSNTable, StaffUsers

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
        persistent_stack: ps.PersistentStack,
        api_model: ApiModel,
    ):
        super().__init__()

        self.resource = resource
        self.api: cc_api.CCApi = resource.api
        self.api_model = api_model

        stack: Stack = Stack.of(resource)

        # Load the data event bus from SSM parameter instead of direct reference
        data_event_bus = SSMParameterUtility.load_data_event_bus_from_ssm_parameter(stack)

        lambda_environment = {
            'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': persistent_stack.provider_table.provider_fam_giv_mid_index_name,
            'PROV_DATE_OF_UPDATE_INDEX_NAME': persistent_stack.provider_table.provider_date_of_update_index_name,
            'SSN_TABLE_NAME': persistent_stack.ssn_table.table_name,
            'SSN_INDEX_NAME': persistent_stack.ssn_table.ssn_index_name,
            'EVENT_BUS_NAME': data_event_bus.event_bus_name,
            'RATE_LIMITING_TABLE_NAME': persistent_stack.rate_limiting_table.table_name,
            'USER_POOL_ID': persistent_stack.staff_users.user_pool_id,
            'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': persistent_stack.email_notification_service_lambda.function_name,
            'USERS_TABLE_NAME': persistent_stack.staff_users.user_table.table_name,
            **stack.common_env_vars,
        }

        # Create the nested resources used by endpoints
        self.provider_resource = self.resource.add_resource('{providerId}')
        self.privileges_resource = self.provider_resource.add_resource('privileges')
        self.privilege_jurisdiction_resource = self.privileges_resource.add_resource('jurisdiction').add_resource('{jurisdiction}')
        self.privilege_jurisdiction_license_type_resource = self.privilege_jurisdiction_resource.add_resource('licenseType').add_resource('{licenseType}')
        self.licenses_resource = self.provider_resource.add_resource('licenses')
        self.license_jurisdiction_resource = self.licenses_resource.add_resource('jurisdiction').add_resource('{jurisdiction}')
        self.license_jurisdiction_license_type_resource = self.license_jurisdiction_resource.add_resource('licenseType').add_resource('{licenseType}')

        self._add_query_providers(
            method_options=method_options,
            data_encryption_key=persistent_stack.shared_encryption_key,
            provider_data_table=persistent_stack.provider_table,
            lambda_environment=lambda_environment,
        )
        self._add_get_provider(
            method_options=method_options,
            data_encryption_key=persistent_stack.shared_encryption_key,
            provider_data_table=persistent_stack.provider_table,
            lambda_environment=lambda_environment,
        )
        self._add_get_provider_ssn(
            method_options=ssn_method_options,
            ssn_table=persistent_stack.ssn_table,
            staff_user_pool=persistent_stack.staff_users,
            rate_limiting_table=persistent_stack.rate_limiting_table,
            provider_table=persistent_stack.provider_table,
            lambda_environment=lambda_environment,
        )
        self._add_deactivate_privilege(
            method_options=admin_method_options,
            provider_data_table=persistent_stack.provider_table,
            event_bus=data_event_bus,
            email_service_lambda=persistent_stack.email_notification_service_lambda,
            staff_users_table=persistent_stack.staff_users.user_table,
            lambda_environment=lambda_environment,
        )

        self.provider_encumbrance_handler = self._add_provider_encumbrance_handler(
            provider_data_table=persistent_stack.provider_table,
            staff_users_table=persistent_stack.staff_users.user_table,
            event_bus=data_event_bus,
            lambda_environment=lambda_environment,
        )

        self._add_encumber_privilege(
            method_options=admin_method_options
        )

        self._add_encumber_license(
            method_options=admin_method_options
        )

    def _add_get_provider(
        self,
        method_options: MethodOptions,
        data_encryption_key: IKey,
        provider_data_table: ProviderTable,
        lambda_environment: dict,
    ):
        self.get_provider_handler = self._get_provider_handler(
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(self.get_provider_handler.log_group)

        self.provider_resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.provider_response_model},
                ),
            ],
            integration=LambdaIntegration(self.get_provider_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _add_query_providers(
        self,
        method_options: MethodOptions,
        data_encryption_key: IKey,
        provider_data_table: ProviderTable,
        lambda_environment: dict,
    ):
        query_resource = self.resource.add_resource('query')

        handler = self._query_providers_handler(
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(handler.log_group)

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
            integration=LambdaIntegration(handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _get_provider_handler(
        self,
        data_encryption_key: IKey,
        provider_data_table: ProviderTable,
        lambda_environment: dict,
    ) -> PythonFunction:
        stack = Stack.of(self.resource)
        handler = PythonFunction(
            self.resource,
            'GetProviderHandler',
            description='Get provider handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'providers.py'),
            handler='get_provider',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )
        data_encryption_key.grant_decrypt(handler)
        provider_data_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
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

    def _query_providers_handler(
        self,
        data_encryption_key: IKey,
        provider_data_table: ProviderTable,
        lambda_environment: dict,
    ) -> PythonFunction:
        self.query_providers_handler = PythonFunction(
            self.resource,
            'QueryProvidersHandler',
            description='Query providers handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'providers.py'),
            handler='query_providers',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )
        data_encryption_key.grant_decrypt(self.query_providers_handler)
        provider_data_table.grant_read_data(self.query_providers_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(self.query_providers_handler.role),
            path=f'{self.query_providers_handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'appliesTo': [
                        'Action::kms:GenerateDataKey*',
                        'Action::kms:ReEncrypt*',
                        'Resource::<ProviderTableEC5D0597.Arn>/index/*',
                    ],
                    'reason': 'The actions in this policy are specifically what this lambda needs to read '
                    'and is scoped to one table and encryption key.',
                },
            ],
        )
        return self.query_providers_handler

    def _add_get_provider_ssn(
        self,
        method_options: MethodOptions,
        ssn_table: SSNTable,
        staff_user_pool: StaffUsers,
        rate_limiting_table: RateLimitingTable,
        provider_table: ProviderTable,
        lambda_environment: dict,
    ):
        """Add GET /providers/{providerId}/ssn endpoint to retrieve a provider's SSN."""
        handler = self._get_provider_ssn_handler(
            ssn_table=ssn_table,
            lambda_environment=lambda_environment,
        )
        # these permissions are needed to read and write items on the rate-limiting table
        rate_limiting_table.grant_read_write_data(handler)
        # these permissions are needed to query provider records on the provider table
        provider_table.grant_read_data(handler)
        # here we grant the lambda the ability to disable staff users if they exceed the rate limit
        staff_user_pool.grant(handler, 'cognito-idp:AdminDisableUser')
        self.api.log_groups.append(handler.log_group)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(handler.role),
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The wildcard actions in this policy are scoped to the rate-limiting table and '
                    'the provider data table.',
                },
            ],
        )

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
            integration=LambdaIntegration(handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

        # Create a metric to track how many times this endpoint has been invoked with a day
        daily_read_ssn_count_metric = Metric(
            namespace='compact-connect',
            metric_name='read-ssn',
            statistic='SampleCount',
            period=Duration.days(1),
            dimensions_map={'service': 'common'},
        )

        # We'll monitor longer access patterns to detect anomalies, over time
        # The L2 construct, Alarm, doesn't yet support Anomaly Detection as a configuration
        # so we're using the L1 construct, CfnAlarm
        # This anomaly detector scans the count of requests to the ssn endpoint by
        # the daily_read_ssn_count_metric and uses machine-learning and pattern recognition to
        # establish baselines of typical usage.
        # See https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/LogsAnomalyDetection.html
        self.ssn_anomaly_detection_alarm = CfnAlarm(
            self.api,
            'ReadSSNAnomalyAlarm',
            alarm_description=f'{self.api.node.path} read-ssn anomaly detection. The GET provider SSN endpoint has been'
            f'called an irregular number of times. Investigation required to ensure ssn endpoint is '
            f'not being abused.',
            comparison_operator='GreaterThanUpperThreshold',
            evaluation_periods=1,
            treat_missing_data='notBreaching',
            actions_enabled=True,
            alarm_actions=[self.api.alarm_topic.node.default_child.ref],
            metrics=[
                CfnAlarm.MetricDataQueryProperty(id='ad1', expression='ANOMALY_DETECTION_BAND(m1, 2)'),
                CfnAlarm.MetricDataQueryProperty(
                    id='m1',
                    metric_stat=CfnAlarm.MetricStatProperty(
                        metric=CfnAlarm.MetricProperty(
                            metric_name=daily_read_ssn_count_metric.metric_name,
                            namespace=daily_read_ssn_count_metric.namespace,
                            dimensions=[CfnAlarm.DimensionProperty(name='service', value='common')],
                        ),
                        period=3600,
                        stat='SampleCount',
                    ),
                ),
            ],
            threshold_metric_id='ad1',
        )

        # Create a metric to track if any user is rate-limited while calling this endpoint
        ssn_rate_limited_count_metric = Metric(
            namespace='compact-connect',
            metric_name='rate-limited-ssn-access',
            statistic='SampleCount',
            period=Duration.minutes(5),
            dimensions_map={'service': 'common'},
        )

        # This alarm will fire if any user is rate-limited by this endpoint
        # This will help us determine if the limit needs to be raised or detect early abuse
        self.ssn_rate_limited_alarm = Alarm(
            self.api,
            'SSNReadsRateLimitedAlarm',
            metric=ssn_rate_limited_count_metric,
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=f'{self.api.node.path} ssn reads rate-limited alarm. The GET provider SSN endpoint has '
            f'been invoked more than an expected threshold within a 24 hour period. Investigation is required to ensure'
            f' access is not the result of abuse.',
        )
        self.ssn_rate_limited_alarm.add_alarm_action(SnsAction(self.api.alarm_topic))

        # Create a metric to track if ssn endpoint has been disabled due to excessive requests
        ssn_endpoint_disabled_count_metric = Metric(
            namespace='compact-connect',
            metric_name='ssn-endpoint-disabled',
            statistic='SampleCount',
            period=Duration.minutes(5),
            dimensions_map={'service': 'common'},
        )
        # This alarm will fire if the ssn endpoint hits our global threshold and is disabled (concurrency set to 0)
        self.ssn_endpoint_disabled_alarm = Alarm(
            self.api,
            'SSNEndpointDisabledAlarm',
            metric=ssn_endpoint_disabled_count_metric,
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=f'{self.api.node.path} SECURITY ALERT: SSN ENDPOINT DISABLED. The GET provider SSN '
            'endpoint has been disabled due to excessive requests. Immediate investigation required. '
            'Endpoint will need to be manually reactivated before any further requests can be '
            'processed.',
        )
        self.ssn_endpoint_disabled_alarm.add_alarm_action(SnsAction(self.api.alarm_topic))

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

    def _get_provider_ssn_handler(
        self,
        ssn_table: SSNTable,
        lambda_environment: dict,
    ) -> PythonFunction:
        """Create and configure the Lambda handler for retrieving a provider's SSN."""
        self.get_provider_ssn_handler = PythonFunction(
            self.resource,
            'GetProviderSSNHandler',
            description='Get provider SSN handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'providers.py'),
            handler='get_provider_ssn',
            role=ssn_table.api_query_role,
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )
        # The lambda needs to read providers from the provider table and the SSN from the ssn table
        # Though, ssn table access is granted via resource policies on the table and key so `.grant()`
        # calls are not needed here.

        # Add permission for the lambda to update its own concurrency setting
        function_arn = self.get_provider_ssn_handler.function_arn
        self.get_provider_ssn_handler.role.attach_inline_policy(
            Policy(
                self.resource,
                'PutFunctionConcurrency',
                statements=[
                    PolicyStatement(
                        actions=['lambda:PutFunctionConcurrency'],
                        resources=[function_arn],
                    )
                ],
            )
        )
        return self.get_provider_ssn_handler

    def _add_deactivate_privilege(
        self,
        method_options: MethodOptions,
        event_bus: EventBus,
        provider_data_table: ProviderTable,
        email_service_lambda: NodejsFunction,
        staff_users_table: Table,
        lambda_environment: dict,
    ):
        """Add POST /providers/{providerId}/privileges/jurisdiction/{jurisdiction}
        /licenseType/{licenseType}/deactivate endpoint."""
        handler = self._deactivate_privilege_handler(
            provider_data_table=provider_data_table,
            event_bus=event_bus,
            email_service_lambda=email_service_lambda,
            staff_users_table=staff_users_table,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(handler.log_group)

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
            integration=LambdaIntegration(handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _deactivate_privilege_handler(
        self,
        provider_data_table: ProviderTable,
        event_bus: EventBus,
        email_service_lambda: NodejsFunction,
        staff_users_table: Table,
        lambda_environment: dict,
    ) -> PythonFunction:
        """Create and configure the Lambda handler for deactivating a provider's privilege."""
        self.deactivate_privilege_handler = PythonFunction(
            self.resource,
            'DeactivatePrivilegeHandler',
            description='Deactivate provider privilege handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'privileges.py'),
            handler='deactivate_privilege',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )
        provider_data_table.grant_read_write_data(self.deactivate_privilege_handler)
        staff_users_table.grant_read_data(self.deactivate_privilege_handler)
        event_bus.grant_put_events_to(self.deactivate_privilege_handler)
        email_service_lambda.grant_invoke(self.deactivate_privilege_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(self.deactivate_privilege_handler.role),
            path=f'{self.deactivate_privilege_handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read/write '
                    'and is scoped to one table and event bus.',
                },
            ],
        )
        return self.deactivate_privilege_handler

    def _add_provider_encumbrance_handler(
        self,
        provider_data_table: ProviderTable,
        staff_users_table: Table,
        event_bus: EventBus,
        lambda_environment: dict,
    ) -> PythonFunction:
        """Create and configure the Lambda handler for deactivating a provider's privilege."""
        encumbrance_handler = PythonFunction(
            self.resource,
            'ProviderEncumbranceHandler',
            description='Provider encumbrance handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'encumbrance.py'),
            handler='encumbrance_handler',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )
        provider_data_table.grant_read_write_data(encumbrance_handler)
        staff_users_table.grant_read_data(encumbrance_handler)
        event_bus.grant_put_events_to(encumbrance_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(encumbrance_handler.role),
            path=f'{encumbrance_handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read/write '
                    'and is scoped to the needed tables and event bus.',
                },
            ],
        )
        return encumbrance_handler

    def _add_encumber_privilege(
        self,
        method_options: MethodOptions,
    ):
        """Add POST /providers/{providerId}/privileges/jurisdiction/{jurisdiction}
        /licenseType/{licenseType}/encumbrance endpoint."""
        self.encumbrance_privilege_resource = self.privilege_jurisdiction_license_type_resource.add_resource('encumbrance')
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
            integration=LambdaIntegration(self.provider_encumbrance_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )

    def _add_encumber_license(
        self,
        method_options: MethodOptions,
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
            integration=LambdaIntegration(self.provider_encumbrance_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorization_type=method_options.authorization_type,
            authorizer=method_options.authorizer,
            authorization_scopes=method_options.authorization_scopes,
        )
