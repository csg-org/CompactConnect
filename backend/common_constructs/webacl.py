from enum import Enum
from typing import List

from aws_cdk import IResolvable, RemovalPolicy, Resource, Stack
from aws_cdk.aws_apigateway import Stage
from aws_cdk.aws_iam import Effect, PolicyStatement, ServicePrincipal
from aws_cdk.aws_logs import LogGroup, RetentionDays
from aws_cdk.aws_wafv2 import CfnLoggingConfiguration, CfnWebACL, CfnWebACLAssociation
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.service_principal_name import ServicePrincipalName


class WebACLScope(Enum):
    REGIONAL = 'REGIONAL'
    CLOUDFRONT = 'CLOUDFRONT'


class WebACL(Resource):
    """
    A WebACL to protect AWS Resources
    """
    def __init__(
        self, scope: Construct, construct_id: str, *,
        acl_scope: WebACLScope = WebACLScope.REGIONAL,
        enable_acl_logging: bool = True,
        rules: List[IResolvable | CfnWebACL.RuleProperty] = None
    ):
        super().__init__(scope, construct_id)

        if rules is None:
            self.rules = [
                WebACLRules.rate_limit_rule(),
                WebACLRules.common_rule()
            ]
        else:
            self.rules = rules

        resource = CfnWebACL(
            self, 'Resource',
            default_action={
                'allow': {}
            },
            scope=acl_scope.value,
            visibility_config={
                'cloudWatchMetricsEnabled': True,
                'metricName': 'MetricForWebACLCDK-' + construct_id,
                'sampledRequestsEnabled': True,
            },
            rules=self.rules
        )
        self.node.default_child = resource
        self.web_acl_id = resource.ref
        self.web_acl_arn = resource.attr_arn

        if enable_acl_logging:
            logs_delivery_principal = ServicePrincipal(ServicePrincipalName.LOGS_DELIVERY.value)
            stack = Stack.of(self)
            waf_group_prefix = 'aws-waf-logs-'

            # WARNING: THIS WILL NOT WORK IN GOVCLOUD
            # Global ACLs need a log group in us-east-1
            # Regional ACLs need a log group in the matching region
            if scope == WebACLScope.CLOUDFRONT and not stack.region == 'us-east-1':
                raise RuntimeError('CLOUDFRONT scoped WebACLs must be in the "us-east-1" region to have'
                                   ' logging enabled')

            log_group = LogGroup(
                self, 'LogGroup',
                    retention=RetentionDays.ONE_MONTH,
                    removal_policy=RemovalPolicy.DESTROY,
                    log_group_name=f'{waf_group_prefix}{self.node.path}'
            )
            NagSuppressions.add_resource_suppressions(
                log_group,
                suppressions=[{
                    'id': 'HIPAA.Security-CloudWatchLogGroupEncrypted',
                    'reason': 'This group will contain no PII or PHI and should be accessible by anyone with access'
                              ' to the AWS account for basic operational support visibility. Encrypting is not '
                              ' appropriate here.'
                }]
            )

            log_group.add_to_resource_policy(
                PolicyStatement(
                    sid='AWSLogDeliveryAclCheck',
                    effect=Effect.ALLOW,
                    principals=[logs_delivery_principal],
                    actions=[
                        'logs:CreateLogStream',
                        'logs:PutLogEvents'
                    ],
                    resources=[
                        # arn:aws:logs:us-east-1:0123456789:log-group:my-log-group:log-stream:*
                        f'{log_group.log_group_arn}:log-stream:*'
                    ],
                    conditions={
                        'StringEquals': {
                            'aws:SourceAccount': [stack.account],
                            'aws:SourceArn': [
                                # arn:aws:logs:us-east-1:01234567890:*
                                stack.format_arn(
                                    partition=stack.partition,
                                    service='logs',
                                    region=stack.region,
                                    account=stack.account,
                                    resource='*'
                                )
                            ]
                        }
                    }
                )
            )
            CfnLoggingConfiguration(
                self, 'Logging',
                log_destination_configs=[log_group.log_group_arn],
                resource_arn=resource.attr_arn,
                redacted_fields=[
                    {
                        'singleHeader': {'Name': 'Authorization'}
                    }
                ]
            )

    def associate_stage(self, resource: Stage):
        CfnWebACLAssociation(
            self, 'WebACLAssociation',
            resource_arn=resource.stage_arn,
            web_acl_arn=self.web_acl_arn
        )

    def add_rule(self, rule: CfnWebACL.RuleProperty):
        self.rules.append(rule)


class WebACLRules():
    @staticmethod
    def rate_limit_rule(limit: int = 100):
        """
        Limit calls to `limit` calls per 5 minutes for any IP
        :param limit: The 5-minute call count limit. Default: 100.
        """
        # Limit calls to 100 per 5 minutes for any IP
        return CfnWebACL.RuleProperty(
            name='RateLimit',
            priority=0,
            statement=CfnWebACL.StatementProperty(
                rate_based_statement=CfnWebACL.RateBasedStatementProperty(
                    aggregate_key_type='IP',
                    limit=limit
                )
            ),
            visibility_config=CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='MetricForWebACL-Rate',
                sampled_requests_enabled=True
            ),
            action=CfnWebACL.RuleActionProperty(block={})
        )

    @staticmethod
    def common_rule():
        """
        AWS-managed firewall rule set that protects from common attacks
        """
        return CfnWebACL.RuleProperty(
            name='CRSRule',
            priority=2,
            statement=CfnWebACL.StatementProperty(
                managed_rule_group_statement=CfnWebACL.ManagedRuleGroupStatementProperty(
                    name='AWSManagedRulesCommonRuleSet',
                    vendor_name='AWS'
                )
            ),
            visibility_config=CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name='MetricForWebACL-CRS',
                sampled_requests_enabled=True
            ),
            override_action=CfnWebACL.OverrideActionProperty(
                none={}
            )
        )
