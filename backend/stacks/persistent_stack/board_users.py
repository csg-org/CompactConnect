from aws_cdk import CfnOutput, Duration
from aws_cdk.aws_cognito import UserPool, UserPoolEmail, AccountRecovery, AutoVerifiedAttrs, AdvancedSecurityMode, \
    DeviceTracking, Mfa, MfaSecondFactor, PasswordPolicy, StandardAttributes, StandardAttribute, StringAttribute, \
    CognitoDomainOptions, AuthFlow, OAuthSettings, OAuthFlows, ClientAttributes, ResourceServerScope, \
    CfnUserPoolRiskConfigurationAttachment
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from constructs import Construct


class BoardUsers(UserPool):
    def __init__(
            self, scope: Construct, construct_id: str, *,
            cognito_domain_prefix: str,
            environment_name: str,
            compact_context: dict,
            encryption_key: IKey,
            removal_policy,
            **kwargs
    ):
        super().__init__(
            scope, construct_id,
            removal_policy=removal_policy,
            deletion_protection=False,
            email=UserPoolEmail.with_cognito(),
            # user_invitation=UserInvitationConfig(...),
            account_recovery=AccountRecovery.EMAIL_ONLY,
            auto_verify=AutoVerifiedAttrs(email=True),
            advanced_security_mode=AdvancedSecurityMode.ENFORCED,
            custom_sender_kms_key=encryption_key,
            device_tracking=DeviceTracking(
                challenge_required_on_new_device=True,
                device_only_remembered_on_user_prompt=True
            ),
            mfa=Mfa.REQUIRED if environment_name in ('prod', 'test') else Mfa.OPTIONAL,
            mfa_second_factor=MfaSecondFactor(otp=True, sms=False),
            password_policy=PasswordPolicy(
                min_length=12
            ),
            self_sign_up_enabled=False,
            sign_in_aliases=None,
            sign_in_case_sensitive=False,
            standard_attributes=StandardAttributes(
                email=StandardAttribute(
                    mutable=False,
                    required=True
                )
            ),
            custom_attributes={
                'jurisdiction': StringAttribute(
                    min_len=4,
                    max_len=60,
                    mutable=False
                )
            },
            **kwargs
        )
        if environment_name not in ('prod', 'test'):
            NagSuppressions.add_resource_suppressions(
                self,
                suppressions=[
                    {
                        'id': 'AwsSolutions-COG2',
                        'reason': 'MFA is not necessary in the sandboxes/dev environment as there is '
                                  'no real user data to protect'
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

        self.add_domain(
            'APIDomain',
            cognito_domain=CognitoDomainOptions(
                domain_prefix=cognito_domain_prefix
            )
        )

        CfnOutput(self, 'UserPoolId', value=self.user_pool_id)

        self._add_resource_server(compact_context=compact_context)
        self._add_ui_client()
        self._add_risk_configuration()

        # We will create some admins to get access started for the app and for support
        # for email in compact_context.get('admins', []):
        #     user = CfnUserPoolUser(
        #         self, f'Admin{email}',
        #         user_pool_id=self.user_pool_id,
        #         username=email,
        #         user_attributes=[
        #             CfnUserPoolUser.AttributeTypeProperty(
        #                 name='email',
        #                 value=email
        #             ),
        #             CfnUserPoolUser.AttributeTypeProperty(
        #                 name='custom:jurisdiction',
        #                 value='colorado'
        #             )
        #         ],
        #         desired_delivery_mediums=['EMAIL']
        #     )
        #     user.add_dependency(self.node.default_child)

    def _add_resource_server(self, compact_context: dict):
        self.scopes = {
            jurisdiction: ResourceServerScope(
                scope_name=jurisdiction,
                scope_description=f'Write access for {jurisdiction}'
            )
            for jurisdiction in compact_context['jurisdictions']
        }
        self.add_resource_server(
            'LicenseData',
            identifier='license-data',
            scopes=list(self.scopes.values())
        )

    def _add_ui_client(self):
        self.ui_client = self.add_client(
            'UIClient',
            auth_flows=AuthFlow(
                admin_user_password=True,
                custom=False,
                user_srp=False,
                user_password=False
            ),
            o_auth=OAuthSettings(
                callback_urls=[
                    'http://localhost:8000/auth'
                ],
                flows=OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=False
                )
            ),
            access_token_validity=Duration.minutes(60),
            auth_session_validity=Duration.minutes(3),
            enable_token_revocation=True,
            generate_secret=False,
            refresh_token_validity=Duration.days(30),
            # If you provide no attributes at all here, it will default
            # to making _all_ attributes writeable, so if we want to limit writes,
            # we have to provide at least _one_ that the client _can_ write.
            write_attributes=ClientAttributes().with_standard_attributes(email=True),
            read_attributes=ClientAttributes().with_custom_attributes('jurisdiction')
        )

    def _add_risk_configuration(self):
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
                        event_action='BLOCK',
                        notify=True
                    ),
                    medium_action=CfnUserPoolRiskConfigurationAttachment.AccountTakeoverActionTypeProperty(
                        event_action='BLOCK',
                        notify=True
                    ),
                    low_action=CfnUserPoolRiskConfigurationAttachment.AccountTakeoverActionTypeProperty(
                        event_action='BLOCK',
                        notify=True
                    )
                )
            ),
            # If Cognito detects the user trying to register compromised credentials, block the activity
            compromised_credentials_risk_configuration=
            CfnUserPoolRiskConfigurationAttachment.CompromisedCredentialsRiskConfigurationTypeProperty(
                actions=CfnUserPoolRiskConfigurationAttachment.CompromisedCredentialsActionsTypeProperty(
                    event_action='BLOCK'
                )
            )
        )
