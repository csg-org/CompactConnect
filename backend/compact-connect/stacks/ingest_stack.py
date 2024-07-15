from __future__ import annotations

import json
import os

from aws_cdk import Duration
from aws_cdk.aws_events import Rule, EventPattern
from aws_cdk.aws_events_targets import SqsQueue
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from aws_cdk.aws_sqs import Queue, QueueEncryption, DeadLetterQueue
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.python_function import PythonFunction
from common_constructs.stack import Stack
from stacks import persistent_stack as ps


class IngestStack(Stack):
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
            retention_period=Duration.hours(2),
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
            entry=os.path.join('lambdas', 'license-data'),
            index=os.path.join('handlers', 'ingest.py'),
            handler='process_license_message',
            environment={
                'DEBUG': 'true',
                'COMPACTS': json.dumps(self.node.get_context('compacts')),
                'JURISDICTIONS': json.dumps(self.node.get_context('jurisdictions')),
                'LICENSE_TABLE_NAME': persistent_stack.license_table.table_name,
                'SSN_INDEX_NAME': persistent_stack.license_table.ssn_index_name,
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
                batch_size=5,
                max_batching_window=Duration.minutes(5),
                report_batch_item_failures=True
            )
        )
