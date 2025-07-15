# ruff: noqa T201
import os

import boto3
import requests
from botocore.exceptions import ClientError
from sandbox_bootstrap_config import SandboxBootstrapConfig

SANDBOX_USER_PASSWORD = 'Test12345678'  # noqa: S105 this script is used in sandbox environments only


class SandboxBootstrapAPI:
    """API helper class for sandbox bootstrap operations."""

    def __init__(self, config: SandboxBootstrapConfig):
        """Initialize the API helper.

        :param config: Configuration object
        """
        self.config = config
        self._setup_environment()

    def _setup_environment(self):
        """Set up environment variables required for the script."""
        import sandbox_fetch_aws_resources

        api_url, provider_details, staff_details = sandbox_fetch_aws_resources.fetch_resources()
        if api_url is None:
            raise Exception('API base URL is not set. Please check your AWS resources.')

        os.environ['ENVIRONMENT_NAME'] = 'sandbox'
        os.environ['USER_TABLE_NAME'] = staff_details['dynamodb_table']
        os.environ['USER_POOL_ID'] = staff_details['user_pool_id']
        os.environ['API_BASE_URL'] = api_url
        os.environ['PROVIDER_USER_POOL_ID'] = provider_details['user_pool_id']
        os.environ['PROVIDER_USER_CLIENT_ID'] = provider_details['client_id']
        os.environ['STAFF_USER_POOL_ID'] = staff_details['user_pool_id']
        os.environ['STAFF_USER_CLIENT_ID'] = staff_details['client_id']

    def get_api_base_url(self) -> str:
        """Get the base URL for the API."""
        return os.environ.get('API_BASE_URL', 'http://localhost:3000')

    def get_user_tokens(self, email: str, password: str = SANDBOX_USER_PASSWORD, is_staff: bool = False) -> dict:
        """Get Cognito tokens for a user.

        :param email: User email
        :param password: User password
        :param is_staff: Whether this is a staff user
        :return: Authentication result with tokens
        """
        cognito_client = boto3.client('cognito-idp')
        try:
            print(f'   🔐 Authenticating {"staff" if is_staff else "provider"} user: {email}')
            response = cognito_client.admin_initiate_auth(
                UserPoolId=os.environ['STAFF_USER_POOL_ID'] if is_staff else os.environ['PROVIDER_USER_POOL_ID'],
                ClientId=os.environ['STAFF_USER_CLIENT_ID'] if is_staff else os.environ['PROVIDER_USER_CLIENT_ID'],
                AuthFlow='ADMIN_USER_PASSWORD_AUTH',
                AuthParameters={'USERNAME': email, 'PASSWORD': password},
            )
            return response['AuthenticationResult']
        except ClientError as e:
            print(f'Failed to get tokens for user {email}: {str(e)}')
            raise e

    def get_staff_user_auth_headers(self, username: str, password: str = SANDBOX_USER_PASSWORD) -> dict:
        """Get authentication headers for a staff user.

        :param username: Staff user username/email
        :param password: Staff user password
        :return: Headers dictionary with Authorization token
        """
        tokens = self.get_user_tokens(username, password, is_staff=True)
        return {
            'Authorization': 'Bearer ' + tokens['AccessToken'],
        }

    def upload_authorize_net_credentials(self, compact: str, staff_user_email: str):
        """Upload authorize.net credentials for the compact.

        :param compact: The compact abbreviation
        :param staff_user_email: Email of the staff user with admin permissions
        """
        headers = self.get_staff_user_auth_headers(staff_user_email)

        credentials = {
            'processor': 'authorize.net',
            'apiLoginId': self.config.authorize_net_api_login_id,
            'transactionKey': self.config.authorize_net_transaction_key,
        }

        # Check if credentials are already uploaded by trying to get compact config
        current_config = self.get_compact_config(compact, headers)
        if current_config and current_config.get('paymentProcessorPublicFields'):
            print(f'   ⏭️  Payment processor credentials already configured, skipping...')
            return

        print(f'   💳 Uploading authorize.net credentials...')

        response = requests.post(
            url=f'{self.get_api_base_url()}/v1/compacts/{compact}/credentials/payment-processor',
            headers=headers,
            json=credentials,
            timeout=30,  # Give this more time as it makes external API calls to authorize.net
        )

        if response.status_code != 200:
            raise Exception(
                f'Failed to POST payment processor credentials for compact {compact}. '
                f'Status: {response.status_code}, Response: {response.text}'
            )

        # Verify the response contains a success message
        response_data = response.json()
        if 'message' not in response_data or 'Successfully verified credentials' not in response_data['message']:
            raise Exception(f'Unexpected response when uploading payment processor credentials: {response_data}')

        print(f'   ✓ Payment processor credentials verified successfully')

    def get_compact_config(self, compact: str, headers: dict) -> dict | None:
        """Get the current compact configuration.

        :param compact: The compact abbreviation
        :param headers: Authentication headers
        :return: Current compact configuration
        """
        response = requests.get(
            url=f'{self.get_api_base_url()}/v1/compacts/{compact}',
            headers=headers,
            timeout=10,
        )

        if response.status_code == 404:
            return None  # Compact doesn't exist yet
        elif response.status_code != 200:
            raise Exception(f'Failed to GET compact configuration for {compact}. Response: {response.json()}')

        return response.json()

    def configure_compact(self, compact: str, staff_user_email: str, enable_licensee_registration: bool = False):
        """Configure the compact settings.

        :param compact: The compact abbreviation
        :param staff_user_email: Email of the staff user with admin permissions
        :param enable_licensee_registration: Whether to enable licensee registration
        """
        headers = self.get_staff_user_auth_headers(staff_user_email)
        compact_config = self.config.get_compact_config()
        compact_config['licenseeRegistrationEnabled'] = enable_licensee_registration

        # Check current state to avoid unnecessary changes
        current_config = self.get_compact_config(compact, headers)

        if current_config:
            current_enabled = current_config.get('licenseeRegistrationEnabled', False)
            if current_enabled == enable_licensee_registration:
                step = 'enabling licensee registration' if enable_licensee_registration else 'initial setup'
                print(f'   ⏭️  {step.title()} already configured, skipping...')
                return
            elif current_enabled and not enable_licensee_registration:
                print(f'   ⚠️  Licensee registration is already enabled and cannot be disabled, skipping...')
                return

        step = 'enabling licensee registration' if enable_licensee_registration else 'initial setup'
        print(f'   ⚙️  {step.title()}...')

        response = requests.put(
            url=f'{self.get_api_base_url()}/v1/compacts/{compact}',
            headers=headers,
            json=compact_config,
            timeout=10,
        )

        if response.status_code != 200:
            raise Exception(f'Failed to PUT compact configuration for compact {compact}. Response: {response.json()}')

        print(f'   ✓ Compact {step} completed')

    def get_jurisdiction_config(self, compact: str, jurisdiction: str, headers: dict) -> dict | None:
        """Get the current jurisdiction configuration.

        :param compact: The compact abbreviation
        :param jurisdiction: The jurisdiction abbreviation
        :param headers: Authentication headers
        :return: Current jurisdiction configuration
        """
        response = requests.get(
            url=f'{self.get_api_base_url()}/v1/compacts/{compact}/jurisdictions/{jurisdiction}',
            headers=headers,
            timeout=10,
        )

        if response.status_code == 404:
            return None  # Jurisdiction doesn't exist yet
        elif response.status_code != 200:
            raise Exception(f'Failed to GET jurisdiction configuration for {jurisdiction}. Response: {response.json()}')

        return response.json()

    def configure_jurisdiction(self, compact: str, jurisdiction: str, staff_user_email: str, privilege_fees: list):
        """Configure a jurisdiction.

        :param compact: The compact abbreviation
        :param jurisdiction: The jurisdiction abbreviation
        :param staff_user_email: Email of the staff user with admin permissions
        :param privilege_fees: List of privilege fee configurations
        """
        headers = self.get_staff_user_auth_headers(staff_user_email)
        jurisdiction_config = self.config.get_jurisdiction_config(privilege_fees)

        # Check if jurisdiction is already configured
        current_config = self.get_jurisdiction_config(compact, jurisdiction, headers)
        if current_config and current_config.get('licenseeRegistrationEnabled', False):
            print(f'   ⏭️  Jurisdiction {jurisdiction.upper()} already configured, skipping...')
            return

        print(f'   ⚙️  Configuring jurisdiction settings...')

        response = requests.put(
            url=f'{self.get_api_base_url()}/v1/compacts/{compact}/jurisdictions/{jurisdiction}',
            headers=headers,
            json=jurisdiction_config,
            timeout=10,
        )

        if response.status_code != 200:
            raise Exception(
                f'Failed to PUT jurisdiction configuration for {jurisdiction} in {compact}. Response: {response.json()}'
            )

        print(f'   ✓ Jurisdiction {jurisdiction.upper()} configured successfully')

    def upload_license_record(self, compact: str, jurisdiction: str, staff_user_email: str):
        """Upload a test license record.

        :param compact: The compact abbreviation
        :param jurisdiction: The jurisdiction abbreviation
        :param staff_user_email: Email of the staff user with admin permissions
        """
        headers = self.get_staff_user_auth_headers(staff_user_email)
        license_data = self.config.get_license_data()

        # Update the license data to use the correct jurisdiction
        license_data['homeAddressState'] = jurisdiction.upper()

        post_body = [license_data]

        print(f'   📄 Uploading license record...')

        response = requests.post(
            url=f'{self.get_api_base_url()}/v1/compacts/{compact}/jurisdictions/{jurisdiction}/licenses',
            headers=headers,
            json=post_body,
            timeout=10,
        )

        if response.status_code != 200:
            raise Exception(f'Failed to POST license record. Response: {response.json()}')

        print(f'   ✓ License record uploaded successfully')
        return response.json()

    def link_provider_to_license_record(self, compact: str, jurisdiction: str, staff_user_email: str):
        """Link the existing provider user to the license record using staff API.

        :param compact: The compact abbreviation
        :param jurisdiction: The jurisdiction abbreviation
        :param staff_user_email: Email of the staff user with admin permissions
        """
        headers = self.get_staff_user_auth_headers(staff_user_email)
        license_data = self.config.get_license_data()

        # Find the matching license record by querying for the provider
        print(f'   🔍 Finding matching license record...')

        # Query for the provider using the license data
        query_body = {
            'query': {
                'jurisdiction': jurisdiction.lower(),
                'givenName': license_data['givenName'],
                'familyName': license_data['familyName'],
            }
        }

        response = requests.post(
            url=f'{self.get_api_base_url()}/v1/compacts/{compact}/providers/query',
            headers=headers,
            json=query_body,
            timeout=10,
        )

        if response.status_code != 200:
            raise Exception(f'Failed to query providers. Response: {response.json()}')

        providers = response.json().get('providers', [])
        if not providers:
            raise Exception(f'No matching license record found for the test data')

        provider = providers[0]
        provider_id = provider['providerId']

        print(f'   ✓ Found matching license record (Provider ID: {provider_id})')

        # Update the Cognito user to include the custom attributes
        print(f'   🔧 Updating Cognito user attributes...')
        cognito_client = boto3.client('cognito-idp')

        try:
            cognito_client.admin_update_user_attributes(
                UserPoolId=os.environ['PROVIDER_USER_POOL_ID'],
                Username=self.config.base_email,
                UserAttributes=[
                    {'Name': 'custom:compact', 'Value': compact.lower()},
                    {'Name': 'custom:providerId', 'Value': str(provider_id)},
                    {'Name': 'email_verified', 'Value': 'true'},
                ],
            )
            print(f'   ✓ Cognito user attributes updated successfully')
        except ClientError as e:
            print(f'   ⚠️  Warning: Failed to update Cognito user attributes: {str(e)}')
            # Continue anyway as the main linking is done

        return provider_id

    def create_test_provider_user(self, email: str, password: str = 'Test12345678'):
        """Create a test provider user in Cognito.

        :param email: Provider email address
        :param password: Provider password
        :return: User ID
        """
        cognito_client = boto3.client('cognito-idp')
        user_pool_id = os.environ['PROVIDER_USER_POOL_ID']

        try:
            user_data = cognito_client.admin_create_user(
                UserPoolId=user_pool_id,
                Username=email,
                UserAttributes=[{'Name': 'email', 'Value': email}],
                DesiredDeliveryMediums=['EMAIL'],
                TemporaryPassword=password,
            )

            cognito_client.admin_set_user_password(
                UserPoolId=user_pool_id, Username=email, Password=password, Permanent=True
            )

            # Get the user sub
            for attribute in user_data['User']['Attributes']:
                if attribute['Name'] == 'sub':
                    return attribute['Value']

            raise Exception('Failed to get user sub from created user')

        except ClientError as e:
            if e.response['Error']['Code'] == 'UsernameExistsException':
                print(f'   ⏭️  Provider user already exists, using existing user')
                user_data = cognito_client.admin_get_user(UserPoolId=user_pool_id, Username=email)
                for attribute in user_data['UserAttributes']:
                    if attribute['Name'] == 'sub':
                        return attribute['Value']
                raise Exception('Failed to get user sub from existing user')
            else:
                raise Exception(f'Failed to create provider user: {e.response["Error"]["Message"]}')
