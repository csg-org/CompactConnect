from __future__ import annotations

from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk.aws_certificatemanager import Certificate, CertificateValidation
from aws_cdk.aws_cognito import (
    CognitoDomainOptions,
    CustomDomainOptions,
    FeaturePlan,
    Mfa,
    MfaSecondFactor,
    PasswordPolicy,
    StandardThreatProtectionMode,
    UserPool,
)
from aws_cdk.aws_route53 import ARecord, RecordTarget
from aws_cdk.aws_route53_targets import UserPoolDomainTarget
from cdk_nag import NagSuppressions
from constructs import Construct

from common_constructs.resource_scope_mixin import ResourceScopeMixin
from stacks import persistent_stack as ps


class StateAuthUsers(UserPool, ResourceScopeMixin):
    """
    User pool for state API machine-to-machine authentication
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cognito_domain_prefix: str,
        persistent_stack: ps.PersistentStack,
        removal_policy: RemovalPolicy,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            removal_policy=removal_policy,
            # These features are useless without actual users
            feature_plan=FeaturePlan.LITE,
            standard_threat_protection_mode=StandardThreatProtectionMode.NO_ENFORCEMENT,
            # We don't intend this pool for actual users, so we might as well just set some strict policies
            password_policy=PasswordPolicy(
                min_length=32,
                require_digits=True,
                require_lowercase=True,
                require_uppercase=True,
                require_symbols=True,
                temp_password_validity=Duration.days(1),
            ),
            mfa=Mfa.REQUIRED,
            mfa_second_factor=MfaSecondFactor(otp=True, sms=False),
            self_sign_up_enabled=False,
            **kwargs,
        )

        self._add_resource_servers(stack=persistent_stack)
        # Hosted-zone environments get state-auth.{zone} (e.g. state-auth.test.dietitian.jcc.iaapi.io).
        # This is unique per hosted zone, so two accounts deploying the same environment_name
        # (e.g. internal test and CSG test) do not collide on the global Cognito prefix namespace.
        # Managed Login Version 2 is intentionally omitted because this pool is on the Lite plan,
        # which does not support it (the pool has no human users so the login UI is irrelevant).
        # Sandboxes with no hosted zone still use the Cognito prefix, which is fine because
        # sandbox environment names are unique per developer.
        if persistent_stack.hosted_zone:
            hosted_zone = persistent_stack.hosted_zone
            domain_name = f'state-auth.{hosted_zone.zone_name}'
            cert = Certificate(
                scope,
                'StateAuthCert',
                domain_name=domain_name,
                validation=CertificateValidation.from_dns(hosted_zone=hosted_zone),
            )
            self.user_pool_domain = self.add_domain(
                'StateUserPoolDomain',
                custom_domain=CustomDomainOptions(certificate=cert, domain_name=domain_name),
                # managed_login_version intentionally omitted — Lite plan does not support v2
            )
            self.state_auth_domain_record = ARecord(
                self,
                'StateAuthDomainARecord',
                zone=hosted_zone,
                record_name=domain_name,
                target=RecordTarget.from_alias(UserPoolDomainTarget(self.user_pool_domain)),
            )
            CfnOutput(self, 'StateUserPoolDomainName', value=self.user_pool_domain.domain_name)
        else:
            self.user_pool_domain = self.add_domain(
                f'{construct_id}Domain',
                cognito_domain=CognitoDomainOptions(domain_prefix=cognito_domain_prefix),
            )

        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'AwsSolutions-COG3',
                    'reason': 'Threat protection mode enforcement offers no benefit when there are no users.',
                },
                {
                    'id': 'AwsSolutions-COG8',
                    'reason': 'This pool is for state API machine-to-machine auth only; '
                    'Cognito Plus features are not relevant for a user pool with no users.',
                },
            ],
        )
