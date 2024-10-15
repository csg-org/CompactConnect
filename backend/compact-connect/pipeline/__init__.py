import json

from aws_cdk import RemovalPolicy
from aws_cdk.aws_iam import Effect, PolicyStatement
from aws_cdk.aws_kms import Key
from aws_cdk.aws_ssm import StringParameter
from common_constructs.access_logs_bucket import AccessLogsBucket
from common_constructs.alarm_topic import AlarmTopic
from common_constructs.stack import Stack
from constructs import Construct

from pipeline.backend_pipeline import BackendPipeline
from pipeline.backend_stage import BackendStage


class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, cdk_path: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # If we delete this stack, retain the resource (orphan but prevent data loss) or destroy it (clean up)?
        removal_policy = RemovalPolicy.DESTROY

        # Fetch ssm_context if not provided locally
        parameter = StringParameter.from_string_parameter_name(
            self, 'PipelineContext', string_parameter_name='compact-connect-context'
        )
        value = StringParameter.value_from_lookup(self, parameter.parameter_name)
        # When CDK runs for the first time, it synthesizes fully without actually retrieving the SSM Parameter
        # value. It, instead, populates parameters and other look-ups with dummy values, synthesizes, collects all
        # the look-ups together, populates them for real, then re-synthesizes with real values.
        # To accommodate this pattern, we have to replace this dummy value with one that will actually
        # let CDK complete its first round of synthesis, so that it can get to its second, real, synthesis.
        if value != 'dummy-value-for-compact-connect-context':
            ssm_context = json.loads(value)
        else:
            with open('cdk.context.production-example.json') as f:
                ssm_context = json.load(f)['ssm_context']
        pipeline_environment_context = ssm_context['environments']['pipeline']
        connection_arn = pipeline_environment_context['connection_arn']
        github_repo_string = ssm_context['github_repo_string']
        app_name = ssm_context['app_name']

        self.shared_encryption_key = Key(
            self,
            'SharedEncryptionKey',
            enable_key_rotation=True,
            alias=f'{self.stack_name}-shared-encryption-key',
            removal_policy=removal_policy,
        )

        notifications = pipeline_environment_context.get('notifications', {})
        self.alarm_topic = AlarmTopic(
            self,
            'AlarmTopic',
            master_key=self.shared_encryption_key,
            email_subscriptions=notifications.get('email', []),
            slack_subscriptions=notifications.get('slack', []),
        )

        access_logs_bucket = AccessLogsBucket(
            self,
            'AccessLogsBucket',
            removal_policy=removal_policy,
            auto_delete_objects=removal_policy == RemovalPolicy.DESTROY,
        )

        # Allows us to override the default branching scheme for the test environment, via context variable
        pre_prod_trigger_branch = pipeline_environment_context.get('pre_prod_trigger_branch', 'development')
        self.pre_prod_pipeline = BackendPipeline(
            self,
            'PreProdPipeline',
            github_repo_string=github_repo_string,
            cdk_path=cdk_path,
            connection_arn=connection_arn,
            trigger_branch=pre_prod_trigger_branch,
            encryption_key=self.shared_encryption_key,
            alarm_topic=self.alarm_topic,
            access_logs_bucket=access_logs_bucket,
            ssm_parameter=parameter,
            environment_context=pipeline_environment_context,
            self_mutation=True,
            removal_policy=removal_policy,
        )
        self.test_stage = BackendStage(
            self,
            'Test',
            app_name=app_name,
            environment_name='test',
            environment_context=ssm_context['environments']['test'],
            github_repo_string=github_repo_string,
        )
        self.pre_prod_pipeline.add_stage(self.test_stage)
        self.pre_prod_pipeline.build_pipeline()
        self.pre_prod_pipeline.synth_project.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=['sts:AssumeRole'],
                resources=[
                    self.format_arn(
                        partition=self.partition,
                        service='iam',
                        region='',
                        account='*',
                        resource='role',
                        resource_name='cdk-hnb659fds-lookup-role-*',
                    )
                ],
            )
        )

        self.prod_pipeline = BackendPipeline(
            self,
            'ProdPipeline',
            github_repo_string=github_repo_string,
            cdk_path=cdk_path,
            connection_arn=connection_arn,
            trigger_branch='main',
            encryption_key=self.shared_encryption_key,
            alarm_topic=self.alarm_topic,
            access_logs_bucket=access_logs_bucket,
            ssm_parameter=parameter,
            environment_context=pipeline_environment_context,
            # We only want to deploy pipelines from a single branch, so we'll deploy pipeline configuration from the
            # preprod pipeline
            self_mutation=False,
            removal_policy=removal_policy,
        )
        self.prod_stage = BackendStage(
            self,
            'Prod',
            app_name=app_name,
            environment_name='prod',
            environment_context=ssm_context['environments']['prod'],
            github_repo_string=github_repo_string,
        )
        self.prod_pipeline.add_stage(self.prod_stage)
        self.prod_pipeline.build_pipeline()
        self.prod_pipeline.synth_project.add_to_role_policy(
            PolicyStatement(
                effect=Effect.ALLOW,
                actions=['sts:AssumeRole'],
                resources=[
                    self.format_arn(
                        partition=self.partition,
                        service='iam',
                        region='',
                        account='*',
                        resource='role',
                        resource_name='cdk-hnb659fds-lookup-role-*',
                    )
                ],
            )
        )
