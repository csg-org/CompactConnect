from __future__ import annotations

import os

from aws_cdk import Stack
from aws_cdk.aws_iam import IRole
from aws_cdk.aws_s3 import IBucket
from aws_cdk.aws_sns import ITopic
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks import api_lambda_stack as als
from stacks import persistent_stack as ps


class BulkUploadUrlLambdas:
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
            'BULK_BUCKET_NAME': persistent_stack.bulk_uploads_bucket.bucket_name,
            **stack.common_env_vars,
        }

        self.bulk_upload_url_handler = self._bulk_upload_url_handler(
            scope=scope,
            env_vars=env_vars,
            license_upload_role=persistent_stack.ssn_table.license_upload_role,
            bulk_uploads_bucket=persistent_stack.bulk_uploads_bucket,
            alarm_topic=persistent_stack.alarm_topic,
        )
        api_lambda_stack.log_groups.append(self.bulk_upload_url_handler.log_group)

    def _bulk_upload_url_handler(
        self,
        scope: Construct,
        env_vars: dict,
        license_upload_role: IRole,
        bulk_uploads_bucket: IBucket,
        alarm_topic: ITopic,
    ):
        handler = PythonFunction(
            scope,
            'V1BulkUrlHandler',
            description='Get upload url handler',
            lambda_dir='provider-data-v1',
            index=os.path.join('handlers', 'bulk_upload.py'),
            handler='bulk_upload_url_handler',
            role=license_upload_role,
            environment=env_vars,
            alarm_topic=alarm_topic,
        )
        # Grant the handler permissions to write to the bulk bucket
        bulk_uploads_bucket.grant_write(handler)
        return handler
