# ruff: noqa: E501 line-too-long
# For the sake of readability, we don't want to break up environment values into separate lines
import os

from aws_cdk import BundlingOptions, DockerImage, Size, Stack
from aws_cdk.aws_s3 import IBucket
from aws_cdk.aws_s3_deployment import BucketDeployment, Source
from cdk_nag import NagSuppressions
from common_constructs.frontend_app_config_utility import (
    COGNITO_AUTH_DOMAIN_SUFFIX,
    HTTPS_PREFIX,
    PersistentStackFrontendAppConfigValues,
)
from constructs import Construct


class CompactConnectUIBucketDeployment(BucketDeployment):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        ui_bucket: IBucket,
        environment_context: dict,
        ui_app_config_values: PersistentStackFrontendAppConfigValues,
    ):
        stack = Stack.of(scope)
        # Get environment-specific values from context
        recaptcha_public_key = environment_context['recaptcha_public_key']
        robots_meta = environment_context['robots_meta']

        super().__init__(
            scope,
            construct_id,
            destination_bucket=ui_bucket,
            # Larger memory reserved for the s3 sync process than the default 128MB
            memory_limit=512,
            ephemeral_storage_size=Size.mebibytes(1024),
            sources=[
                Source.asset(
                    # we need to back up two parent directories to get to root
                    os.path.join('..', '..', 'webroot')
                    if ui_app_config_values.should_bundle
                    else os.path.join('tests', 'resources', 'test_ui_directory'),
                    # This will take a long time to run because it installs a bunch of packages
                    # into a docker container before building the UI, every time
                    # If you aren't working on the UI, you can skip bundling for local dev work
                    # to save significant time on app synthesis. To do this, set
                    # cdk-context['aws:cdk:bundling-stacks'] = []
                    **{
                        'bundling': BundlingOptions(
                            # DockerHub was rate-limiting us, so pivot to the AWS public registry
                            image=DockerImage('public.ecr.aws/lts/ubuntu:22.04_stable'),
                            environment={
                                'BASE_URL': '/',
                                'VUE_APP_DOMAIN': f'{HTTPS_PREFIX}{ui_app_config_values.ui_domain_name}',
                                'VUE_APP_ROBOTS_META': robots_meta,
                                'VUE_APP_API_STATE_ROOT': f'{HTTPS_PREFIX}{ui_app_config_values.api_domain_name}',
                                'VUE_APP_API_LICENSE_ROOT': f'{HTTPS_PREFIX}{ui_app_config_values.api_domain_name}',
                                'VUE_APP_API_USER_ROOT': f'{HTTPS_PREFIX}{ui_app_config_values.api_domain_name}',
                                'VUE_APP_COGNITO_REGION': 'us-east-1',
                                'VUE_APP_COGNITO_AUTH_DOMAIN_STAFF': f'{HTTPS_PREFIX}{ui_app_config_values.staff_cognito_domain}{COGNITO_AUTH_DOMAIN_SUFFIX}',
                                'VUE_APP_COGNITO_CLIENT_ID_STAFF': ui_app_config_values.staff_cognito_client_id,
                                'VUE_APP_COGNITO_AUTH_DOMAIN_LICENSEE': f'{HTTPS_PREFIX}{ui_app_config_values.provider_cognito_domain}{COGNITO_AUTH_DOMAIN_SUFFIX}',
                                'VUE_APP_COGNITO_CLIENT_ID_LICENSEE': ui_app_config_values.provider_cognito_client_id,
                                'VUE_APP_RECAPTCHA_KEY': recaptcha_public_key,
                            },
                            entrypoint=['bash'],
                            command=['bin/build.sh'],
                            # Necessary to install system packages
                            user='root',
                        )
                    }
                    if ui_app_config_values.should_bundle
                    else {},
                )
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack=stack,
            path=f'{stack.node.path}/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C512MiB1024MiB/Resource',
            suppressions=[
                {'id': 'AwsSolutions-L1', 'reason': 'This resource is created by CDK. We do not maintain it.'},
                {
                    'id': 'HIPAA.Security-LambdaConcurrency',
                    'reason': 'This lambda is managed by AWS. We do not maintain it.',
                },
                {'id': 'HIPAA.Security-LambdaDLQ', 'reason': 'This lambda is managed by AWS. We do not maintain it.'},
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'This lambda is managed by AWS. We do not maintain it.',
                },
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack=stack,
            path=f'{stack.node.path}/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C512MiB1024MiB/ServiceRole/DefaultPolicy/Resource',
            suppressions=[
                {'id': 'AwsSolutions-IAM5', 'reason': 'This resource is created by CDK. We do not maintain it.'},
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack=stack,
            path=f'{stack.node.path}/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C512MiB1024MiB/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'reason': 'This resource uses AWS managed policies because it is created by CDK. We do not maintain it.',
                },
            ],
        )
