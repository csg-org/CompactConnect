from enum import Enum
from typing import List, Optional, Mapping

from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk.aws_cognito import UserPool as CdkUserPool, UserPoolEmail, AccountRecovery, AutoVerifiedAttrs, \
    AdvancedSecurityMode, DeviceTracking, Mfa, MfaSecondFactor, PasswordPolicy, StandardAttributes, \
    CognitoDomainOptions, AuthFlow, OAuthSettings, OAuthFlows, ClientAttributes, \
    CfnUserPoolRiskConfigurationAttachment, OAuthScope, ICustomAttribute, SignInAliases
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from constructs import Construct


class SecurityProfile(Enum):
    RECOMMENDED = 1
    # We need to open up security rules to allow for automated security testing in some environments
    # (but NEVER production)
    VULNERABLE = 2


class UserPool(CdkUserPool):
    # A lot of arguments legitimately need to be passed into the constructor
    def __init__(  # pylint: disable=too-many-arguments
            self, scope: Construct, construct_id: str, *,
            cognito_domain_prefix: str,
            environment_name: str,
            encryption_key: IKey,
            sign_in_aliases: SignInAliases | None,
            standard_attributes: StandardAttributes,
            custom_attributes: Optional[Mapping[str, ICustomAttribute]] = None,
            email: UserPoolEmail,
            removal_policy,
            security_profile: SecurityProfile = SecurityProfile.RECOMMENDED,
            **kwargs
    ):
        if environment_name == 'prod' and security_profile != SecurityProfile.RECOMMENDED:
            raise ValueError('Security profile must be RECOMMENDED in production environments')

        super().__init__(
            scope, construct_id,
            removal_policy=removal_policy,
            deletion_protection=removal_policy != RemovalPolicy.DESTROY,
            email=email,
            # user_invitation=UserInvitationConfig(...),
            account_recovery=AccountRecovery.EMAIL_ONLY,
            auto_verify=AutoVerifiedAttrs(email=True),
            advanced_security_mode=AdvancedSecurityMode.ENFORCED
            if security_profile == SecurityProfile.RECOMMENDED else AdvancedSecurityMode.AUDIT,
            custom_sender_kms_key=encryption_key,
            device_tracking=DeviceTracking(
                challenge_required_on_new_device=True,
                device_only_remembered_on_user_prompt=True
            ),
            mfa=Mfa.REQUIRED
            if security_profile == SecurityProfile.RECOMMENDED else Mfa.OPTIONAL,
            mfa_second_factor=MfaSecondFactor(otp=True, sms=False),
            password_policy=PasswordPolicy(
                min_length=12
            ),
            self_sign_up_enabled=False,
            sign_in_aliases=sign_in_aliases,
            sign_in_case_sensitive=False,
            standard_attributes=standard_attributes,
            custom_attributes=custom_attributes,
            **kwargs
        )

        self.security_profile = security_profile

        self.user_pool_domain = self.add_domain(
            f'{construct_id}Domain',
            cognito_domain=CognitoDomainOptions(
                domain_prefix=cognito_domain_prefix
            )
        )

        CfnOutput(self, f'{construct_id}UsersDomain', value=self.user_pool_domain.domain_name)
        CfnOutput(self, f'{construct_id}UserPoolId', value=self.user_pool_id)

        self._add_risk_configuration(security_profile)

        if security_profile == SecurityProfile.VULNERABLE:
            NagSuppressions.add_resource_suppressions(
                self,
                suppressions=[
                    {
                        'id': 'AwsSolutions-COG2',
                        'reason': 'MFA is disabled to facilitate automated security testing in some pre-production '
                                  'environments.'
                    },
                    {
                        'id': 'AwsSolutions-COG3',
                        'reason': 'Advanced security mode is not enforced in some pre-production environments to'
                                  'facilitate automated security testing.'
                    }
                ]
            )
        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'AwsSolutions-COG1',
                    'reason': 'OWASP ASVS v4.0.3-2.1.9 specifically prohibits requirements on upper or lower case or'
                    ' numbers or special characters.'
                }
            ]
        )

    def add_ui_client(self,
                      callback_urls: List[str],
                      read_attributes: ClientAttributes,
                      write_attributes: ClientAttributes,
                      ui_scopes: List[OAuthScope] = None):
        """
        Creates an app client for the UI to authenticate with the user pool.

        :param callback_urls: The URLs that Cognito allows the UI to redirect to after authentication.
        :param read_attributes: The attributes that the UI can read.
        :param write_attributes: The attributes that the UI can write.
        :param ui_scopes: OAuth scopes that are allowed with this client
        """
        return self.add_client(
            'UIClient',
            auth_flows=AuthFlow(
                admin_user_password=False,
                custom=False,
                user_srp=self.security_profile == SecurityProfile.VULNERABLE,
                user_password=False
            ),
            o_auth=OAuthSettings(
                callback_urls=callback_urls,
                flows=OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=False
                ),
                scopes=ui_scopes
            ),
            access_token_validity=Duration.minutes(60),
            auth_session_validity=Duration.minutes(3),
            enable_token_revocation=True,
            generate_secret=False,
            refresh_token_validity=Duration.days(30),
            write_attributes=write_attributes,
            read_attributes=read_attributes
        )

    def _add_risk_configuration(self, security_profile: SecurityProfile):
        CfnUserPoolRiskConfigurationAttachment(
            self, 'UserPoolRiskConfiguration',
            # Applies to all clients
            client_id='ALL',
            user_pool_id=self.user_pool_id,
            # If Cognito suspects an account take-over event, block all actions and notify the user
            account_takeover_risk_configuration=
            CfnUserPoolRiskConfigurationAttachment.AccountTakeoverRiskConfigurationTypeProperty(
                actions=CfnUserPoolRiskConfigurationAttachment.AccountTakeoverActionsTypeProperty(
                    high_action=CfnUserPoolRiskConfigurationAttachment.AccountTakeoverActionTypeProperty(
                        event_action='BLOCK'
                        if security_profile == SecurityProfile.RECOMMENDED else 'NO_ACTION',
                        notify=True
                    ),
                    medium_action=CfnUserPoolRiskConfigurationAttachment.AccountTakeoverActionTypeProperty(
                        event_action='BLOCK'
                        if security_profile == SecurityProfile.RECOMMENDED else 'NO_ACTION',
                        notify=True
                    ),
                    low_action=CfnUserPoolRiskConfigurationAttachment.AccountTakeoverActionTypeProperty(
                        event_action='BLOCK'
                        if security_profile == SecurityProfile.RECOMMENDED else 'NO_ACTION',
                        notify=True
                    )
                )
            ),
            # If Cognito detects the user trying to register compromised credentials, block the activity
            compromised_credentials_risk_configuration=
            CfnUserPoolRiskConfigurationAttachment.CompromisedCredentialsRiskConfigurationTypeProperty(
                actions=CfnUserPoolRiskConfigurationAttachment.CompromisedCredentialsActionsTypeProperty(
                    event_action='BLOCK'
                    if security_profile == SecurityProfile.RECOMMENDED else 'NO_ACTION'
                )
            )
        )
