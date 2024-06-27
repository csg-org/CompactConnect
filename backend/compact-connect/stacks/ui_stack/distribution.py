import os

from aws_cdk import Stack
from aws_cdk.aws_cloudfront import Distribution, BehaviorOptions, CachePolicy, OriginAccessIdentity, \
    ViewerProtocolPolicy, SecurityPolicyProtocol, SSLMethod, ErrorResponse, AllowedMethods, EdgeLambda, \
    LambdaEdgeEventType
from aws_cdk.aws_cloudfront_origins import S3Origin
from aws_cdk.aws_lambda import Function, Code, Runtime
from aws_cdk.aws_s3 import IBucket
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.webacl import WebACL, WebACLScope
from stacks.persistent_stack import PersistentStack


class UIDistribution(Distribution):
    def __init__(
        self, scope: Construct, construct_id: str, *,
        ui_bucket: IBucket,
        persistent_stack: PersistentStack
    ):
        stack = Stack.of(scope)

        # Set up S3 access for CloudFront
        origin_access_identity = OriginAccessIdentity(
            scope, 'OriginAccessIdentity'
        )
        ui_bucket.grant_read(origin_access_identity)

        web_acl = WebACL(
            scope, 'DistributionAcl',
            acl_scope=WebACLScope.CLOUDFRONT,
            enable_acl_logging=True
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{web_acl.node.path}/LogGroup/Resource',
            suppressions=[{
                'id': 'HIPAA.Security-CloudWatchLogGroupEncrypted',
                'reason': 'This group will contain no PII or PHI and should be accessible by anyone with access'
                ' to the AWS account for basic operational support visibility. Encrypting is not appropriate here.'
            }]
        )
        with open(os.path.join('lambdas', 'cloudfront-csp', 'index.js'), 'r') as f:
            csp_function = Function(
                scope, 'CSPFunction',
                code=Code.from_inline(f.read()),
                runtime=Runtime.NODEJS_20_X,
                handler='index.handler'
            )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{csp_function.node.path}/ServiceRole/Resource',
            suppressions=[{
                'id': 'AwsSolutions-IAM4',
                'applies_to': [
                    'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                ],
                'reason': 'This policy enables CloudWatch logging and is appropriate for this lambda'
            }]
        )
        NagSuppressions.add_resource_suppressions(
            csp_function,
            suppressions=[
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': 'This lambda is synchronous and would not benefit from a DLQ'
                },
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'This is a lambda executing at CloudFront edge and has no access to sensitive data.'
                    ' There is no benefit to putting it inside a custom VPC'
                }
            ]
        )

        super().__init__(
            scope, construct_id,
            default_root_object='index.html',
            default_behavior=BehaviorOptions(
                # We will re-enable caching for pipelined environments. We just want it disabled for dev
                # for faster refreshes of static content.
                cache_policy=CachePolicy.CACHING_DISABLED,
                origin=S3Origin(
                    ui_bucket,
                    origin_access_identity=origin_access_identity
                ),
                viewer_protocol_policy=ViewerProtocolPolicy.HTTPS_ONLY,
                edge_lambdas=[
                    EdgeLambda(
                        event_type=LambdaEdgeEventType.VIEWER_RESPONSE,
                        function_version=csp_function.current_version
                    )
                ]
            ),
            additional_behaviors={
                'service-worker.js': BehaviorOptions(
                    cache_policy=CachePolicy.CACHING_DISABLED,
                    allowed_methods=AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    origin=S3Origin(
                        ui_bucket,
                        origin_access_identity=origin_access_identity
                    ),
                    viewer_protocol_policy=ViewerProtocolPolicy.HTTPS_ONLY
                )
            },
            minimum_protocol_version=SecurityPolicyProtocol.TLS_V1_2_2021,
            ssl_support_method=SSLMethod.SNI,
            enable_logging=True,
            web_acl_id=web_acl.web_acl_arn,
            log_bucket=persistent_stack.access_logs_bucket,
            log_file_prefix=f'_logs/{stack.account}/{stack.region}/{scope.node.path}/{construct_id}/',
            error_responses=[
                ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path='/index.html'
                ),
                ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path='/index.html'
                )
            ]
        )

        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[{
                'id': 'AwsSolutions-CFR4',
                'reason': 'An ACM certificate will be added to this distribution once we have linked '
                          'its domain name'
            }]
        )
        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'AwsSolutions-CFR1',
                    'reason': 'Geo restrictions are not desirable at this time'
                }
            ]
        )
