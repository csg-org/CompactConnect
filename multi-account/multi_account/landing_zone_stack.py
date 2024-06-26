from typing import List

from aws_cdk import Stack, RemovalPolicy, ArnFormat
from aws_cdk.aws_controltower import CfnLandingZone
from aws_cdk.aws_iam import PolicyStatement, Effect, ServicePrincipal, Role, ManagedPolicy
from aws_cdk.aws_kms import Key
from constructs import Construct

from multi_account.bare_org_stack import BareOrgStack


class LandingZoneStack(Stack):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            bare_org_stack: BareOrgStack,
            governed_regions: List[str],
            **kwargs
    ):
        """
        Creates an AWS ControlTower LandingZone with its expected IAM roles.

        This stack must be deployed in the Management AWS account.

        :param scope:
        :param construct_id:
        :param bare_org_stack: The Stack object that contains the bare Organization elements needed to
        provision a LandingZone.
        :param governed_regions: A list of AWS regions to be governed by Control Tower.
        """
        super().__init__(scope, construct_id, **kwargs)

        encryption_key = Key(
            self, 'Encryption',
            alias='control-tower',
            description='Encryption key for ControlTower',
            enable_key_rotation=True
        )
        encryption_key.apply_removal_policy(RemovalPolicy.RETAIN)
        encryption_key.add_to_resource_policy(PolicyStatement(
            sid='Allow Config to use this key for encryption',
            effect=Effect.ALLOW,
            principals=[ServicePrincipal('config.amazonaws.com')],
            actions=[
                'kms:GenerateDataKey',
                'kms:Decrypt'
            ],
            resources=['*']
        ))
        encryption_key.add_to_resource_policy(PolicyStatement(
            sid='Allow CloudTrail to use this key for encryption',
            effect=Effect.ALLOW,
            principals=[ServicePrincipal('cloudtrail.amazonaws.com')],
            actions=[
                'kms:GenerateDataKey',
                'kms:Decrypt'
            ],
            resources=['*'],
            conditions={
                'StringEquals': {
                    # arn:aws:cloudtrail:us-east-1:111122223333:trail/aws-controltower-BaselineCloudTrail
                    'aws:SourceArn': self.format_arn(
                        partition=self.partition,
                        service='cloudtrail',
                        region=self.region,
                        account=self.account,
                        resource='trail',
                        resource_name='aws-controltower-BaselineCloudTrail'
                    )
                },
                'StringLike': {
                    # arn:aws:cloudtrail:*:111122223333:trail/*
                    'kms:EncryptionContext:aws:cloudtrail:arn': self.format_arn(
                        partition=self.partition,
                        service='cloudtrail',
                        region='*',
                        account=self.account,
                        resource='trail',
                        resource_name='*'
                    )
                }
            }
        ))

        control_tower_role = Role(
            self, 'AWSControlTowerAdmin',
            role_name='AWSControlTowerAdmin',
            path='/service-role/',
            assumed_by=ServicePrincipal('controltower.amazonaws.com'),
            managed_policies=[
                ManagedPolicy.from_managed_policy_arn(
                    # arn:aws:iam::aws:policy/service-role/AWSConfigRoleForOrganizations
                    self, 'AWSControlTowerServiceRolePolicy', self.format_arn(
                        partition=self.partition,
                        service='iam',
                        region='',
                        account='aws',
                        resource='policy',
                        resource_name='service-role/AWSControlTowerServiceRolePolicy'
                    )
                )
            ]
        )
        control_tower_role.apply_removal_policy(RemovalPolicy.RETAIN)
        control_tower_role.add_to_policy(PolicyStatement(
            effect=Effect.ALLOW,
            actions=[
                'ec2:DescribeAvailabilityZones'
            ],
            resources=['*']
        ))
        control_tower_role.add_to_policy(PolicyStatement(
            effect=Effect.ALLOW,
            actions=[
                'account:EnableRegion',
                'account:ListRegions',
                'account:GetRegionOptStatus'
            ],
            resources=['*']
        ))
        control_tower_role.add_to_policy(PolicyStatement(
            effect=Effect.ALLOW,
            actions=[
                'logs:*LogGroup'
            ],
            resources=[
                # arn:aws:logs:*:*:log-group:aws-controltower/CloudTrailLogs:*
                #                           ^ COLON_RESOURCE_NAME
                self.format_arn(
                    arn_format=ArnFormat.COLON_RESOURCE_NAME,
                    partition=self.partition,
                    service='logs',
                    account='*',
                    region='*',
                    resource='log-group',
                    resource_name='aws-controltower/CloudTrailLogs:*'
                )
            ]
        ))

        cloudtrail_role = Role(
            self, 'AWSControlTowerCloudTrailRole',
            role_name='AWSControlTowerCloudTrailRole',
            path='/service-role/',
            assumed_by=ServicePrincipal('cloudtrail.amazonaws.com')
        )
        cloudtrail_role.apply_removal_policy(RemovalPolicy.RETAIN)
        cloudtrail_role.add_to_policy(PolicyStatement(
            effect=Effect.ALLOW,
            actions=[
                'logs:CreateLogStream',
                'logs:PutLogEvents'
            ],
            resources=[
                # arn:aws:logs:*:*:log-group:aws-controltower/CloudTrailLogs:*
                #                           ^ COLON_RESOURCE_NAME
                self.format_arn(
                    arn_format=ArnFormat.COLON_RESOURCE_NAME,
                    partition=self.partition,
                    service='logs',
                    account='*',
                    region='*',
                    resource='log-group',
                    resource_name='aws-controltower/CloudTrailLogs:*'
                )
            ]
        ))

        config_aggregator_role = Role(
            self, 'AWSControlTowerConfigAggregatorRoleForOrganizations',
            path='/service-role/',
            assumed_by=ServicePrincipal('config.amazonaws.com'),
            managed_policies=[
                ManagedPolicy.from_managed_policy_arn(
                    self, 'AWSConfigRoleForOrganizations', self.format_arn(
                        partition=self.partition,
                        service='iam',
                        region='',
                        account='aws',
                        resource='policy',
                        resource_name='service-role/AWSConfigRoleForOrganizations'
                    )
                )
            ]
        )
        config_aggregator_role.apply_removal_policy(RemovalPolicy.RETAIN)

        stack_set_role = Role(
            self, 'AWSControlTowerStackSetRole',
            role_name='AWSControlTowerStackSetRole',
            path='/service-role/',
            assumed_by=ServicePrincipal('cloudformation.amazonaws.com')
        )
        stack_set_role.apply_removal_policy(RemovalPolicy.RETAIN)
        stack_set_role.add_to_policy(PolicyStatement(
            effect=Effect.ALLOW,
            actions=['sts:AssumeRole'],
            resources=[
                # arn:aws:iam::*:role/AWSControlTowerExecution
                self.format_arn(
                    partition=self.partition,
                    service='iam',
                    region='',
                    account='*',
                    resource='role',
                    resource_name='AWSControlTowerExecution'
                )
            ]
        ))

        landing_zone = CfnLandingZone(
            self, 'LandingZone',
            version='3.3',
            manifest={
                'accessManagement': {
                    'enabled': True
                },
                'securityRoles': {
                    'accountId': bare_org_stack.audit_account.attr_account_id
                },
                'governedRegions': governed_regions,
                # NOTE: ControlTower will create and register OUs declared here, but they will
                # not be explicitly reflected in a CFn Stack. It will also move the log/audit
                # accounts into the Security OU, which will show up as Drift in the
                # BareOrganization CFn Stack.
                # Reference:
                # https://docs.aws.amazon.com/controltower/latest/userguide/getting-started-expectations-api.html
                'organizationStructure': {
                    'security': {
                        'name': 'CT-Security',
                    },
                    'sandbox': {
                        'name': 'Sandbox'
                    },
                },
                'centralizedLogging': {
                    'accountId': bare_org_stack.logging_account.attr_account_id,
                    'configurations': {
                        'loggingBucket': {
                            'retentionDays': 365
                        },
                        'kmsKeyArn': encryption_key.key_arn,
                        'accessLoggingBucket': {
                            'retentionDays': 3650
                        }
                    },
                    'enabled': True
                }
            }
        )
        landing_zone.apply_removal_policy(RemovalPolicy.RETAIN)
        landing_zone.add_dependency(control_tower_role.node.default_child)
        landing_zone.add_dependency(cloudtrail_role.node.default_child)
        landing_zone.add_dependency(config_aggregator_role.node.default_child)
        landing_zone.add_dependency(stack_set_role.node.default_child)
