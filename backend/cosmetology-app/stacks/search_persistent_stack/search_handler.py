import os

from aws_cdk import Duration
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator, TreatMissingData
from aws_cdk.aws_cloudwatch_actions import SnsAction
from aws_cdk.aws_ec2 import SubnetSelection
from aws_cdk.aws_iam import IRole
from aws_cdk.aws_logs import FilterPattern, MetricFilter, RetentionDays
from aws_cdk.aws_opensearchservice import Domain
from aws_cdk.aws_s3 import IBucket
from aws_cdk.aws_sns import ITopic
from cdk_nag import NagSuppressions
from common_constructs.stack import Stack
from constructs import Construct

from common_constructs.python_function import PythonFunction
from stacks.vpc_stack import VpcStack


class SearchHandler(Construct):
    """
    Construct for the Search Lambda function.

    This construct creates the Lambda function that handles search requests
    against the OpenSearch domain for both provider and privilege records.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        opensearch_domain: Domain,
        vpc_stack: VpcStack,
        vpc_subnets: SubnetSelection,
        lambda_role: IRole,
        alarm_topic: ITopic,
        export_results_bucket: IBucket,
    ):
        """
        Initialize the SearchHandler construct.

        :param scope: The scope of the construct
        :param construct_id: The id of the construct
        :param opensearch_domain: The reference to the OpenSearch domain resource
        :param vpc_stack: The VPC stack
        :param vpc_subnets: The VPC subnets for Lambda deployment
        :param lambda_role: The IAM role for the Lambda function
        :param alarm_topic: The SNS topic for alarms
        :param export_results_bucket: The S3 bucket for storing export result CSV files
        """
        super().__init__(scope, construct_id)
        stack = Stack.of(scope)

        # Create Lambda function for searching providers and privileges
        self.handler = PythonFunction(
            self,
            'SearchProvidersFunction',
            description='Search handler for OpenSearch queries',
            index=os.path.join('handlers', 'search.py'),
            lambda_dir='search',
            handler='search_api_handler',
            role=lambda_role,
            log_retention=RetentionDays.ONE_MONTH,
            environment={
                'OPENSEARCH_HOST_ENDPOINT': opensearch_domain.domain_endpoint,
                'EXPORT_RESULTS_BUCKET_NAME': export_results_bucket.bucket_name,
                **stack.common_env_vars,
            },
            timeout=Duration.seconds(29),
            # memory slightly larger to manage pulling down privilege reports for CSV export
            # and to improve performance of search in general
            memory_size=2048,
            vpc=vpc_stack.vpc,
            vpc_subnets=vpc_subnets,
            security_groups=[vpc_stack.lambda_security_group],
            alarm_topic=alarm_topic,
        )

        # Create Lambda function for public query providers
        self.public_handler = PythonFunction(
            self,
            'PublicSearchProvidersFunction',
            description='Public search handler for OpenSearch license queries',
            index=os.path.join('handlers', 'search.py'),
            lambda_dir='search',
            handler='public_search_api_handler',
            role=lambda_role,
            log_retention=RetentionDays.ONE_MONTH,
            environment={
                'OPENSEARCH_HOST_ENDPOINT': opensearch_domain.domain_endpoint,
                **stack.common_env_vars,
            },
            timeout=Duration.seconds(29),
            memory_size=2048,
            vpc=vpc_stack.vpc,
            vpc_subnets=vpc_subnets,
            security_groups=[vpc_stack.lambda_security_group],
            alarm_topic=alarm_topic,
        )
        opensearch_domain.grant_read(self.public_handler)

        # Create metric filter and alarm for public handler errors
        public_error_log_metric = MetricFilter(
            self,
            'PublicSearchHandlerErrorLogMetric',
            log_group=self.public_handler.log_group,
            metric_namespace='CompactConnect/Search',
            metric_name='PublicSearchHandlerErrors',
            filter_pattern=FilterPattern.string_value(json_field='$.level', comparison='=', value='ERROR'),
            metric_value='1',
            default_value=0,
        )
        public_error_log_alarm = Alarm(
            self,
            'PublicSearchHandlerErrorLogAlarm',
            metric=public_error_log_metric.metric(statistic='Sum'),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description='The Public Search Handler Lambda logged an ERROR level message.',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )
        public_error_log_alarm.add_alarm_action(SnsAction(alarm_topic))

        # Grant the handler read access to the OpenSearch domain
        opensearch_domain.grant_read(self.handler)

        # Grant the handler write access to the export results bucket
        export_results_bucket.grant_write(self.handler)

        # Grant the handler permission to generate presigned URLs for the export results bucket
        export_results_bucket.grant_read(self.handler)

        # Add CDK Nag suppressions for the Lambda function's IAM role
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{self.handler.role.node.path}/DefaultPolicy/Resource',
            [
                {
                    'id': 'AwsSolutions-IAM5',
                    'reason': 'The grant_read method requires wildcard permissions on the OpenSearch domain to '
                    'read from indices. This is appropriate for a search function that needs to query '
                    'provider indices in the domain. Additionally, grant_write and grant_read on the S3 bucket '
                    'use wildcard permissions for object-level operations which is required for writing and '
                    'generating presigned URLs for export result CSV files.',
                },
            ],
        )

        # Create a metric filter to capture ERROR level logs from the search handler Lambda
        error_log_metric = MetricFilter(
            self,
            'SearchHandlerErrorLogMetric',
            log_group=self.handler.log_group,
            metric_namespace='CompactConnect/Search',
            metric_name='SearchHandlerErrors',
            filter_pattern=FilterPattern.string_value(json_field='$.level', comparison='=', value='ERROR'),
            metric_value='1',
            default_value=0,
        )

        # Create an alarm that triggers when ERROR logs are detected
        error_log_alarm = Alarm(
            self,
            'SearchHandlerErrorLogAlarm',
            metric=error_log_metric.metric(statistic='Sum'),
            evaluation_periods=1,
            threshold=1,
            actions_enabled=True,
            alarm_description=f'The Search Handler Lambda logged an ERROR level message. Investigate '
            f'the logs for the {self.handler.function_name} lambda to determine the cause.',
            comparison_operator=ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=TreatMissingData.NOT_BREACHING,
        )
        error_log_alarm.add_alarm_action(SnsAction(alarm_topic))
