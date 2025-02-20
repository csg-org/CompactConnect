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
from aws_cdk.aws_events import EventBus
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

# Importing module level to allow lazy loading for typing
from stacks.api_stack import cc_api
from stacks.persistent_stack import ProviderTable, SSNTable

from .api_model import ApiModel


class QueryProviders:
    def __init__(
        self,
        *,
        resource: Resource,
        method_options: MethodOptions,
        admin_method_options: MethodOptions,
        ssn_method_options: MethodOptions,
        event_bus: EventBus,
        data_encryption_key: IKey,
        ssn_table: SSNTable,
        provider_data_table: ProviderTable,
        api_model: ApiModel,
    ):
        super().__init__()

        self.resource = resource
        self.api: cc_api.CCApi = resource.api
        self.api_model = api_model

        stack: Stack = Stack.of(resource)
        lambda_environment = {
            'PROVIDER_TABLE_NAME': provider_data_table.table_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': provider_data_table.provider_fam_giv_mid_index_name,
            'PROV_DATE_OF_UPDATE_INDEX_NAME': provider_data_table.provider_date_of_update_index_name,
            'SSN_TABLE_NAME': ssn_table.table_name,
            'SSN_INDEX_NAME': ssn_table.ssn_index_name,
            **stack.common_env_vars,
        }

        self._add_query_providers(
            method_options=method_options,
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment,
        )
        self._add_get_provider(
            method_options=method_options,
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment,
        )
        self._add_get_provider_ssn(
            method_options=ssn_method_options,
            ssn_table=ssn_table,
            lambda_environment=lambda_environment,
        )
        self._add_deactivate_privilege(
            method_options=admin_method_options,
            provider_data_table=provider_data_table,
            event_bus=event_bus,
            lambda_environment=lambda_environment,
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

        self.provider_resource = self.resource.add_resource('{providerId}')
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
        lambda_environment: dict,
    ):
        """Add GET /providers/{providerId}/ssn endpoint to retrieve a provider's SSN."""
        handler = self._get_provider_ssn_handler(
            ssn_table=ssn_table,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(handler.log_group)

        # Add the SSN endpoint as a sub-resource of the provider
        self.provider_resource.add_resource('ssn').add_method(
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

        # Create a metric
        metric = Metric(
            namespace='compact-connect',
            metric_name='read-ssn',
            statistic='SampleCount',
            period=Duration.hours(1),
            dimensions_map={'service': 'common'},
        )

        # We'll monitor longer access patterns to detect anomalies, over time
        # The L2 construct, Alarm, doesn't yet support Anomaly Detection as a configuration
        # so we're using the L1 construct, CfnAlarm
        self.ssn_anomaly_detection_alarm = CfnAlarm(
            self.api,
            'ReadSSNAnomalyAlarm',
            alarm_description=f'{self.api.node.path} read-ssn anomaly detection',
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
                            metric_name=metric.metric_name,
                            namespace=metric.namespace,
                            dimensions=[CfnAlarm.DimensionProperty(name='service', value='common')],
                        ),
                        period=3600,
                        stat='SampleCount',
                    ),
                ),
            ],
            threshold_metric_id='ad1',
        )

        # We'll also set a flat maximum access rate of 5 reads per hour to alarm on
        self.max_ssn_reads_alarm = Alarm(
            self.api,
            'MaxSSNReadsAlarm',
            metric=metric,
            threshold=5,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(f'{self.api.node.path} max ssn reads alarm'),
        )
        self.max_ssn_reads_alarm.add_alarm_action(SnsAction(self.api.alarm_topic))

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

        return self.get_provider_ssn_handler

    def _add_deactivate_privilege(
        self,
        method_options: MethodOptions,
        event_bus: EventBus,
        provider_data_table: ProviderTable,
        lambda_environment: dict,
    ):
        """Add POST /providers/{providerId}/privileges/jurisdiction/{jurisdiction}
        /licenseType/{licenseType}/deactivate endpoint."""
        handler = self._deactivate_privilege_handler(
            provider_data_table=provider_data_table,
            event_bus=event_bus,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(handler.log_group)

        # Create the nested resources for the path
        privileges_resource = self.provider_resource.add_resource('privileges')
        jurisdiction_resource = privileges_resource.add_resource('jurisdiction').add_resource('{jurisdiction}')
        license_type_resource = jurisdiction_resource.add_resource('licenseType').add_resource('{licenseType}')
        deactivate_resource = license_type_resource.add_resource('deactivate')

        deactivate_resource.add_method(
            'POST',
            request_validator=self.api.parameter_body_validator,
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
        event_bus.grant_put_events_to(self.deactivate_privilege_handler)

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
