from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, MathExpression, Metric, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_secretsmanager import Secret
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack

from stacks import persistent_stack as ps
from stacks.provider_users import ProviderUsersStack


class ProviderUsersLambdas:
    def __init__(
        self,
        *,
        scope: Stack,
        persistent_stack: ps.PersistentStack,
        provider_users_stack: ProviderUsersStack,
    ) -> None:
        self.scope = scope
        self.persistent_stack = persistent_stack
        self.provider_users_stack = provider_users_stack

        self.stack: Stack = Stack.of(scope)
        lambda_environment = {
            'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
            'PROV_FAM_GIV_MID_INDEX_NAME': 'providerFamGivMid',
            'PROV_DATE_OF_UPDATE_INDEX_NAME': 'providerDateOfUpdate',
            'PROVIDER_USER_BUCKET_NAME': persistent_stack.provider_users_bucket.bucket_name,
            'LICENSE_GSI_NAME': persistent_stack.provider_table.license_gsi_name,
            'PROVIDER_USER_POOL_ID': provider_users_stack.provider_users.user_pool_id,
            'RATE_LIMITING_TABLE_NAME': persistent_stack.rate_limiting_table.table_name,
            'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
            'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': persistent_stack.email_notification_service_lambda.function_name,
            **self.stack.common_env_vars,
        }

        # Get the recaptcha secret
        environment_name = self.stack.common_env_vars['ENVIRONMENT_NAME']
        self.recaptcha_secret = Secret.from_secret_name_v2(
            self.scope,
            'RecaptchaSecret',
            f'compact-connect/env/{environment_name}/recaptcha/token',
        )

        self.account_recovery_initiate_function = self._create_account_recovery_initiate_function(lambda_environment)
        self.account_recovery_verify_function = self._create_account_recovery_verify_function(lambda_environment)
        self.provider_users_me_handler = self._create_provider_users_me_handler(lambda_environment)
        self.provider_registration_handler = self._create_provider_registration_handler(lambda_environment)

    def _create_account_recovery_initiate_function(self, lambda_environment: dict) -> PythonFunction:
        # Add client id only for initiate function
        env = {
            **lambda_environment,
            'PROVIDER_USER_POOL_CLIENT_ID': self.provider_users_stack.provider_users.ui_client.user_pool_client_id,
        }

        initiate_account_recovery_function = PythonFunction(
            self.scope,
            'ProviderUsersAccountRecoveryInitiate',
            description='Provider users account recovery initiate handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'account_recovery.py'),
            handler='initiate_account_recovery',
            environment=env,
            alarm_topic=self.persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        self.persistent_stack.provider_table.grant_read_write_data(initiate_account_recovery_function)
        self.persistent_stack.rate_limiting_table.grant_read_write_data(initiate_account_recovery_function)
        self.persistent_stack.compact_configuration_table.grant_read_data(initiate_account_recovery_function)
        self.persistent_stack.email_notification_service_lambda.grant_invoke(initiate_account_recovery_function)
        self.provider_users_stack.provider_users.grant(
            initiate_account_recovery_function, 'cognito-idp:AdminInitiateAuth'
        )
        self.recaptcha_secret.grant_read(initiate_account_recovery_function)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{initiate_account_recovery_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are scoped to the tables, user pool, '
                    'and recaptcha secret it needs to access.',
                },
            ],
        )

        # Create metrics for account recovery attempts and successes
        # This metric uses SAMPLE_COUNT to count the number of times we added a value of 1 to the metric.
        # The registration handler code only adds a value of 1 to this metric when a user successfully initiated the
        # account recovery process. Failed attemps add a value of 0, which are not counted by SAMPLE_COUNT.
        account_recovery_initiation_successes = Metric(
            namespace='compact-connect',
            metric_name='mfa-recovery-initiate',
            dimensions_map={'service': 'common'},
            statistic=Stats.SAMPLE_COUNT,
            period=Duration.minutes(5),
        )

        # This metric uses SUM to count the total number of registration attempts.
        # The registration handler code adds to this metric for every registration attempt
        # (both successful and failed).
        # This allows us to calculate failures by subtracting successes from total attempts.
        account_recovery_initiation_attempts = Metric(
            namespace='compact-connect',
            metric_name='mfa-recovery-initiate',
            dimensions_map={'service': 'common'},
            statistic=Stats.SUM,
            period=Duration.minutes(5),
        )

        # Calculate registration failures using math expression
        account_recovery_failures = MathExpression(
            expression='m1 - m2',
            label='AccountRecoveryInitiationFailures',
            using_metrics={'m1': account_recovery_initiation_attempts, 'm2': account_recovery_initiation_successes},
            period=Duration.minutes(5),
        )

        # Create an alarm for high registration failure rate
        account_recovery_failures_alarm = Alarm(
            initiate_account_recovery_function,
            'AccountRecoveryFailuresAlarm',
            metric=account_recovery_failures,
            threshold=15,  # Alert if we have more than 15 failures in 5 minutes
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                'This alarm monitors the rate of account recovery failures. '
                'It triggers when there are more than 15 failures within a 5-minute period. '
                'A failure is counted when an account recovery attempt does not result in a successful '
                'email notification.'
            ),
        )
        # Add the alarm to the SNS topic
        account_recovery_failures_alarm.add_alarm_action(SnsAction(self.persistent_stack.alarm_topic))

        # Create metrics for daily account recovery monitoring
        # This metric uses SAMPLE_COUNT to count the number of times we added a value of 1 to the metric.
        # The account recovery handler code only adds a value of 1 to this metric when a user is successfully
        # initiates the account recovery email. Failed recoveries add a value of 0,
        # which are not counted by SAMPLE_COUNT.
        daily_account_recovery_successes = Metric(
            namespace='compact-connect',
            metric_name='mfa-recovery-initiate',
            dimensions_map={'service': 'common'},
            statistic=Stats.SAMPLE_COUNT,
            period=Duration.days(1),
        )

        # This metric uses SUM to count the total number of account recovery attempts.
        # The initiate account recovery handler code adds to this metric for every account recovery attempt
        # (both successful and failed).
        # This allows us to calculate failures by subtracting successes from total attempts.
        daily_account_recovery_attempts = Metric(
            namespace='compact-connect',
            metric_name='mfa-recovery-initiate',
            dimensions_map={'service': 'common'},
            statistic=Stats.SUM,
            period=Duration.days(1),
        )

        # Calculate account recovery failures for the sustained period using math expression
        account_recovery_failures_one_day = MathExpression(
            expression='m1 - m2',
            label='SustainedAccountRecoveryFailures',
            using_metrics={'m1': daily_account_recovery_attempts, 'm2': daily_account_recovery_successes},
            period=Duration.days(1),
        )

        sustained_account_recovery_alarm = Alarm(
            initiate_account_recovery_function,
            'SustainedAccountRecoveryFailuresAlarm',
            metric=account_recovery_failures_one_day,
            threshold=24,  # More than 1 failure per hour over 24 hours
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                'This alarm monitors for sustained account recovery failures over a 24-hour period. '
                'It triggers when there have been more than 24 failures in 24 hours '
                '(equivalent to more than 1 failure every hour). '
                'This helps detect potential targeted attacks that might stay under the short-term threshold.'
            ),
        )
        # Add the alarm to the SNS topic
        sustained_account_recovery_alarm.add_alarm_action(SnsAction(self.persistent_stack.alarm_topic))

        return initiate_account_recovery_function

    def _create_account_recovery_verify_function(self, lambda_environment: dict) -> PythonFunction:
        verify_account_recovery_function = PythonFunction(
            self.scope,
            'ProviderUsersAccountRecoveryVerify',
            description='Provider users account recovery verify handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'account_recovery.py'),
            handler='verify_account_recovery',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        self.persistent_stack.provider_table.grant_read_write_data(verify_account_recovery_function)
        self.persistent_stack.rate_limiting_table.grant_read_write_data(verify_account_recovery_function)
        self.provider_users_stack.provider_users.grant(verify_account_recovery_function, 'cognito-idp:AdminDeleteUser')
        self.provider_users_stack.provider_users.grant(verify_account_recovery_function, 'cognito-idp:AdminCreateUser')
        self.recaptcha_secret.grant_read(verify_account_recovery_function)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{verify_account_recovery_function.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are scoped to the tables, user pool, '
                    'and recaptcha secret it needs to access.',
                },
            ],
        )

        # Create metrics for account recovery attempts and successes
        # This metric uses SAMPLE_COUNT to count the number of times we added a value of 1 to the metric.
        # The registration handler code only adds a value of 1 to this metric when a user successfully initiated the
        # account recovery process. Failed attemps add a value of 0, which are not counted by SAMPLE_COUNT.
        account_recovery_verification_successes = Metric(
            namespace='compact-connect',
            metric_name='mfa-recovery-verify',
            dimensions_map={'service': 'common'},
            statistic=Stats.SAMPLE_COUNT,
            period=Duration.minutes(5),
        )

        # This metric uses SUM to count the total number of registration attempts.
        # The registration handler code adds to this metric for every registration attempt
        # (both successful and failed).
        # This allows us to calculate failures by subtracting successes from total attempts.
        account_recovery_verification_attempts = Metric(
            namespace='compact-connect',
            metric_name='mfa-recovery-verify',
            dimensions_map={'service': 'common'},
            statistic=Stats.SUM,
            period=Duration.minutes(5),
        )

        # Calculate registration failures using math expression
        account_recovery_verification_failures = MathExpression(
            expression='m1 - m2',
            label='AccountRecoveryVerificationFailures',
            using_metrics={'m1': account_recovery_verification_attempts, 'm2': account_recovery_verification_successes},
            period=Duration.minutes(5),
        )

        # Create an alarm for high registration failure rate
        account_recovery_verification_failures_alarm = Alarm(
            verify_account_recovery_function,
            'AccountRecoveryFailuresAlarm',
            metric=account_recovery_verification_failures,
            # Alert if we have more than 3 failures in 5 minutes (failures are not expected at this step, but may
            # occur due to bot activity)
            threshold=3,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                'This alarm monitors the rate of account recovery verification failures. '
                'It triggers when there are more than 3 failures within a 5-minute period. '
                'A failure is counted when an account recovery verification attempt does not result in a successful '
                'account recovery, most likely due to an invalid recovery token.'
            ),
        )
        # Add the alarm to the SNS topic
        account_recovery_verification_failures_alarm.add_alarm_action(SnsAction(self.persistent_stack.alarm_topic))

        return verify_account_recovery_function

    def _create_provider_users_me_handler(self, lambda_environment: dict) -> PythonFunction:
        provider_users_me_handler = PythonFunction(
            self.scope,
            'ProviderUsersHandler',
            description='Provider users API handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'provider_users.py'),
            handler='provider_users_api_handler',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        self.persistent_stack.shared_encryption_key.grant_decrypt(provider_users_me_handler)
        self.persistent_stack.provider_table.grant_read_write_data(provider_users_me_handler)
        self.persistent_stack.provider_users_bucket.grant_read_write(provider_users_me_handler)
        self.persistent_stack.email_notification_service_lambda.grant_invoke(provider_users_me_handler)
        self.persistent_stack.compact_configuration_table.grant_read_data(provider_users_me_handler)
        # Grant Cognito permissions for email update operations
        self.provider_users_stack.provider_users.grant(provider_users_me_handler, 'cognito-idp:AdminGetUser')
        self.provider_users_stack.provider_users.grant(
            provider_users_me_handler, 'cognito-idp:AdminUpdateUserAttributes'
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{provider_users_me_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs '
                    'and is scoped to one table, bucket, and encryption key.',
                },
            ],
        )

        return provider_users_me_handler

    def _create_provider_registration_handler(self, lambda_environment: dict) -> PythonFunction:
        provider_registration_handler = PythonFunction(
            self.scope,
            'ProviderRegistrationHandler',
            description='Provider registration handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'registration.py'),
            handler='register_provider',
            environment=lambda_environment,
            alarm_topic=self.persistent_stack.alarm_topic,
        )

        # Grant necessary permissions
        self.persistent_stack.provider_table.grant_read_write_data(provider_registration_handler)
        self.persistent_stack.compact_configuration_table.grant_read_data(provider_registration_handler)
        self.recaptcha_secret.grant_read(provider_registration_handler)
        self.provider_users_stack.provider_users.grant(provider_registration_handler, 'cognito-idp:AdminCreateUser')
        self.provider_users_stack.provider_users.grant(provider_registration_handler, 'cognito-idp:AdminGetUser')
        # This is granted to allow the registration handler to clean up user accounts that were never logged into and
        # need to be re-registered under a different email (ie mistyped their email address during the first
        # registration)
        self.provider_users_stack.provider_users.grant(provider_registration_handler, 'cognito-idp:AdminDeleteUser')
        self.persistent_stack.rate_limiting_table.grant_read_write_data(provider_registration_handler)
        self.persistent_stack.email_notification_service_lambda.grant_invoke(provider_registration_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            self.stack,
            path=f'{provider_registration_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The actions in this policy are specifically what this lambda needs '
                    'and is scoped to one table, user pool, and one secret.',
                },
            ],
        )

        # Create metrics for registration attempts and successes
        # This metric uses SAMPLE_COUNT to count the number of times we added a value of 1 to the metric.
        # The registration handler code only adds a value of 1 to this metric when a user is successfully
        # registered. Failed registrations add a value of 0, which are not counted by SAMPLE_COUNT.
        registration_successes = Metric(
            namespace='compact-connect',
            metric_name='registration-attempt',
            dimensions_map={'service': 'common'},
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
            dimensions_map={'service': 'common'},
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
            provider_registration_handler,
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
        registration_failures_alarm.add_alarm_action(SnsAction(self.persistent_stack.alarm_topic))

        # Create metrics for daily registration monitoring
        # This metric uses SAMPLE_COUNT to count the number of times we added a value of 1 to the metric.
        # The registration handler code only adds a value of 1 to this metric when a user is successfully
        # registered. Failed registrations add a value of 0, which are not counted by SAMPLE_COUNT.
        daily_registration_successes = Metric(
            namespace='compact-connect',
            metric_name='registration-attempt',
            dimensions_map={'service': 'common'},
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
            dimensions_map={'service': 'common'},
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
            provider_registration_handler,
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
        sustained_registration_failures_alarm.add_alarm_action(SnsAction(self.persistent_stack.alarm_topic))

        return provider_registration_handler
