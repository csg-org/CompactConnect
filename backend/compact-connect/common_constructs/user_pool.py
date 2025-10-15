import base64
import os
from collections.abc import Mapping

from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk.aws_cognito import (
    AccountRecovery,
    AdvancedSecurityMode,
    AuthFlow,
    AutoVerifiedAttrs,
    CfnManagedLoginBranding,
    CfnUserPoolRiskConfigurationAttachment,
    ClientAttributes,
    CognitoDomainOptions,
    DeviceTracking,
    FeaturePlan,
    ICustomAttribute,
    ManagedLoginVersion,
    Mfa,
    MfaSecondFactor,
    OAuthFlows,
    OAuthScope,
    OAuthSettings,
    PasswordPolicy,
    SignInAliases,
    StandardAttributes,
    UserPoolClient,
    UserPoolEmail,
)
from aws_cdk.aws_cognito import UserPool as CdkUserPool
from aws_cdk.aws_kms import IKey
from cdk_nag import NagSuppressions
from common_constructs.security_profile import SecurityProfile
from constructs import Construct


class UserPool(CdkUserPool):
    # A lot of arguments legitimately need to be passed into the constructor
    def __init__(  # pylint: disable=too-many-arguments
        self,
        scope: Construct,
        construct_id: str,
        *,
        cognito_domain_prefix: str,
        environment_name: str,
        encryption_key: IKey,
        sign_in_aliases: SignInAliases | None,
        standard_attributes: StandardAttributes,
        custom_attributes: Mapping[str, ICustomAttribute] | None = None,
        email: UserPoolEmail,
        notification_from_email: str | None,
        ses_identity_arn: str | None,
        removal_policy,
        security_profile: SecurityProfile = SecurityProfile.RECOMMENDED,
        password_policy: PasswordPolicy = None,
        **kwargs,
    ):
        if environment_name == 'prod' and security_profile != SecurityProfile.RECOMMENDED:
            raise ValueError('Security profile must be RECOMMENDED in production environments')

        super().__init__(
            scope,
            construct_id,
            removal_policy=removal_policy,
            deletion_protection=removal_policy != RemovalPolicy.DESTROY,
            email=email,
            account_recovery=AccountRecovery.EMAIL_ONLY,
            auto_verify=AutoVerifiedAttrs(email=True),
            advanced_security_mode=AdvancedSecurityMode.ENFORCED
            if security_profile == SecurityProfile.RECOMMENDED
            else AdvancedSecurityMode.AUDIT,
            # required for advanced security mode
            feature_plan=FeaturePlan.PLUS,
            custom_sender_kms_key=encryption_key,
            device_tracking=DeviceTracking(
                challenge_required_on_new_device=True, device_only_remembered_on_user_prompt=True
            ),
            mfa=Mfa.REQUIRED if security_profile == SecurityProfile.RECOMMENDED else Mfa.OPTIONAL,
            mfa_second_factor=MfaSecondFactor(otp=True, sms=False, email=False),
            password_policy=PasswordPolicy(
                min_length=12,
                require_digits=True,
                require_lowercase=True,
                require_uppercase=False,
                require_symbols=False,
                password_history_size=4,
            )
            if not password_policy
            else password_policy,
            self_sign_up_enabled=False,
            sign_in_aliases=sign_in_aliases,
            sign_in_case_sensitive=False,
            standard_attributes=standard_attributes,
            custom_attributes=custom_attributes,
            **kwargs,
        )

        self.security_profile = security_profile

        # Configure notification emails if provided
        self.notification_from_email = notification_from_email
        self.ses_identity_arn = ses_identity_arn

        if cognito_domain_prefix:
            self.user_pool_domain = self.add_domain(
                f'{construct_id}Domain',
                cognito_domain=CognitoDomainOptions(domain_prefix=cognito_domain_prefix),
                managed_login_version=ManagedLoginVersion.NEWER_MANAGED_LOGIN,
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
                        'environments.',
                    },
                    {
                        'id': 'AwsSolutions-COG3',
                        'reason': 'Advanced security mode is not enforced in some pre-production environments to'
                        'facilitate automated security testing.',
                    },
                ],
            )
        NagSuppressions.add_resource_suppressions(
            self,
            suppressions=[
                {
                    'id': 'AwsSolutions-COG1',
                    'reason': 'OWASP ASVS v4.0.3-2.1.9 specifically prohibits requirements on upper or lower case or'
                    ' numbers or special characters.',
                }
            ],
        )

    def add_ui_client(
        self,
        ui_domain_name: str,
        environment_context: dict,
        read_attributes: ClientAttributes,
        write_attributes: ClientAttributes,
        ui_scopes: list[OAuthScope] = None,
    ):
        """
        Creates an app client for the UI to authenticate with the user pool.

        :param ui_domain_name: The ui domain name used to determine acceptable redirects.
        :param environment_context: The environment context used to determine acceptable redirects.
        :param read_attributes: The attributes that the UI can read.
        :param write_attributes: The attributes that the UI can write.
        :param ui_scopes: OAuth scopes that are allowed with this client
        """
        callback_urls = []
        if ui_domain_name is not None:
            callback_urls.append(f'https://{ui_domain_name}/auth/callback')
        # This toggle will allow front-end devs to point their local UI at this environment's user pool to support
        # authenticated actions.
        if environment_context.get('allow_local_ui', False):
            local_ui_port = environment_context.get('local_ui_port', '3018')
            callback_urls.append(f'http://localhost:{local_ui_port}/auth/callback')
        if not callback_urls:
            raise ValueError(
                "This app requires a callback url for its authentication path. Either provide 'domain_name' or set "
                "'allow_local_ui' to true in this environment's context."
            )

        logout_urls = []
        if ui_domain_name is not None:
            logout_urls.append(f'https://{ui_domain_name}/Login')
            logout_urls.append(f'https://{ui_domain_name}/Dashboard')
            logout_urls.append(f'https://{ui_domain_name}/Logout')
        # This toggle will allow front-end devs to point their local UI at this environment's user pool to support
        # authenticated actions.
        if environment_context.get('allow_local_ui', False):
            local_ui_port = environment_context.get('local_ui_port', '3018')
            logout_urls.append(f'http://localhost:{local_ui_port}/Login')
            logout_urls.append(f'http://localhost:{local_ui_port}/Dashboard')
            logout_urls.append(f'http://localhost:{local_ui_port}/Logout')
        if not logout_urls:
            raise ValueError(
                "This app requires a logout url for its logout function. Either provide 'domain_name' or set "
                "'allow_local_ui' to true in this environment's context."
            )

        return self.add_client(
            'UIClient',
            auth_flows=AuthFlow(
                # Admin User Password is required for AdminInitiateAuth, which we use for account recovery
                # (and automated testing in test environments)
                admin_user_password=True,
                custom=False,
                user_srp=False if self.security_profile == SecurityProfile.RECOMMENDED else True,
                user_password=False,
            ),
            o_auth=OAuthSettings(
                callback_urls=callback_urls,
                logout_urls=logout_urls,
                flows=OAuthFlows(authorization_code_grant=True, implicit_code_grant=False),
                scopes=ui_scopes,
            ),
            access_token_validity=Duration.minutes(5),
            id_token_validity=Duration.minutes(5),
            auth_session_validity=Duration.minutes(15),
            enable_token_revocation=True,
            generate_secret=False,
            refresh_token_validity=Duration.days(30),
            write_attributes=write_attributes,
            read_attributes=read_attributes,
            prevent_user_existence_errors=True,
        )

    def _add_risk_configuration(self, security_profile: SecurityProfile):
        with open(os.path.join('resources', 'cognito-blocked-notification.txt')) as f:
            blocked_notify_text = f.read()
        with open(os.path.join('resources', 'cognito-no-action-notification.txt')) as f:
            no_action_notify_text = f.read()
        CfnUserPoolRiskConfigurationAttachment(
            self,
            'UserPoolRiskConfiguration',
            # Applies to all clients
            client_id='ALL',
            user_pool_id=self.user_pool_id,
            # If Cognito suspects an account take-over event, notify the user
            account_takeover_risk_configuration=CfnUserPoolRiskConfigurationAttachment.AccountTakeoverRiskConfigurationTypeProperty(
                actions=CfnUserPoolRiskConfigurationAttachment.AccountTakeoverActionsTypeProperty(
                    high_action=CfnUserPoolRiskConfigurationAttachment.AccountTakeoverActionTypeProperty(
                        event_action='MFA_REQUIRED' if security_profile == SecurityProfile.RECOMMENDED else 'NO_ACTION',
                        notify=True,
                    ),
                    medium_action=CfnUserPoolRiskConfigurationAttachment.AccountTakeoverActionTypeProperty(
                        event_action='MFA_REQUIRED' if security_profile == SecurityProfile.RECOMMENDED else 'NO_ACTION',
                        notify=True,
                    ),
                    low_action=CfnUserPoolRiskConfigurationAttachment.AccountTakeoverActionTypeProperty(
                        event_action='MFA_REQUIRED' if security_profile == SecurityProfile.RECOMMENDED else 'NO_ACTION',
                        notify=True,
                    ),
                ),
                **(
                    {
                        'notify_configuration': CfnUserPoolRiskConfigurationAttachment.NotifyConfigurationTypeProperty(
                            source_arn=self.ses_identity_arn,
                            block_email=CfnUserPoolRiskConfigurationAttachment.NotifyEmailTypeProperty(
                                subject='CompactConnect: Account Security Alert',
                                text_body=blocked_notify_text,
                                html_body=f'<p>{blocked_notify_text}</p>',
                            ),
                            mfa_email=CfnUserPoolRiskConfigurationAttachment.NotifyEmailTypeProperty(
                                subject='CompactConnect: Account Security Alert',
                                text_body=no_action_notify_text,
                                html_body=f'<p>{no_action_notify_text}</p>',
                            ),
                            no_action_email=CfnUserPoolRiskConfigurationAttachment.NotifyEmailTypeProperty(
                                subject='CompactConnect: Account Security Alert',
                                text_body=no_action_notify_text,
                                html_body=f'<p>{no_action_notify_text}</p>',
                            ),
                            from_=self.notification_from_email,
                        )
                    }
                    if self.notification_from_email is not None
                    else {}
                ),
            ),
            # If Cognito detects the user trying to register compromised credentials, block the activity
            compromised_credentials_risk_configuration=CfnUserPoolRiskConfigurationAttachment.CompromisedCredentialsRiskConfigurationTypeProperty(
                actions=CfnUserPoolRiskConfigurationAttachment.CompromisedCredentialsActionsTypeProperty(
                    event_action='BLOCK' if security_profile == SecurityProfile.RECOMMENDED else 'NO_ACTION'
                )
            ),
        )

    def add_managed_login_styles(
        self,
        user_pool_client: UserPoolClient,
        branding_assets: list[any] = None,
        branding_settings: dict = None,
    ):
        # Handle custom styles
        login_branding = CfnManagedLoginBranding(
            self,
            'MyCfnManagedLoginBranding',
            user_pool_id=self.user_pool_id,
            assets=branding_assets,
            client_id=user_pool_client.user_pool_client_id,
            return_merged_resources=False,
            settings=branding_settings,
            use_cognito_provided_values=False,
        )

        login_branding.add_dependency(user_pool_client.node.default_child)

    def prepare_assets_for_managed_login_ui(
        self, ico_filepath: str, logo_filepath: str, background_file_path: str | None = None
    ):
        # options found: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-properties-cognito-managedloginbranding-assettype.html#cfn-cognito-managedloginbranding-assettype-category
        assets = []
        base_64_favicon = self.convert_img_to_base_64(ico_filepath)
        assets.append(
            CfnManagedLoginBranding.AssetTypeProperty(
                category='FAVICON_ICO', color_mode='LIGHT', extension='ICO', bytes=base_64_favicon
            )
        )

        base_64_logo = self.convert_img_to_base_64(logo_filepath)
        assets.append(
            CfnManagedLoginBranding.AssetTypeProperty(
                category='FORM_LOGO', color_mode='LIGHT', extension='PNG', bytes=base_64_logo
            )
        )

        if background_file_path:
            base_64_background = self.convert_img_to_base_64(background_file_path)
            assets.append(
                CfnManagedLoginBranding.AssetTypeProperty(
                    category='PAGE_BACKGROUND', color_mode='LIGHT', extension='PNG', bytes=base_64_background
                )
            )

        return assets

    def convert_img_to_base_64(self, file_path: str):
        with open(file_path, 'rb') as binary_file:
            binary_file_data = binary_file.read()
            base64_encoded_data = base64.b64encode(binary_file_data)
            return base64_encoded_data.decode('utf-8')
