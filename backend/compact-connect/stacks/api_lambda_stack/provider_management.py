from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, CfnAlarm, ComparisonOperator, Metric, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import EventBus
from aws_cdk.aws_iam import Policy, PolicyStatement
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack

from common_constructs.python_function import PythonFunction
from stacks import api_lambda_stack as als
from stacks import persistent_stack as ps


class ProviderManagementLambdas:
    def __init__(
        self,
        *,
        scope: Stack,
        persistent_stack: ps.PersistentStack,
        data_event_bus: EventBus,
        api_lambda_stack: als.ApiLambdaStack,
    ) -> None:
        self.scope = scope
        self.persistent_stack = persistent_stack
        self.data_event_bus = data_event_bus

        self.stack: Stack = Stack.of(scope)
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
            'PROVIDER_USER_BUCKET_NAME': persistent_stack.provider_users_bucket.bucket_name,
            **self.stack.common_env_vars,
        }

        # Create all the lambda handlers
        self.get_provider_handler = self._get_provider_handler(lambda_environment)
        api_lambda_stack.log_groups.append(self.get_provider_handler.log_group)
        self.query_providers_handler = self._query_providers_handler(lambda_environment)
        api_lambda_stack.log_groups.append(self.query_providers_handler.log_group)
        self.get_provider_ssn_handler = self._get_provider_ssn_handler(lambda_environment)
        api_lambda_stack.log_groups.append(self.get_provider_ssn_handler.log_group)
        self.deactivate_privilege_handler = self._deactivate_privilege_handler(lambda_environment)
        api_lambda_stack.log_groups.append(self.deactivate_privilege_handler.log_group)
        self.provider_encumbrance_handler = self._add_provider_encumbrance_handler(lambda_environment)
        api_lambda_stack.log_groups.append(self.provider_encumbrance_handler.log_group)

    def _get_provider_handler(
        self,
        lambda_environment: dict,
    ) -> PythonFunction:
        handler = PythonFunction(
            self.scope,
            'GetProviderHandler',
            description='Get provider handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'providers.py'),
            handler='get_provider',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )
        self.persistent_stack.shared_encryption_key.grant_decrypt(handler)
        self.persistent_stack.provider_table.grant_read_data(handler)
        self.persistent_stack.provider_users_bucket.grant_read(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
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
        lambda_environment: dict,
    ) -> PythonFunction:
        handler = PythonFunction(
            self.scope,
            'QueryProvidersHandler',
            description='Query providers handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'providers.py'),
            handler='query_providers',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )
        self.persistent_stack.shared_encryption_key.grant_decrypt(handler)
        self.persistent_stack.provider_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(handler.role),
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
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
        return handler

    def _get_provider_ssn_handler(
        self,
        lambda_environment: dict,
    ) -> PythonFunction:
        """Create and configure the Lambda handler for retrieving a provider's SSN."""
        handler = PythonFunction(
            self.scope,
            'GetProviderSSNHandler',
            description='Get provider SSN handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'providers.py'),
            handler='get_provider_ssn',
            role=self.persistent_stack.ssn_table.api_query_role,
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )
        # The lambda needs to read providers from the provider table and the SSN from the ssn table
        # Though, ssn table access is granted via resource policies on the table and key so `.grant()`
        # calls are not needed here.

        # Grant permissions for rate limiting, provider table access, and staff user pool access
        self.persistent_stack.rate_limiting_table.grant_read_write_data(handler)
        self.persistent_stack.provider_table.grant_read_data(handler)
        self.persistent_stack.staff_users.grant(handler, 'cognito-idp:AdminDisableUser')

        # Add permission for the lambda to update its own concurrency setting
        function_arn = handler.function_arn
        handler.role.attach_inline_policy(
            Policy(
                self.scope,
                'PutFunctionConcurrency',
                statements=[
                    PolicyStatement(
                        actions=['lambda:PutFunctionConcurrency'],
                        resources=[function_arn],
                    )
                ],
            )
        )

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
            handler,
            'ReadSSNAnomalyAlarm',
            alarm_description=f'{handler.node.path} read-ssn anomaly detection. The GET provider SSN endpoint has been'
            f'called an irregular number of times. Investigation required to ensure ssn endpoint is '
            f'not being abused.',
            comparison_operator='GreaterThanUpperThreshold',
            evaluation_periods=1,
            treat_missing_data='notBreaching',
            actions_enabled=True,
            alarm_actions=[self.persistent_stack.alarm_topic.node.default_child.ref],
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
            handler,
            'SSNReadsRateLimitedAlarm',
            metric=ssn_rate_limited_count_metric,
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=f'{handler.node.path} ssn reads rate-limited alarm. The GET provider SSN endpoint has '
            f'been invoked more than an expected threshold within a 24 hour period. Investigation is '
            f'required to ensure access is not the result of abuse.',
        )
        self.ssn_rate_limited_alarm.add_alarm_action(SnsAction(self.persistent_stack.alarm_topic))

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
            handler,
            'SSNEndpointDisabledAlarm',
            metric=ssn_endpoint_disabled_count_metric,
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=f'{handler.node.path} SECURITY ALERT: SSN ENDPOINT DISABLED. The GET provider SSN '
            'endpoint has been disabled due to excessive requests. Immediate investigation required. '
            'Endpoint will need to be manually reactivated before any further requests can be '
            'processed.',
        )
        self.ssn_endpoint_disabled_alarm.add_alarm_action(SnsAction(self.persistent_stack.alarm_topic))

        return handler

    def _deactivate_privilege_handler(
        self,
        lambda_environment: dict,
    ) -> PythonFunction:
        """Create and configure the Lambda handler for deactivating a provider's privilege."""
        handler = PythonFunction(
            self.scope,
            'DeactivatePrivilegeHandler',
            description='Deactivate provider privilege handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'privileges.py'),
            handler='deactivate_privilege',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )
        self.persistent_stack.provider_table.grant_read_write_data(handler)
        self.persistent_stack.staff_users.user_table.grant_read_data(handler)
        self.data_event_bus.grant_put_events_to(handler)
        self.persistent_stack.email_notification_service_lambda.grant_invoke(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(handler.role),
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read/write '
                    'and is scoped to one table and event bus.',
                },
            ],
        )
        return handler

    def _add_provider_encumbrance_handler(
        self,
        lambda_environment: dict,
    ) -> PythonFunction:
        """Create and configure the Lambda handler for encumbering a provider's privilege or license."""
        handler = PythonFunction(
            self.scope,
            'ProviderEncumbranceHandler',
            description='Provider encumbrance handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'encumbrance.py'),
            handler='encumbrance_handler',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )
        self.persistent_stack.provider_table.grant_read_write_data(handler)
        self.persistent_stack.staff_users.user_table.grant_read_data(handler)
        self.data_event_bus.grant_put_events_to(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(handler.role),
            path=f'{handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs to read/write '
                    'and is scoped to the needed tables and event bus.',
                },
            ],
        )
        return handler
