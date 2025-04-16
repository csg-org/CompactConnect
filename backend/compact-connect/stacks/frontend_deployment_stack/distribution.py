import os

from aws_cdk.aws_certificatemanager import Certificate, CertificateValidation
from aws_cdk.aws_cloudfront import (
    AllowedMethods,
    BehaviorOptions,
    CachePolicy,
    Distribution,
    EdgeLambda,
    ErrorResponse,
    LambdaEdgeEventType,
    SecurityPolicyProtocol,
    SSLMethod,
    ViewerProtocolPolicy,
)
from aws_cdk.aws_cloudfront_origins import S3BucketOrigin
from aws_cdk.aws_lambda import Code, Function, Runtime
from aws_cdk.aws_route53 import ARecord, RecordTarget
from aws_cdk.aws_route53_targets import CloudFrontTarget
from aws_cdk.aws_s3 import IBucket
from cdk_nag import NagSuppressions
from common_constructs.frontend_app_config_utility import (
    COGNITO_AUTH_DOMAIN_SUFFIX,
    PersistentStackFrontendAppConfigValues,
)
from common_constructs.security_profile import SecurityProfile
from common_constructs.stack import AppStack
from common_constructs.webacl import WebACL, WebACLScope
from constructs import Construct

S3_URL_SUFFIX = '.s3.amazonaws.com'

def generate_csp_lambda_code(persistent_stack_values: PersistentStackFrontendAppConfigValues) -> str:
    """
    Generate CSP Lambda code with injected configuration values.

    This function reads the template file and replaces placeholders with actual values.

    :param persistent_stack_values: The values from the persistent stack
    :return: The generated Lambda function code
    """
    template_path = os.path.join('lambdas', 'nodejs', 'cloudfront-csp', 'index.js')

    with open(template_path) as f:
        template = f.read()

    # Replace placeholders with actual values
    replacements = {
        '##WEB_FRONTEND##': persistent_stack_values.ui_domain_name,
        '##DATA_API##': persistent_stack_values.api_domain_name,
        '##S3_UPLOAD_URL_STATE##': f'{persistent_stack_values.bulk_uploads_bucket_name}{S3_URL_SUFFIX}',
        '##S3_UPLOAD_URL_PROVIDER##': f'{persistent_stack_values.provider_users_bucket_name}{S3_URL_SUFFIX}',
        '##COGNITO_STAFF##': f'{persistent_stack_values.staff_cognito_domain}{COGNITO_AUTH_DOMAIN_SUFFIX}',
        '##COGNITO_PROVIDER##': f'{persistent_stack_values.provider_cognito_domain}{COGNITO_AUTH_DOMAIN_SUFFIX}',
    }

    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)

    return template


class UIDistribution(Distribution):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        ui_bucket: IBucket,
        security_profile: SecurityProfile = SecurityProfile.RECOMMENDED,
        access_logs_bucket: IBucket,
        persistent_stack_frontend_app_config_values: PersistentStackFrontendAppConfigValues,
    ):
        stack: AppStack = AppStack.of(scope)

        domain_name_kwargs = {}
        if stack.hosted_zone is not None:
            ui_domain_name = f'app.{stack.hosted_zone.zone_name}'
            domain_name_kwargs = {
                'domain_names': [ui_domain_name],
                'certificate': Certificate(
                    scope,
                    'UICert',
                    domain_name=ui_domain_name,
                    validation=CertificateValidation.from_dns(hosted_zone=stack.hosted_zone),
                ),
            }

        web_acl = WebACL(
            scope,
            'DistributionAcl',
            acl_scope=WebACLScope.CLOUDFRONT,
            security_profile=security_profile,
            enable_acl_logging=True,
        )
        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            path=f'{web_acl.node.path}/LogGroup/Resource',
            suppressions=[
                {
                    'id': 'HIPAA.Security-CloudWatchLogGroupEncrypted',
                    'reason': 'This group will contain no PII or PHI and should be accessible by anyone with access'
                    ' to the AWS account for basic operational support visibility. Encrypting is not appropriate here.',
                }
            ],
        )

        # Generate the CSP Lambda code with injected values
        csp_function_code = generate_csp_lambda_code(persistent_stack_frontend_app_config_values)

        csp_function = Function(
            scope,
            'CSPFunction',
            code=Code.from_inline(csp_function_code),
            runtime=Runtime.NODEJS_22_X,
            handler='index.handler',
        )

        NagSuppressions.add_resource_suppressions_by_path(
            stack,
            f'{csp_function.node.path}/ServiceRole/Resource',
            suppressions=[
                {
                    'id': 'AwsSolutions-IAM4',
                    'appliesTo': [
                        'Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                    ],
                    'reason': 'This policy enables CloudWatch logging and is appropriate for this lambda',
                }
            ],
        )
        NagSuppressions.add_resource_suppressions(
            csp_function,
            suppressions=[
                {
                    'id': 'HIPAA.Security-LambdaDLQ',
                    'reason': 'This lambda is synchronous and would not benefit from a DLQ',
                },
                {
                    'id': 'HIPAA.Security-LambdaInsideVPC',
                    'reason': 'This is a lambda executing at CloudFront edge and has no access to sensitive data.'
                    ' There is no benefit to putting it inside a custom VPC',
                },
            ],
        )

        super().__init__(
            scope,
            construct_id,
            default_root_object='index.html',
            default_behavior=BehaviorOptions(
                # We will re-enable caching for pipelined environments. We just want it disabled for dev
                # for faster refreshes of static content.
                cache_policy=CachePolicy.CACHING_DISABLED,
                origin=S3BucketOrigin.with_origin_access_control(ui_bucket, origin_shield_enabled=False),
                viewer_protocol_policy=ViewerProtocolPolicy.HTTPS_ONLY,
                edge_lambdas=[
                    EdgeLambda(
                        event_type=LambdaEdgeEventType.VIEWER_RESPONSE, function_version=csp_function.current_version
                    )
                ],
            ),
            additional_behaviors={
                'service-worker.js': BehaviorOptions(
                    cache_policy=CachePolicy.CACHING_DISABLED,
                    allowed_methods=AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    origin=S3BucketOrigin.with_origin_access_control(ui_bucket, origin_shield_enabled=False),
                    viewer_protocol_policy=ViewerProtocolPolicy.HTTPS_ONLY,
                )
            },
            minimum_protocol_version=SecurityPolicyProtocol.TLS_V1_2_2021,
            ssl_support_method=SSLMethod.SNI,
            enable_logging=True,
            web_acl_id=web_acl.web_acl_arn,
            log_bucket=access_logs_bucket,
            log_file_prefix=f'_logs/{stack.account}/{stack.region}/{scope.node.path}/{construct_id}/',
            error_responses=[
                ErrorResponse(http_status=404, response_http_status=200, response_page_path='/index.html'),
                ErrorResponse(http_status=403, response_http_status=200, response_page_path='/index.html'),
            ],
            **domain_name_kwargs,
        )

        if persistent_stack_frontend_app_config_values.ui_domain_name is not None:
            self.record = ARecord(
                self,
                'UiARecord',
                zone=stack.hosted_zone,
                record_name=ui_domain_name,
                target=RecordTarget(alias_target=CloudFrontTarget(self)),
            )
            self.base_url = f'https://{ui_domain_name}'

        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'AwsSolutions-CFR4',
                    'reason': 'An ACM certificate will be added to this distribution once we have linked '
                    'its domain name',
                }
            ],
        )
        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[{'id': 'AwsSolutions-CFR1', 'reason': 'Geo restrictions are not desirable at this time'}],
        )
