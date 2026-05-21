import os
from unittest import TestCase

from aws_cdk import App, RemovalPolicy, Stack
from aws_cdk.assertions import Match, Template
from aws_cdk.aws_cognito import (
    CfnUserPool,
    CfnUserPoolClient,
    CfnUserPoolRiskConfigurationAttachment,
    PasswordPolicy,
    SignInAliases,
    StandardAttributes,
    UserPoolEmail,
)
from aws_cdk.aws_kms import Key

from common_constructs.security_profile import SecurityProfile
from common_constructs.user_pool import UserPool

_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


def _make_pool(stack: Stack, construct_id: str = 'Pool', **kwargs) -> UserPool:
    defaults = {
        'environment_name': 'sandbox',
        'sign_in_aliases': SignInAliases(email=True),
        'standard_attributes': StandardAttributes(),
        'email': UserPoolEmail.with_cognito('noreply@example.com'),
        'notification_from_email': None,
        'ses_identity_arn': None,
        'removal_policy': RemovalPolicy.DESTROY,
        'encryption_key': Key(stack, f'{construct_id}Key'),
    }
    defaults.update(kwargs)
    return UserPool(stack, construct_id, **defaults)


class TestUserPool(TestCase):
    def setUp(self):
        self._original_dir = os.getcwd()
        os.chdir(_FIXTURES_DIR)
        self.addCleanup(os.chdir, self._original_dir)

        self.app = App()
        self.stack = Stack(self.app, 'TestStack')

    # --- MFA settings -------------------------------------------------------

    def test_recommended_profile_requires_mfa(self):
        _make_pool(self.stack, security_profile=SecurityProfile.RECOMMENDED)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(CfnUserPool.CFN_RESOURCE_TYPE_NAME, {'MfaConfiguration': 'ON'})

    def test_vulnerable_profile_makes_mfa_optional(self):
        _make_pool(self.stack, security_profile=SecurityProfile.VULNERABLE)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(CfnUserPool.CFN_RESOURCE_TYPE_NAME, {'MfaConfiguration': 'OPTIONAL'})

    def test_mfa_uses_totp_only(self):
        _make_pool(self.stack)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            {
                'EnabledMfas': ['SOFTWARE_TOKEN_MFA'],
            },
        )

    # --- password policy ----------------------------------------------------

    def test_password_policy_min_length_12(self):
        _make_pool(self.stack)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            {'Policies': {'PasswordPolicy': Match.object_like({'MinimumLength': 12})}},
        )

    def test_password_history_size_4(self):
        _make_pool(self.stack)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            {'Policies': {'PasswordPolicy': Match.object_like({'PasswordHistorySize': 4})}},
        )

    def test_custom_password_policy_kwarg_overrides_default(self):
        _make_pool(self.stack, password_policy=PasswordPolicy(min_length=16))

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            {'Policies': {'PasswordPolicy': Match.object_like({'MinimumLength': 16})}},
        )

    # --- threat protection ---------------------------------------------------

    def test_recommended_profile_full_function_threat_protection(self):
        _make_pool(self.stack, security_profile=SecurityProfile.RECOMMENDED)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            {'UserPoolTier': 'PLUS'},
        )

    def test_recommended_profile_standard_threat_protection_full_function(self):
        _make_pool(self.stack, security_profile=SecurityProfile.RECOMMENDED)

        template = Template.from_stack(self.stack)
        # FULL_FUNCTION standard threat protection
        template.has_resource_properties(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            {
                'UserPoolAddOns': {'AdvancedSecurityMode': 'ENFORCED'},
            },
        )

    def test_vulnerable_profile_audit_only_threat_protection(self):
        _make_pool(self.stack, security_profile=SecurityProfile.VULNERABLE)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            {
                'UserPoolAddOns': {'AdvancedSecurityMode': 'AUDIT'},
            },
        )

    # --- risk configuration -------------------------------------------------

    def test_recommended_profile_risk_config_high_event_action_mfa_required(self):
        _make_pool(self.stack, security_profile=SecurityProfile.RECOMMENDED)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPoolRiskConfigurationAttachment.CFN_RESOURCE_TYPE_NAME,
            {
                'AccountTakeoverRiskConfiguration': {
                    'Actions': Match.object_like({'HighAction': Match.object_like({'EventAction': 'MFA_REQUIRED'})})
                }
            },
        )

    def test_vulnerable_profile_risk_config_high_event_action_no_action(self):
        _make_pool(self.stack, security_profile=SecurityProfile.VULNERABLE)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPoolRiskConfigurationAttachment.CFN_RESOURCE_TYPE_NAME,
            {
                'AccountTakeoverRiskConfiguration': {
                    'Actions': Match.object_like({'HighAction': Match.object_like({'EventAction': 'NO_ACTION'})})
                }
            },
        )

    def test_recommended_profile_compromised_credentials_block(self):
        _make_pool(self.stack, security_profile=SecurityProfile.RECOMMENDED)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPoolRiskConfigurationAttachment.CFN_RESOURCE_TYPE_NAME,
            {'CompromisedCredentialsRiskConfiguration': {'Actions': {'EventAction': 'BLOCK'}}},
        )

    def test_vulnerable_profile_compromised_credentials_no_action(self):
        _make_pool(self.stack, security_profile=SecurityProfile.VULNERABLE)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPoolRiskConfigurationAttachment.CFN_RESOURCE_TYPE_NAME,
            {'CompromisedCredentialsRiskConfiguration': {'Actions': {'EventAction': 'NO_ACTION'}}},
        )

    # --- deletion protection ------------------------------------------------

    def test_deletion_protection_enabled_when_retain(self):
        _make_pool(self.stack, removal_policy=RemovalPolicy.RETAIN)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            {'DeletionProtection': 'ACTIVE'},
        )

    def test_no_deletion_protection_when_destroy(self):
        _make_pool(self.stack, removal_policy=RemovalPolicy.DESTROY)

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPool.CFN_RESOURCE_TYPE_NAME,
            {'DeletionProtection': 'INACTIVE'},
        )

    # --- prod profile guard -------------------------------------------------

    def test_prod_environment_raises_if_not_recommended(self):
        with self.assertRaises(ValueError):
            _make_pool(
                self.stack,
                environment_name='prod',
                security_profile=SecurityProfile.VULNERABLE,
            )

    # --- UI client settings -------------------------------------------------

    def test_ui_client_oauth_uses_authorization_code_grant_not_implicit(self):
        pool = _make_pool(self.stack)
        pool.add_ui_client(
            ui_domain_name=None,
            environment_context={'allow_local_ui': True, 'local_ui_port': '3000'},
            read_attributes=None,
            write_attributes=None,
        )

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME,
            {
                'AllowedOAuthFlows': Match.array_with(['code']),
            },
        )
        clients = template.find_resources(
            CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'AllowedOAuthFlows': ['implicit']}},
        )
        self.assertEqual({}, clients)

    def test_ui_client_sets_short_token_validities(self):
        pool = _make_pool(self.stack)
        pool.add_ui_client(
            ui_domain_name=None,
            environment_context={'allow_local_ui': True, 'local_ui_port': '3000'},
            read_attributes=None,
            write_attributes=None,
        )

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME,
            {
                'AccessTokenValidity': 5,
                'IdTokenValidity': 5,
                'TokenValidityUnits': Match.object_like({'AccessToken': 'minutes', 'IdToken': 'minutes'}),
            },
        )

    def test_ui_client_prevent_user_existence_errors(self):
        pool = _make_pool(self.stack)
        pool.add_ui_client(
            ui_domain_name=None,
            environment_context={'allow_local_ui': True, 'local_ui_port': '3000'},
            read_attributes=None,
            write_attributes=None,
        )

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME,
            {'PreventUserExistenceErrors': 'ENABLED'},
        )

    def test_ui_client_does_not_generate_secret(self):
        pool = _make_pool(self.stack)
        pool.add_ui_client(
            ui_domain_name=None,
            environment_context={'allow_local_ui': True, 'local_ui_port': '3000'},
            read_attributes=None,
            write_attributes=None,
        )

        template = Template.from_stack(self.stack)
        clients = template.find_resources(
            CfnUserPoolClient.CFN_RESOURCE_TYPE_NAME,
            props={'Properties': {'GenerateSecret': True}},
        )
        self.assertEqual({}, clients)

    def test_ui_client_requires_callback_url(self):
        pool = _make_pool(self.stack)
        with self.assertRaises(ValueError):
            pool.add_ui_client(
                ui_domain_name=None,
                environment_context={},
                read_attributes=None,
                write_attributes=None,
            )

    def test_add_default_app_client_domain_creates_cognito_domain(self):
        pool = _make_pool(self.stack)
        pool.add_default_app_client_domain('testprefix')

        template = Template.from_stack(self.stack)
        template.has_resource_properties(
            'AWS::Cognito::UserPoolDomain',
            {'Domain': Match.string_like_regexp('testprefix')},
        )
