import os

from aws_cdk import Duration
from aws_cdk.aws_dynamodb import Table
from aws_cdk.aws_events import EventBus
from aws_cdk.aws_iam import IRole
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from common_constructs.python_function import PythonFunction
from common_constructs.queued_lambda_processor import QueuedLambdaProcessor
from common_constructs.stack import Stack
from constructs import Construct


class LicensePreprocessor(Construct):
    """This Construct creates a preprocessing SQS queue with
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        ssn_table: Table,
        ssn_ingest_role: IRole,
        ssn_encryption_key = IKey,
        data_event_bus: EventBus,
        alarm_topic: ITopic,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)
        stack: Stack = Stack.of(self)

        preprocess_handler = PythonFunction(
            self,
            'LicensePreprocessHandler',
            description='Preprocess license data to create SSN Dynamo records '
                        'before sending licenses to the event bus',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'ingest.py'),
            handler='preprocess_license_ingest',
            role=ssn_ingest_role,
            timeout=Duration.minutes(1),
            environment={
                'EVENT_BUS_NAME': data_event_bus.event_bus_name,
                'SSN_TABLE_NAME': ssn_table.table_name,
                **stack.common_env_vars,
            },
            alarm_topic=alarm_topic,
        )
        # Grant permissions to the preprocess handler
        data_event_bus.grant_put_events_to(preprocess_handler)
        NagSuppressions.add_resource_suppressions_by_path(
            Stack.of(preprocess_handler.role),
            f'{preprocess_handler.role.node.path}/DefaultPolicy/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': """
                            This policy contains wild-carded actions and resources but they are scoped to the
                            specific actions, KMS key and Table that this lambda specifically needs access to.
                            """,
                },
            ],
        )

        # Create the queued lambda processor for license preprocessing
        self.preprocessor_queue = QueuedLambdaProcessor(
            self,
            'LicenseQueuePreprocessor',
            process_function=preprocess_handler,
            visibility_timeout=Duration.minutes(5),
            retention_period=Duration.hours(12),
            max_batching_window=Duration.minutes(5),
            max_receive_count=3,
            batch_size=50,
            # Use the SSN key for encryption to protect sensitive data
            encryption_key=ssn_encryption_key,
            alarm_topic=alarm_topic,
        )
