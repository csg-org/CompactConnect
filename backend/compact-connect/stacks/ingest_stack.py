from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, Metric, Stats, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_events import EventBus, EventPattern, Rule
from aws_cdk.aws_events_targets import SqsQueue
from aws_cdk.aws_logs import FilterPattern, MetricFilter
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.queued_lambda_processor import QueuedLambdaProcessor
from common_constructs.ssm_parameter_utility import SSMParameterUtility
from common_constructs.stack import AppStack, Stack
from constructs import Construct

from stacks import persistent_stack as ps
from stacks.provider_users import ProviderUsersStack


class IngestStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        persistent_stack: ps.PersistentStack,
        provider_users_stack: ProviderUsersStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)
        # We explicitly get the event bus arn from parameter store, to avoid issues with cross stack updates
        data_event_bus = SSMParameterUtility.load_data_event_bus_from_ssm_parameter(self)
        self._add_v1_ingest_chain(persistent_stack, provider_users_stack, data_event_bus)

    def _add_v1_ingest_chain(
        self,
        persistent_stack: ps.PersistentStack,
        provider_users_stack: ProviderUsersStack,
        data_event_bus: EventBus,
    ):
        ingest_handler = PythonFunction(
            self,
            'V1IngestHandler',
            description='Ingest license data handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'ingest.py'),
            handler='ingest_license_message',
            timeout=Duration.minutes(5),
            environment={
                'EVENT_BUS_NAME': data_event_bus.event_bus_name,
                'PROVIDER_TABLE_NAME': persistent_stack.provider_table.table_name,
                'PROVIDER_USER_POOL_ID': provider_users_stack.provider_users.user_pool_id,
                'PROVIDER_USER_BUCKET_NAME': persistent_stack.provider_users_bucket.bucket_name,
                'EMAIL_NOTIFICATION_SERVICE_LAMBDA_NAME': (
                    persistent_stack.email_notification_service_lambda.function_name
                ),
                **self.common_env_vars,
            },
            alarm_topic=persistent_stack.alarm_topic,
        )
        # Stored for test accessibility
        self.ingest_handler = ingest_handler
        persistent_stack.provider_table.grant_read_write_data(ingest_handler)
        data_event_bus.grant_put_events_to(ingest_handler)
        # The SSN-correction migration deletes the old provider's Cognito account on a full migration, moves
        # the practitioner's documents from the old provider id's keyspace to the new one in the provider
        # users bucket, and notifies the practitioner to re-register
        provider_users_stack.provider_users.grant(ingest_handler, 'cognito-idp:AdminDeleteUser')
        persistent_stack.provider_users_bucket.grant_read_write(ingest_handler)
        persistent_stack.provider_users_bucket.grant_delete(ingest_handler)
        persistent_stack.email_notification_service_lambda.grant_invoke(ingest_handler)

        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(ingest_handler.role),
            f'{ingest_handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                    This policy contains wild-carded actions and resources but they are scoped to the
                    specific actions, KMS key, Table, user pool, bucket, and lambda that this handler
                    specifically needs access to.
                    """,
                },
            ],
        )
        # We should specifically set an alarm for any failures of this handler, since it could otherwise go unnoticed.
        Alarm(
            self,
            'V1IngestFailureAlarm',
            metric=ingest_handler.metric_errors(statistic=Stats.SUM),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'{ingest_handler.node.path} failed to process a message batch',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        # The invocation-error alarm above only catches failures that escape the handler. The sqs_handler
        # reports per-message failures as batch item failures (the invocation still succeeds), and some paths
        # (e.g. the best-effort S3 document move during an SSN-correction migration) log an ERROR without
        # raising, so we also alarm directly on ERROR-level log lines to catch those.
        error_log_metric = MetricFilter(
            self,
            'V1IngestErrorLogMetric',
            log_group=ingest_handler.log_group,
            metric_namespace='CompactConnect/Ingest',
            metric_name='V1IngestErrors',
            filter_pattern=FilterPattern.string_value(json_field='$.level', comparison='=', value='ERROR'),
            metric_value='1',
            default_value=0,
        )
        Alarm(
            self,
            'V1IngestErrorLogAlarm',
            metric=error_log_metric.metric(statistic='Sum'),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'The ingest handler Lambda logged an ERROR level message. Investigate the logs '
            f'for the {ingest_handler.function_name} lambda to determine the cause.',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        self._add_ssn_correction_migration_alarms(ingest_handler, persistent_stack)

        processor = QueuedLambdaProcessor(
            self,
            'V1Ingest',
            process_function=ingest_handler,
            # SQS visibility timeout is larger than the function timeout,
            # so a message stays invisible long enough to cover the full batch's processing, plus potential retries,
            # before it can be redelivered. See https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-configure.html
            visibility_timeout=Duration.minutes(20),
            retention_period=Duration.hours(12),
            max_batching_window=Duration.minutes(1),
            max_receive_count=3,
            batch_size=50,
            encryption_key=persistent_stack.shared_encryption_key,
            alarm_topic=persistent_stack.alarm_topic,
        )

        ingest_rule = Rule(
            self,
            'V1IngestEventRule',
            event_bus=data_event_bus,
            event_pattern=EventPattern(detail_type=['license.ingest']),
            targets=[SqsQueue(processor.queue, dead_letter_queue=processor.dlq)],
        )

        # We will want to alert on failure of this rule to deliver events to the ingest queue
        Alarm(
            self,
            'V1IngestRuleFailedInvocations',
            metric=Metric(
                namespace='AWS/Events',
                metric_name='FailedInvocations',
                dimensions_map={
                    'EventBusName': data_event_bus.event_bus_name,
                    'RuleName': ingest_rule.rule_name,
                },
                period=Duration.minutes(5),
                statistic='Sum',
            ),
            evaluation_periods=1,
            threshold=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

    def _add_ssn_correction_migration_alarms(
        self, ingest_handler: PythonFunction, persistent_stack: ps.PersistentStack
    ):
        """
        Alarm whenever a state relies on the previousSSN last-resort correction feature (see
        handlers/ingest.py::_perform_ssn_correction_migration), split by whether the correction fully or only
        partially migrated the affected practitioner. Each metric/alarm pair uses a 24-hour period with a
        threshold of 1, so devops support sees at most one notification per category (2 total) per day this
        feature is used, regardless of how many corrections occurred that day.
        """
        full_migration_metric = Metric(
            namespace='compact-connect',
            metric_name='ssn-correction-full-migration',
            dimensions_map={'service': 'common'},
            statistic=Stats.SUM,
            period=Duration.days(1),
        )
        Alarm(
            ingest_handler,
            'SsnCorrectionFullMigrationAlarm',
            metric=full_migration_metric,
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                'A state has used the previousSSN field to fully migrate a practitioner record within the '
                'last 24 hours. This is a last-resort correction feature (see the previousSSN field '
                'documentation) and should be rare; investigate with the reporting state to confirm the '
                'correction was warranted and to help prevent recurring upload errors.'
            ),
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))

        partial_migration_metric = Metric(
            namespace='compact-connect',
            metric_name='ssn-correction-partial-migration',
            dimensions_map={'service': 'common'},
            statistic=Stats.SUM,
            period=Duration.days(1),
        )
        Alarm(
            ingest_handler,
            'SsnCorrectionPartialMigrationAlarm',
            metric=partial_migration_metric,
            threshold=1,
            evaluation_periods=1,
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
            alarm_description=(
                'A state has used the previousSSN field to partially migrate a practitioner record within '
                'the last 24 hours. This is a last-resort correction feature (see the previousSSN field '
                'documentation) and should be rare; investigate with the reporting state to confirm the '
                'correction was warranted and to help prevent recurring upload errors.'
            ),
        ).add_alarm_action(SnsAction(persistent_stack.alarm_topic))
