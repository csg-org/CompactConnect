from __future__ import annotations

import os

from aws_cdk import Duration, Stack
from aws_cdk.aws_cloudwatch import (
    Alarm,
    CfnAlarm,
    ComparisonOperator,
    Metric,
    TreatMissingData,
)
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_cognito import IUserPool
from aws_cdk.aws_dynamodb import ITable
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.python_function import PythonFunction
from common_constructs.user_pool import UserPool
from stacks import api_lambda_stack as als
from stacks import persistent_stack as ps


class StaffUsersLambdas:
    def __init__(
        self,
        *,
        scope: Construct,
        persistent_stack: ps.PersistentStack,
        api_lambda_stack: als.ApiLambdaStack,
    ):
        super().__init__()
        stack = Stack.of(scope)

        env_vars = {
            **stack.common_env_vars,
            'USER_POOL_ID': persistent_stack.staff_users.user_pool_id,
            'USERS_TABLE_NAME': persistent_stack.staff_users.user_table.table_name,
            'FAM_GIV_INDEX_NAME': persistent_stack.staff_users.user_table.family_given_index_name,
            'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
        }

        self.get_me_handler = self._get_me_handler(
            scope=scope,
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
        )
        api_lambda_stack.log_groups.append(self.get_me_handler.log_group)

        self.patch_me_handler = self._patch_me_handler(
            scope=scope,
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
            user_pool=persistent_stack.staff_users,
        )
        api_lambda_stack.log_groups.append(self.patch_me_handler.log_group)

        self.get_users_handler = self._get_users_handler(
            scope=scope,
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
        )
        api_lambda_stack.log_groups.append(self.get_users_handler.log_group)

        self.get_user_handler = self._get_user_handler(
            scope=scope,
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
        )
        api_lambda_stack.log_groups.append(self.get_user_handler.log_group)

        self.patch_user_handler = self._patch_user_handler(
            scope=scope,
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
            compact_configuration_table=persistent_stack.compact_configuration_table,
        )
        api_lambda_stack.log_groups.append(self.patch_user_handler.log_group)

        self.delete_user_handler = self._delete_user_handler(
            scope=scope,
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
            staff_user_pool=persistent_stack.staff_users,
        )
        api_lambda_stack.log_groups.append(self.delete_user_handler.log_group)

        self.post_user_handler = self._post_user_handler(
            scope=scope,
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
            user_pool=persistent_stack.staff_users,
            compact_configuration_table=persistent_stack.compact_configuration_table,
            alarm_topic=persistent_stack.alarm_topic,
        )
        api_lambda_stack.log_groups.append(self.post_user_handler.log_group)

        self.reinvite_user_handler = self._reinvite_user_handler(
            scope=scope,
            env_vars=env_vars,
            data_encryption_key=persistent_stack.shared_encryption_key,
            user_table=persistent_stack.staff_users.user_table,
            user_pool=persistent_stack.staff_users,
        )
        api_lambda_stack.log_groups.append(self.reinvite_user_handler.log_group)

    def _get_me_handler(self, scope: Construct, env_vars: dict, data_encryption_key: IKey, user_table: ITable):
        stack = Stack.of(scope)
        handler = PythonFunction(
            scope,
            'GetMeStaffUserHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'me.py'),
            handler='get_me',
            environment=env_vars,
        )
        data_encryption_key.grant_decrypt(handler)
        user_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
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

    def _patch_me_handler(
        self, scope: Construct, env_vars: dict, data_encryption_key: IKey, user_table: ITable, user_pool: IUserPool
    ):
        stack = Stack.of(scope)

        handler = PythonFunction(
            scope,
            'PatchMeStaffUserHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'me.py'),
            handler='patch_me',
            environment=env_vars,
        )
        data_encryption_key.grant_encrypt_decrypt(handler)
        user_table.grant_read_write_data(handler)
        user_pool.grant(handler, 'cognito-idp:AdminUpdateUserAttributes')

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
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

    def _get_users_handler(self, scope: Construct, env_vars: dict, data_encryption_key: IKey, user_table: ITable):
        stack = Stack.of(scope)

        handler = PythonFunction(
            scope,
            'GetStaffUsersHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='get_users',
            environment=env_vars,
        )
        data_encryption_key.grant_decrypt(handler)
        user_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
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

    def _get_user_handler(self, scope: Construct, env_vars: dict, data_encryption_key: IKey, user_table: ITable):
        stack = Stack.of(scope)

        handler = PythonFunction(
            scope,
            'GetStaffUserHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='get_one_user',
            environment=env_vars,
        )
        data_encryption_key.grant_decrypt(handler)
        user_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
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

    def _patch_user_handler(
        self,
        scope: Construct,
        env_vars: dict,
        data_encryption_key: IKey,
        user_table: ITable,
        compact_configuration_table: ITable,
    ):
        stack = Stack.of(scope)

        handler = PythonFunction(
            scope,
            'PatchUserHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='patch_user',
            environment=env_vars,
        )
        data_encryption_key.grant_encrypt_decrypt(handler)
        user_table.grant_read_write_data(handler)
        compact_configuration_table.grant_read_data(handler)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
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

    def _delete_user_handler(
        self, scope: Construct, env_vars: dict, data_encryption_key: IKey, user_table: ITable, staff_user_pool: UserPool
    ):
        stack = Stack.of(scope)

        handler = PythonFunction(
            scope,
            'DeleteStaffUserFunction',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='delete_user',
            environment=env_vars,
        )

        # Grant permissions to the function
        data_encryption_key.grant_encrypt_decrypt(handler)
        user_table.grant_read_write_data(handler)
        staff_user_pool.grant(handler, 'cognito-idp:AdminDisableUser')

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
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

    def _add_post_user_metrics(
        self,
        scope: Construct,
        alarm_topic: ITopic,
    ):
        # Create a metric to track how many times this endpoint has been invoked within an hour
        staff_user_created_hourly_count_metric = Metric(
            namespace='compact-connect',
            metric_name='staff-user-created',
            statistic='SampleCount',
            period=Duration.hours(1),
            dimensions_map={'service': 'common'},
        )

        # Setting a flat rate of 5 Staff users per hour to alarm on
        self.max_hourly_staff_users_created_alarm = Alarm(
            scope,
            'MaxHourlyStaffUserCreatedAlarm',
            metric=staff_user_created_hourly_count_metric,
            threshold=5,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=f'{scope.node.path} max hourly staff users created alarm. The POST staff user '
            f'endpoint has been invoked more than an expected threshold within an hour period. '
            f'Investigation is required to ensure requests are authorized.',
        )
        self.max_hourly_staff_users_created_alarm.add_alarm_action(SnsAction(alarm_topic))

        # Also create a daily metric
        staff_user_created_daily_count_metric = Metric(
            namespace='compact-connect',
            metric_name='staff-user-created',
            statistic='SampleCount',
            period=Duration.days(1),
            dimensions_map={'service': 'common'},
        )

        # Setting a flat rate of 20 Staff users created per day to alarm on
        self.max_daily_staff_users_created_alarm = Alarm(
            scope,
            'MaxDailyStaffUserCreatedAlarm',
            metric=staff_user_created_daily_count_metric,
            threshold=20,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=f'{scope.node.path} max daily staff users created alarm. The POST staff user endpoint '
            f'has been invoked more than an expected threshold within a day. '
            f'Investigation is required to ensure requests are authorized.',
        )
        self.max_daily_staff_users_created_alarm.add_alarm_action(SnsAction(alarm_topic))

        # We'll monitor longer access patterns to detect anomalies, over time
        # The L2 construct, Alarm, doesn't yet support Anomaly Detection as a configuration
        # so we're using the L1 construct, CfnAlarm
        self.staff_user_creation_anomaly_detection_alarm = CfnAlarm(
            scope,
            'StaffUserCreationAnomalyAlarm',
            alarm_description=f'{scope.node.path} staff-user-created anomaly detection. Anomalies in the number of '
            f'staff users created per day are detected. Investigation is required to ensure requests '
            f'are authorized.',
            comparison_operator='GreaterThanUpperThreshold',
            evaluation_periods=1,
            treat_missing_data='notBreaching',
            actions_enabled=True,
            alarm_actions=[alarm_topic.node.default_child.ref],
            metrics=[
                CfnAlarm.MetricDataQueryProperty(id='ad1', expression='ANOMALY_DETECTION_BAND(m1, 2)'),
                CfnAlarm.MetricDataQueryProperty(
                    id='m1',
                    metric_stat=CfnAlarm.MetricStatProperty(
                        metric=CfnAlarm.MetricProperty(
                            metric_name=staff_user_created_daily_count_metric.metric_name,
                            namespace=staff_user_created_daily_count_metric.namespace,
                            dimensions=[CfnAlarm.DimensionProperty(name='service', value='common')],
                        ),
                        period=3600,
                        stat='SampleCount',
                    ),
                ),
            ],
            threshold_metric_id='ad1',
        )

    def _post_user_handler(
        self,
        scope: Construct,
        env_vars: dict,
        data_encryption_key: IKey,
        user_table: ITable,
        user_pool: IUserPool,
        compact_configuration_table: ITable,
        alarm_topic: ITopic,
    ):
        stack = Stack.of(scope)
        handler = PythonFunction(
            scope,
            'PostStaffUserHandler',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='post_user',
            environment=env_vars,
        )
        data_encryption_key.grant_encrypt_decrypt(handler)
        user_table.grant_read_write_data(handler)
        user_pool.grant(
            handler,
            'cognito-idp:AdminCreateUser',
            'cognito-idp:AdminDeleteUser',
            'cognito-idp:AdminDisableUser',
            'cognito-idp:AdminEnableUser',
            'cognito-idp:AdminGetUser',
            'cognito-idp:AdminResetUserPassword',
            'cognito-idp:AdminSetUserPassword',
        )
        compact_configuration_table.grant_read_data(handler)

        self._add_post_user_metrics(scope, alarm_topic)

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
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

    def _reinvite_user_handler(
        self, scope: Construct, env_vars: dict, data_encryption_key: IKey, user_table: ITable, user_pool: IUserPool
    ):
        stack = Stack.of(scope)

        handler = PythonFunction(
            scope,
            'ReinviteStaffUserFunction',
            lambda_dir='staff-users',
            index=os.path.join('handlers', 'users.py'),
            handler='reinvite_user',
            environment=env_vars,
        )

        # Grant permissions to the function
        data_encryption_key.grant_encrypt_decrypt(handler)
        user_table.grant_read_write_data(handler)
        user_pool.grant(
            handler,
            'cognito-idp:AdminGetUser',
            'cognito-idp:AdminResetUserPassword',
            'cognito-idp:AdminSetUserPassword',
            'cognito-idp:AdminCreateUser',
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
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
