from __future__ import annotations

from aws_cdk import Duration, RemovalPolicy
from aws_cdk.aws_cognito import (
    CognitoDomainOptions,
    FeaturePlan,
    Mfa,
    MfaSecondFactor,
    PasswordPolicy,
    StandardThreatProtectionMode,
    UserPool,
)
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
                }
            ],
        )
