from __future__ import annotations

import os

from aws_cdk import Duration
from aws_cdk.aws_events import Rule, EventPattern
from aws_cdk.aws_events_targets import SqsQueue
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from aws_cdk.aws_logs import QueryDefinition, QueryString
from aws_cdk.aws_sqs import Queue, QueueEncryption, DeadLetterQueue
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.python_function import PythonFunction
from common_constructs.stack import AppStack
from stacks import persistent_stack as ps


class IngestStack(AppStack):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            persistent_stack: ps.PersistentStack,
            **kwargs
    ):
        super().__init__(scope, construct_id, **kwargs)

        ingest_dlq = Queue(
            self, 'IngestDLQ',
            encryption=QueueEncryption.KMS,
            encryption_master_key=persistent_stack.shared_encryption_key,
            enforce_ssl=True
        )

        self.ingest_queue = Queue(
            self, 'IngestQueue',
            encryption=QueueEncryption.KMS,
            encryption_master_key=persistent_stack.shared_encryption_key,
            enforce_ssl=True,
            retention_period=Duration.hours(12),
            visibility_timeout=Duration.minutes(5),
            dead_letter_queue=DeadLetterQueue(
                max_receive_count=3,
                queue=ingest_dlq
            )
        )
        Rule(
            self, 'IngestEventRule',
            event_bus=persistent_stack.data_event_bus,
            event_pattern=EventPattern(
                detail_type=['license-ingest']
            ),
            targets=[SqsQueue(
                self.ingest_queue,
                dead_letter_queue=ingest_dlq
            )]
        )

        ingest_handler = PythonFunction(
            self, 'IngestHandler',
            description='Ingest license data handler',
            entry=os.path.join('lambdas', 'license-data'),
            index=os.path.join('handlers', 'ingest.py'),
            handler='ingest_license_message',
            timeout=Duration.minutes(1),
            environment={
                'LICENSE_TABLE_NAME': persistent_stack.license_table.table_name,
                'SSN_INDEX_NAME': persistent_stack.license_table.ssn_index_name,
                **self.common_env_vars
            }
        )
        persistent_stack.license_table.grant_read_write_data(ingest_handler)
        NagSuppressions.add_resource_suppressions_by_path(
            self,
            f'{ingest_handler.node.path}/ServiceRole/DefaultPolicy/Resource',
            suppressions=[{
                'id': 'AwsSolutions-IAM5',
                'reason': 'This policy contains wild-carded actions and resources but they are scoped to the specific'
                          ' actions, KMS key and Table that this lambda specifically needs access to.'
            }]
        )

        ingest_handler.add_event_source(
            SqsEventSource(
                self.ingest_queue,
                batch_size=50,
                max_batching_window=Duration.minutes(5),
                report_batch_item_failures=True
            )
        )

        QueryDefinition(
            self, 'RuntimeQuery',
            query_definition_name=f'{construct_id}/Lambdas',
            query_string=QueryString(
                fields=[
                    '@timestamp',
                    '@log',
                    'level',
                    'status',
                    'message',
                    '@message'
                ],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc'
            ),
            log_groups=[ingest_handler.log_group]
        )
