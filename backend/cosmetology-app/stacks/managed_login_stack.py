import json

from aws_cdk.aws_cognito import CfnManagedLoginBranding
from common_constructs.stack import AppStack
from constructs import Construct

from stacks.persistent_stack import PersistentStack


class ManagedLoginStack(AppStack):
    """
    Stack for managing Cognito managed login branding assets.

    This stack isolates the base64-encoded assets from the persistent stack
    to avoid hitting CloudFormation template size limits.

    The style settings json data can be obtained by styling the user pool in the
    console and then running the following CLI command:
    aws cognito-idp describe-managed-login-branding --managed-login-branding-id
    "<style-id>" --user-pool-id "<user-pool-id>" --region <region>
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        persistent_stack: PersistentStack,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create managed login branding for staff users
        self._create_managed_login_for_staff_users(persistent_stack)

    def _create_managed_login_for_staff_users(self, persistent_stack: PersistentStack):
        """Create managed login branding for staff users"""
        # Load the style settings
        with open('resources/staff_managed_login_style_settings.json') as f:
            branding_settings = json.load(f)

        # Prepare the assets
        branding_assets = persistent_stack.staff_users.prepare_assets_for_managed_login_ui(
            ico_filepath='resources/assets/favicon.ico',
            logo_filepath='resources/assets/compact-connect-logo.png',
            background_file_path='resources/assets/staff-background.png',
        )

        # Create the managed login branding
        CfnManagedLoginBranding(
            self,
            'StaffManagedLoginBranding',
            user_pool_id=persistent_stack.staff_users.user_pool_id,
            assets=branding_assets,
            client_id=persistent_stack.staff_users.ui_client.user_pool_client_id,
            return_merged_resources=False,
            settings=branding_settings,
            use_cognito_provided_values=False,
        )
