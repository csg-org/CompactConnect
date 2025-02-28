from __future__ import annotations

from aws_cdk import Duration
from aws_cdk.aws_cognito import (
    ClientAttributes,
    SignInAliases,
    StandardAttribute,
    StandardAttributes,
    StringAttribute,
    UserPoolEmail,
    UserPoolOperation,
)
from aws_cdk.aws_kms import IKey
from common_constructs.nodejs_function import NodejsFunction
from common_constructs.user_pool import UserPool
from constructs import Construct

from stacks import persistent_stack as ps


class ProviderUsers(UserPool):
    """
    User pool for providers (aka Licensees)
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cognito_domain_prefix: str,
        environment_name: str,
        environment_context: dict,
        encryption_key: IKey,
        user_pool_email: UserPoolEmail,
        removal_policy,
        **kwargs,
    ):
        super().__init__(
            scope,
            construct_id,
            cognito_domain_prefix=cognito_domain_prefix,
            environment_name=environment_name,
            encryption_key=encryption_key,
            removal_policy=removal_policy,
            email=user_pool_email,
            sign_in_aliases=SignInAliases(email=True, username=False),
            standard_attributes=self._configure_user_pool_standard_attributes(),
            custom_attributes={
                # these fields are required in order for the provider to be able to query
                # for their personal profile information. Once these fields are set, they cannot be changed.
                'providerId': StringAttribute(mutable=False),
                'compact': StringAttribute(mutable=False),
            },
            **kwargs,
        )
        stack: ps.PersistentStack = ps.PersistentStack.of(self)

        # Create an app client to allow the front-end to authenticate.
        self.ui_client = self.add_ui_client(
            ui_domain_name=stack.ui_domain_name,
            environment_context=environment_context,
            # For now, we are allowing the user to read and update their email, given name, and family name.
            # we only allow the user to be able to see their providerId and compact, which are custom attributes.
            # If we ever want other attributes to be read or written, they must be added here.
            read_attributes=ClientAttributes()
            .with_standard_attributes(email=True, given_name=True, family_name=True)
            .with_custom_attributes('providerId', 'compact'),
            write_attributes=ClientAttributes().with_standard_attributes(email=True, given_name=True, family_name=True),
        )
        self._add_custom_message_lambda(stack=stack, environment_name=environment_name)

    @staticmethod
    def _configure_user_pool_standard_attributes() -> StandardAttributes:
        """
        The provider user pool standard attributes.

        Note that these values can never change! If you need to make other attributes
        required in the future, you must create an entirely new user pool and migrate
        existing users to the new pool. See https://repost.aws/knowledge-center/cognito-change-user-pool-attributes

        These attributes are used to display on a provider's profile page. We do not
        intend to use them for authentication purposes or for back-end processing.
        """
        return StandardAttributes(
            # We are requiring the following attributes for all users
            # that are registered in the provider user pool.
            email=StandardAttribute(mutable=True, required=True),
            given_name=StandardAttribute(mutable=True, required=True),
            family_name=StandardAttribute(mutable=True, required=True),
            # The following attributes are not required, but we are including them because
            # Cognito does not allow you to add them after the user pool is created, and we
            # may want to use them in the future.
            address=StandardAttribute(mutable=True, required=False),
            birthdate=StandardAttribute(mutable=True, required=False),
            fullname=StandardAttribute(mutable=True, required=False),
            gender=StandardAttribute(mutable=True, required=False),
            last_update_time=StandardAttribute(mutable=True, required=False),
            locale=StandardAttribute(mutable=True, required=False),
            middle_name=StandardAttribute(mutable=True, required=False),
            nickname=StandardAttribute(mutable=True, required=False),
            phone_number=StandardAttribute(mutable=True, required=False),
            preferred_username=StandardAttribute(mutable=True, required=False),
            profile_page=StandardAttribute(mutable=True, required=False),
            profile_picture=StandardAttribute(mutable=True, required=False),
            timezone=StandardAttribute(mutable=True, required=False),
            website=StandardAttribute(mutable=True, required=False),
        )

    def _add_custom_message_lambda(self, stack: ps.PersistentStack, environment_name: str):
        """Add a custom message lambda to the user pool"""

        from_address = 'NONE'
        if stack.hosted_zone:
            from_address = f'noreply@{stack.user_email_notifications.email_identity.email_identity_name}'

        self.custom_message_lambda = NodejsFunction(
            self,
            'CustomMessageLambda',
            description='Cognito custom message lambda',
            lambda_dir='cognito-emails',
            handler='customMessage',
            timeout=Duration.minutes(1),
            environment={
                'FROM_ADDRESS': from_address,
                'COMPACT_CONFIGURATION_TABLE_NAME': stack.compact_configuration_table.table_name,
                'UI_BASE_PATH_URL': stack.get_ui_base_path_url(),
                'ENVIRONMENT_NAME': environment_name,
                **stack.common_env_vars,
            },
        )

        self.add_trigger(
            UserPoolOperation.CUSTOM_MESSAGE,
            self.custom_message_lambda,
        )
