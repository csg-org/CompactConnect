from __future__ import annotations

import os

from aws_cdk import Stack
from aws_cdk.aws_dynamodb import ITable
from aws_cdk.aws_iam import IRole
from aws_cdk.aws_sns import ITopic
from aws_cdk.aws_sqs import IQueue
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks import persistent_stack as ps


class PostLicensesLambdas:
    def __init__(
        self,
        *,
        scope: Construct,
        persistent_stack: ps.PersistentStack,
    ):
        super().__init__()
        stack = Stack.of(scope)

        env_vars = {
            'LICENSE_PREPROCESSING_QUEUE_URL': persistent_stack.ssn_table.preprocessor_queue.queue.queue_url,
            'COMPACT_CONFIGURATION_TABLE_NAME': persistent_stack.compact_configuration_table.table_name,
            'RATE_LIMITING_TABLE_NAME': persistent_stack.rate_limiting_table.table_name,
            **stack.common_env_vars,
        }

        self.post_licenses_handler = self._post_licenses_handler(
            scope=scope,
            env_vars=env_vars,
            license_upload_role=persistent_stack.ssn_table.license_upload_role,
            license_preprocessing_queue=persistent_stack.ssn_table.preprocessor_queue.queue,
            compact_configuration_table=persistent_stack.compact_configuration_table,
            rate_limiting_table=persistent_stack.rate_limiting_table,
            alarm_topic=persistent_stack.alarm_topic,
        )

    def _post_licenses_handler(
        self,
        scope: Construct,
        env_vars: dict,
        license_upload_role: IRole,
        license_preprocessing_queue: IQueue,
        compact_configuration_table: ITable,
        rate_limiting_table: ITable,
        alarm_topic: ITopic,
    ):
        handler = PythonFunction(
            scope,
            'V1PostLicensesHandler',
            description='Post licenses handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'licenses.py'),
            handler='post_licenses',
            role=license_upload_role,
            environment=env_vars,
            alarm_topic=alarm_topic,
        )

        # Grant permissions to put messages on the preprocessing queue
        license_preprocessing_queue.grant_send_messages(handler)
        compact_configuration_table.grant_read_data(handler)
        rate_limiting_table.grant_read_write_data(handler)
        return handler
