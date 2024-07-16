import os

from aws_cdk import Stack, RemovalPolicy
from aws_cdk.aws_kms import IKey
from aws_cdk.aws_s3 import IBucket, BucketEncryption
from aws_cdk.aws_ssm import IParameter
from aws_cdk.pipelines import CodePipeline as CdkCodePipeline, ShellStep, CodePipelineSource
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.bucket import Bucket


class BackendPipeline(CdkCodePipeline):
    def __init__(  # pylint: disable=too-many-arguments
            self, scope: Construct, construct_id: str, *,
            github_repo_string: str,
            cdk_path: str,
            connection_id: str,
            trigger_branch: str,
            access_logs_bucket: IBucket,
            encryption_key: IKey,
            ssm_parameter: IParameter,
            environment_context: dict,
            removal_policy: RemovalPolicy,
            **kwargs
    ):
        stack = Stack.of(scope)
        artifact_bucket = Bucket(
            scope, f'{construct_id}ArtifactsBucket',
            encryption_key=encryption_key,
            encryption=BucketEncryption.KMS,
            versioned=True,
            server_access_logs_bucket=access_logs_bucket,
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY
        )
        NagSuppressions.add_resource_suppressions(
            artifact_bucket,
            suppressions=[{
                'id': 'HIPAA.Security-S3BucketReplicationEnabled',
                'reason': 'These artifacts are reproduced on deploy, so the resilience from replication is not'
                ' necessary'
            }]
        )

        super().__init__(
            scope, construct_id,
            artifact_bucket=artifact_bucket,
            self_mutation=True,
            synth=ShellStep(
                'Synth',
                input=CodePipelineSource.connection(
                    repo_string=github_repo_string,
                    branch=trigger_branch,
                    trigger_on_push=True,
                    # Arn format:
                    # arn:aws:codestar-connections:us-east-1:111122223333:connection/<uuid>
                    connection_arn=stack.format_arn(
                        partition=stack.partition,
                        service='codestar-connections',
                        region=stack.region,
                        account=stack.account,
                        resource='connection',
                        resource_name=connection_id
                    )
                ),
                env={
                    'CDK_DEFAULT_ACCOUNT': environment_context['account_id'],
                    'CDK_DEFAULT_REGION': environment_context['region']
                },
                primary_output_directory=os.path.join(cdk_path, 'cdk.out'),
                commands=[
                    f'cd {cdk_path}',
                    'npm install -g aws-cdk',
                    'python -m pip install -r requirements.txt',
                    'cdk synth'
                ]
            ),
            cross_account_keys=True,
            enable_key_rotation=True,
            publish_assets_in_parallel=False,
            **kwargs
        )
        self._ssm_parameter = ssm_parameter

    def build_pipeline(self) -> None:
        super().build_pipeline()

        self._ssm_parameter.grant_read(self.synth_project)

        stack = Stack.of(self)
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            self.node.path,
            suppressions=[
                {
                    'id': 'HIPAA.Security-CodeBuildProjectSourceRepoUrl',
                    'reason': 'This resource does in fact use a secure integration by virtue of the CodeStar connection'
                },
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The wildcarded actions and resources are still scoped to the specific actions, bucket,'
                    ' key, and codebuild resources it specifically needs access to.'
                }
            ],
            apply_to_children=True
        )
