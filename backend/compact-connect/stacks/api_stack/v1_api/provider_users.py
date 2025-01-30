from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_apigateway import LambdaIntegration, MethodResponse, Resource
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, MathExpression, Metric, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_secretsmanager import Secret
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

from stacks import persistent_stack as ps

# Importing module level to allow lazy loading for typing
from stacks.api_stack import cc_api
from stacks.persistent_stack import ProviderTable

from .api_model import ApiModel


class ProviderUsers:
    def __init__(
        self,
        *,
        resource: Resource,
        persistent_stack: ps.PersistentStack,
        api_model: ApiModel,
    ):
        super().__init__()
        # /v1/provider-users
        self.provider_users_resource = resource
        self.api_model = api_model
        self.api: cc_api.CCApi = resource.api

        stack: Stack = Stack.of(resource)
        lambda_environment = {
            'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': 'providerFamGivMid',
            'PROV_DATE_OF_UPDATE_INDEX_NAME': 'providerDateOfUpdate',
            'PROVIDER_USER_BUCKET_NAME': persistent_stack.provider_users_bucket.bucket_name,
            'LICENSE_GSI_NAME': persistent_stack.provider_table.license_gsi_name,
            'PROVIDER_USER_POOL_ID': persistent_stack.provider_users.user_pool_id,
            'RATE_LIMITING_TABLE_NAME': persistent_stack.rate_limiting_table.table_name,
            **stack.common_env_vars,
        }

        # /v1/provider-users/registration
        self.provider_users_registration_resource = self.provider_users_resource.add_resource('registration')
        self._add_provider_registration(
            provider_data_table=persistent_stack.provider_table,
            persistent_stack=persistent_stack,
            lambda_environment=lambda_environment,
        )

        # /v1/provider-users/me
        self.provider_users_me_resource = self.provider_users_resource.add_resource('me')
        self._add_get_provider_user_me(
            data_encryption_key=persistent_stack.shared_encryption_key,
            provider_data_table=persistent_stack.provider_table,
            lambda_environment=lambda_environment,
        )

        # /v1/provider-users/me/military-affiliation
        self.provider_users_me_military_affiliation_resource = self.provider_users_me_resource.add_resource(
            'military-affiliation'
        )

        self.provider_users_me_military_affiliation_handler = PythonFunction(
            self.provider_users_resource,
            'ProviderUserMeMilitaryAffiliationHandler',
            description='Provider user military affiliation handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'provider_users.py'),
            handler='provider_user_me_military_affiliation',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )
        persistent_stack.shared_encryption_key.grant_decrypt(self.provider_users_me_military_affiliation_handler)
        persistent_stack.provider_table.grant_read_write_data(self.provider_users_me_military_affiliation_handler)
        persistent_stack.provider_users_bucket.grant_read_write(self.provider_users_me_military_affiliation_handler)
        self.api.log_groups.append(self.provider_users_me_military_affiliation_handler.log_group)
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{self.provider_users_me_military_affiliation_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs '
                    'and is scoped to one table, bucket, and encryption key.',
                },
            ],
        )

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
            integration=LambdaIntegration(
                self.provider_users_me_military_affiliation_handler, timeout=Duration.seconds(29)
            ),
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
            integration=LambdaIntegration(
                self.provider_users_me_military_affiliation_handler, timeout=Duration.seconds(29)
            ),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

    def _add_get_provider_user_me(
        self,
        data_encryption_key: IKey,
        provider_data_table: ProviderTable,
        lambda_environment: dict,
    ):
        self.get_provider_users_me_handler = self._get_provider_user_me_handler(
            data_encryption_key=data_encryption_key,
            provider_data_table=provider_data_table,
            lambda_environment=lambda_environment,
        )
        self.api.log_groups.append(self.get_provider_users_me_handler.log_group)

        self.provider_users_me_resource.add_method(
            'GET',
            request_validator=self.api.parameter_body_validator,
            method_responses=[
                MethodResponse(
                    status_code='200',
                    response_models={'application/json': self.api_model.provider_response_model},
                ),
            ],
            integration=LambdaIntegration(self.get_provider_users_me_handler, timeout=Duration.seconds(29)),
            request_parameters={'method.request.header.Authorization': True},
            authorizer=self.api.provider_users_authorizer,
        )

    def _get_provider_user_me_handler(
        self,
        data_encryption_key: IKey,
        provider_data_table: ProviderTable,
        lambda_environment: dict,
    ) -> PythonFunction:
        stack = Stack.of(self.provider_users_resource)
        handler = PythonFunction(
            self.provider_users_resource,
            'GetProviderUserMeHandler',
            description='Get provider personal profile information handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'provider_users.py'),
            handler='get_provider_user_me',
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

    def _add_provider_registration(
        self,
        provider_data_table: ProviderTable,
        persistent_stack: ps,
        lambda_environment: dict,
    ):
        stack = Stack.of(self.provider_users_resource)
        environment_name = stack.common_env_vars['ENVIRONMENT_NAME']

        # Get the recaptcha secret from us-east-1
        recaptcha_secret = Secret.from_secret_name_v2(
            self.provider_users_resource,
            'RecaptchaSecret',
            f'compact-connect/env/{environment_name}/recaptcha/token',
        )

        self.provider_registration_handler = PythonFunction(
            self.provider_users_resource,
            'ProviderRegistrationHandler',
            description='Provider registration handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'registration.py'),
            handler='register_provider',
            environment=lambda_environment,
            alarm_topic=self.api.alarm_topic,
        )

        provider_data_table.grant_read_write_data(self.provider_registration_handler)
        recaptcha_secret.grant_read(self.provider_registration_handler)
        persistent_stack.provider_users.grant(self.provider_registration_handler, 'cognito-idp:AdminCreateUser')
        persistent_stack.rate_limiting_table.grant_read_write_data(self.provider_registration_handler)
        self.api.log_groups.append(self.provider_registration_handler.log_group)

        # Create metrics for registration attempts and successes
        # This metric uses SAMPLE_COUNT to count the number of times we added a value of 1 to the metric.
        # The registration handler code only adds a value of 1 to this metric when a user is successfully
        # registered. Failed registrations add a value of 0, which are not counted by SAMPLE_COUNT.
        registration_successes = Metric(
            namespace='compact-connect',
            metric_name='registration-attempt',
            statistic=Stats.SAMPLE_COUNT,
            period=Duration.minutes(5),
        )

        # This metric uses SUM to count the total number of registration attempts.
        # The registration handler code adds to this metric for every registration attempt
        # (both successful and failed).
        # This allows us to calculate failures by subtracting successes from total attempts.
        registration_attempts = Metric(
            namespace='compact-connect',
            metric_name='registration-attempt',
            statistic=Stats.SUM,
            period=Duration.minutes(5),
        )

        # Calculate registration failures using math expression
        registration_failures = MathExpression(
            expression='m1 - m2',
            label='RegistrationFailures',
            using_metrics={'m1': registration_attempts, 'm2': registration_successes},
            period=Duration.minutes(5),
        )

        # Create an alarm for high registration failure rate
        registration_failures_alarm = Alarm(
            self.provider_registration_handler,
            'RegistrationFailuresAlarm',
            metric=registration_failures,
            threshold=30,  # Alert if we have more than 30 failures in 5 minutes
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                'This alarm monitors the rate of registration failures. '
                'It triggers when there are more than 30 failures within a 5-minute period. '
                'A failure is counted when a registration attempt does not result in a user account being created.'
            ),
        )
        # Add the alarm to the SNS topic
        registration_failures_alarm.add_alarm_action(SnsAction(self.api.alarm_topic))

        # Create metrics for daily registration monitoring
        # This metric uses SAMPLE_COUNT to count the number of times we added a value of 1 to the metric.
        # The registration handler code only adds a value of 1 to this metric when a user is successfully
        # registered. Failed registrations add a value of 0, which are not counted by SAMPLE_COUNT.
        daily_registration_successes = Metric(
            namespace='compact-connect',
            metric_name='registration-attempt',
            statistic=Stats.SAMPLE_COUNT,
            period=Duration.days(1),
        )

        # This metric uses SUM to count the total number of registration attempts.
        # The registration handler code adds to this metric for every registration attempt
        # (both successful and failed).
        # This allows us to calculate failures by subtracting successes from total attempts.
        daily_registration_attempts = Metric(
            namespace='compact-connect',
            metric_name='registration-attempt',
            statistic=Stats.SUM,
            period=Duration.days(1),
        )

        # Calculate registration failures for the sustained period using math expression
        registration_failures_one_day = MathExpression(
            expression='m1 - m2',
            label='SustainedRegistrationFailures',
            using_metrics={'m1': daily_registration_attempts, 'm2': daily_registration_successes},
            period=Duration.days(1),
        )

        sustained_registration_failures_alarm = Alarm(
            self.provider_registration_handler,
            'SustainedRegistrationFailuresAlarm',
            metric=registration_failures_one_day,
            threshold=288,  # More than 1 failure per 5 minutes over 24 hours (288 = 24 hours * 12 periods per hour)
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                'This alarm monitors for sustained registration failures over a 24-hour period. '
                'It triggers when there have been more than 288 failures in 24 hours '
                '(equivalent to more than 1 failure every 5 minutes). '
                'This helps detect potential targeted attacks that might stay under the short-term threshold.'
            ),
        )
        # Add the alarm to the SNS topic
        sustained_registration_failures_alarm.add_alarm_action(SnsAction(self.api.alarm_topic))

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{self.provider_registration_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs '
                    'and is scoped to one table, user pool, and one secret.',
                },
            ],
        )

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
            integration=LambdaIntegration(self.provider_registration_handler, timeout=Duration.seconds(29)),
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
