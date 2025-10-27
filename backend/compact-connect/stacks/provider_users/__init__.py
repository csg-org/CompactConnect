from aws_cdk import RemovalPolicy
from aws_cdk.aws_cognito import SignInAliases, UserPoolEmail
from aws_cdk.aws_logs import QueryDefinition, QueryString
from common_constructs.frontend_app_config_utility import COGNITO_AUTH_DOMAIN_SUFFIX
from common_constructs.security_profile import SecurityProfile
from common_constructs.stack import AppStack
from constructs import Construct

from stacks.persistent_stack import PersistentStack
from stacks.provider_users.provider_users import ProviderUsers


class ProviderUsersStack(AppStack):
    """
    Stack containing the provider user resources (ie provider user pool resources).

    This stack is separate from the persistent stack to allow for easier management
    and reduce risk of cognito putting our persistent stack in an irrecoverable state.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        app_name: str,
        environment_name: str,
        environment_context: dict,
        persistent_stack: PersistentStack,
        **kwargs,
    ) -> None:
        super().__init__(
            scope, construct_id, environment_context=environment_context, environment_name=environment_name, **kwargs
        )

        self.persistent_stack = persistent_stack

        # If we delete this stack, retain the resource (orphan but prevent data loss) or destroy it (clean up)?
        removal_policy = RemovalPolicy.RETAIN if environment_name == 'prod' else RemovalPolicy.DESTROY

        # Get user pool email settings from persistent stack
        if persistent_stack.hosted_zone:
            notification_from_email = f'no-reply@{persistent_stack.hosted_zone.zone_name}'
            ses_identity_arn = persistent_stack.user_email_notifications.email_identity.email_identity_arn
            user_pool_email_settings = UserPoolEmail.with_ses(
                from_email=notification_from_email,
                ses_verified_domain=persistent_stack.hosted_zone.zone_name,
                configuration_set_name=persistent_stack.user_email_notifications.config_set.configuration_set_name,
            )
        else:
            ses_identity_arn = None
            notification_from_email = None
            user_pool_email_settings = UserPoolEmail.with_cognito()

        # Get security profile from environment context
        security_profile = SecurityProfile[environment_context.get('security_profile', 'RECOMMENDED')]

        # Create the new green provider user pool
        self.provider_users = ProviderUsers(
            self,
            'ProviderUsersGreen',
            app_name=app_name,
            environment_name=environment_name,
            environment_context=environment_context,
            encryption_key=persistent_stack.shared_encryption_key,
            sign_in_aliases=SignInAliases(email=True, username=False),
            user_pool_email=user_pool_email_settings,
            notification_from_email=notification_from_email,
            ses_identity_arn=ses_identity_arn,
            security_profile=security_profile,
            removal_policy=removal_policy,
            persistent_stack=persistent_stack,
        )

        # Add SES dependencies if hosted zone exists
        if persistent_stack.hosted_zone:
            self.provider_users.node.add_dependency(persistent_stack.user_email_notifications.email_identity)
            self.provider_users.node.add_dependency(persistent_stack.user_email_notifications.dmarc_record)
            self.provider_users.node.add_dependency(
                persistent_stack.user_email_notifications.verification_custom_resource
            )

        # Create query definition for provider user pool logs
        QueryDefinition(
            self,
            'ProviderUserCustomEmails',
            query_definition_name='ProviderUserCustomEmails/Lambdas',
            query_string=QueryString(
                fields=['@timestamp', '@log', 'level', 'message', '@message'],
                filter_statements=['level in ["INFO", "WARNING", "ERROR"]'],
                sort='@timestamp desc',
            ),
            log_groups=[
                self.provider_users.custom_message_lambda.log_group,
            ],
        )

        # Create frontend app config parameter for this stack's values
        self._create_frontend_app_config_parameter()

    def _create_frontend_app_config_parameter(self):
        """
        Creates and stores provider user pool configuration in SSM Parameter Store
        for use in the frontend deployment stack.
        """
        from common_constructs.frontend_app_config_utility import ProviderUsersStackFrontendAppConfigUtility

        provider_app_config = ProviderUsersStackFrontendAppConfigUtility()

        auth_domain_name = ''
        if self.persistent_stack.hosted_zone:
            auth_domain_name = self.provider_users.app_client_custom_domain.domain_name
        else:
            auth_domain_name = f'{self.provider_users.default_user_pool_domain.domain_name}{COGNITO_AUTH_DOMAIN_SUFFIX}'

        # Add provider user pool Cognito configuration
        provider_app_config.set_provider_cognito_values(
            domain_name=auth_domain_name,
            client_id=self.provider_users.ui_client.user_pool_client_id,
        )

        # Generate the SSM parameter
        self.provider_frontend_app_config_parameter = provider_app_config.generate_ssm_parameter(
            self, 'ProviderFrontendAppConfigParameter'
        )
