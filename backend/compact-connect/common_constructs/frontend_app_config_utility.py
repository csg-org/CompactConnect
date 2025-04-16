import json
from typing import Optional

from aws_cdk import Stack
from aws_cdk.aws_ssm import StringParameter
from constructs import Construct

PERSISTENT_STACK_FRONTEND_APP_CONFIGURATION_PARAMETER_NAME = '/deployment/persistent-stack/frontend_app_configuration'
UI_STACK_FRONTEND_APP_CONFIGURATION_PARAMETER_NAME = '/deployment/ui-stack/frontend_app_configuration'


class PersistentStackFrontendAppConfigUtility:
    """
    Utility class for managing frontend application configuration values from persistent stack in SSM Parameter Store.

    This class provides helper methods for generating and storing configuration
    values that need to be shared between the Persistent stack and Frontend Deployment Stack.
    """

    def __init__(self):
        self._config: dict[str, str] = {}

    def set_staff_cognito_values(self, domain_name: str, client_id: str) -> None:
        """
        Set Cognito configuration values for staff users.

        :param domain_name: The Cognito domain name for staff users
        :param client_id: The UI client ID for staff users
        """
        self._config['staff_cognito_domain'] = domain_name
        self._config['staff_cognito_client_id'] = client_id

    def set_provider_cognito_values(self, domain_name: str, client_id: str) -> None:
        """
        Set Cognito configuration values for provider users.

        :param domain_name: The Cognito domain name for provider users
        :param client_id: The UI client ID for provider users
        """
        self._config['provider_cognito_domain'] = domain_name
        self._config['provider_cognito_client_id'] = client_id

    def set_domain_names(self, ui_domain_name: str, api_domain_name: str) -> None:
        """
        Set UI and API domain names.

        :param ui_domain_name: The domain name for the UI application
        :param api_domain_name: The domain name for the API
        """
        self._config['ui_domain_name'] = ui_domain_name
        self._config['api_domain_name'] = api_domain_name   

    def set_access_logs_bucket_name(self, bucket_name: str) -> None:
        """
        Set the access logs bucket name.

        :param bucket_name: The name of the access logs bucket
        """
        self._config['access_logs_bucket_name'] = bucket_name
        
    def set_license_bulk_uploads_bucket_name(self, bucket_name: str) -> None:
        """
        Set the license bulk uploads bucket name.

        :param bucket_name: The name of the bulk uploads bucket
        """
        self._config['bulk_uploads_bucket_name'] = bucket_name
        
    def set_provider_users_bucket_name(self, bucket_name: str) -> None:
        """
        Set the provider users bucket name.

        :param bucket_name: The name of the provider users bucket
        """
        self._config['provider_users_bucket_name'] = bucket_name

    def get_config_json(self) -> str:
        """
        Generate JSON string representation of the configuration.

        :return: A JSON string containing all configuration values
        """
        return json.dumps(self._config)

    def generate_ssm_parameter(self, scope: Construct, resource_id: str) -> StringParameter:
        """
        Create an SSM Parameter with the current configuration.

        :param scope: The CDK construct scope
        :param resource_id: The ID for the SSM Parameter construct

        :return: The created StringParameter construct
        """
        return StringParameter(
            scope,
            resource_id,
            parameter_name=PERSISTENT_STACK_FRONTEND_APP_CONFIGURATION_PARAMETER_NAME,
            string_value=self.get_config_json(),
            description='UI application configuration values',
        )


class UIStackFrontendAppConfigUtility:
    """
    Utility class for managing frontend application configuration values from the UI stack in SSM Parameter Store.

    This class provides helper methods for generating and storing configuration
    values that need to be shared between the UI stack and Frontend Deployment Stack.
    """

    def __init__(self):
        self._config: dict[str, str] = {}

    def set_ui_bucket_arn(self, ui_bucket_arn: str) -> None:
        """
        Set the ARN of the ui bucket.

        :param ui_bucket_arn: The ARN of the access logs bucket
        """
        self._config['ui_bucket_arn'] = ui_bucket_arn

    def get_config_json(self) -> str:
        """
        Generate JSON string representation of the configuration.

        :return: A JSON string containing all configuration values
        """
        return json.dumps(self._config)

    def generate_ssm_parameter(self, scope: Construct, resource_id: str) -> StringParameter:
        """
        Create an SSM Parameter with the current configuration.

        :param scope: The CDK construct scope
        :param resource_id: The ID for the SSM Parameter construct

        :return: The created StringParameter construct
        """
        return StringParameter(
            scope,
            resource_id,
            parameter_name=UI_STACK_FRONTEND_APP_CONFIGURATION_PARAMETER_NAME,
            string_value=self.get_config_json(),
            description='UI application configuration values',
        )


class PersistentStackFrontendAppConfigValues:
    """
    Class to access frontend application configuration values from the persistent stack loaded from SSM.
    """

    def __init__(self, config_json: str):
        """
        Initialize with configuration JSON from SSM.

        :param config_json: JSON string containing configuration values
        """
        if not config_json:
            raise ValueError('Persistent Stack App Configuration Parameter is required.')

        self._config: dict[str, str] = json.loads(config_json)

    @staticmethod
    def load_persistent_stack_values_from_ssm_parameter(
        stack: Stack,
    ) -> Optional['PersistentStackFrontendAppConfigValues']:
        """
        Load configuration values from an existing SSM Parameter.

        :param stack: The CDK stack

        :return: An instance of UIAppConfigValues with loaded configuration if the parameter exists, otherwise None
        """
        config_value = StringParameter.value_from_lookup(
            stack, PERSISTENT_STACK_FRONTEND_APP_CONFIGURATION_PARAMETER_NAME, default_value=None
        )
        # The first time synth is run, CDK returns a dummy value without actually looking up the value
        # the second time, it will either return a value if the parameter exists, or None. So we check for both of
        # those cases here.
        if (
            config_value is not None
            and config_value != f'dummy-value-for-{PERSISTENT_STACK_FRONTEND_APP_CONFIGURATION_PARAMETER_NAME}'
        ):
            return PersistentStackFrontendAppConfigValues(config_value)
        if config_value == f'dummy-value-for-{PERSISTENT_STACK_FRONTEND_APP_CONFIGURATION_PARAMETER_NAME}':
            return PersistentStackFrontendAppConfigValues._create_dummy_values()

        return None

    @staticmethod
    def _create_dummy_values() -> 'PersistentStackFrontendAppConfigValues':
        """
        Create a mock instance with default values for testing.

        This method is intended for use where bundling is not required (ie unit tests) or CDK returns a dummy parameter
        value, and we just populate the config with dummy values.

        :return: An instance of UIAppConfigValues with default test values
        """
        test_config = {
            'staff_cognito_domain': 'test-staff-domain',
            'staff_cognito_client_id': 'test-staff-client-id',
            'provider_cognito_domain': 'test-provider-domain',
            'provider_cognito_client_id': 'test-provider-client-id',
            'ui_domain_name': 'test-ui.example.com',
            'api_domain_name': 'test-api.example.com',
            'access_logs_bucket_name': 'test-access-logs-bucket-name',
            'bulk_uploads_bucket_name': 'test-bulk-uploads-bucket-name',
            'provider_users_bucket_name': 'test-provider-users-bucket-name',
            # if we are working with dummy values, no need to run an actual bundle
            'should_bundle': False,
        }
        return PersistentStackFrontendAppConfigValues(json.dumps(test_config))

    @property
    def staff_cognito_domain(self) -> str:
        """Get the Cognito domain name for staff users."""
        return self._config['staff_cognito_domain']

    @property
    def staff_cognito_client_id(self) -> str:
        """Get the UI client ID for staff users."""
        return self._config['staff_cognito_client_id']

    @property
    def provider_cognito_domain(self) -> str:
        """Get the Cognito domain name for provider users."""
        return self._config['provider_cognito_domain']

    @property
    def provider_cognito_client_id(self) -> str:
        """Get the UI client ID for provider users."""
        return self._config['provider_cognito_client_id']

    @property
    def ui_domain_name(self) -> str:
        """Get the domain name for the UI application."""
        return self._config['ui_domain_name']

    @property
    def api_domain_name(self) -> str:
        """Get the domain name for the API."""
        return self._config['api_domain_name']
    
    @property
    def access_logs_bucket_name(self) -> str:
        """Get the name of the access logs bucket."""
        return self._config['access_logs_bucket_name']
    
    @property
    def bulk_uploads_bucket_name(self) -> str:
        """Get the name of the bulk uploads bucket."""
        return self._config['bulk_uploads_bucket_name']
    
    @property
    def provider_users_bucket_name(self) -> str:
        """Get the name of the provider users bucket."""
        return self._config['provider_users_bucket_name']

    @property
    def should_bundle(self) -> str:
        """Return bool that determines if front end will run bundling process

        There are many synth steps run during the pipeline deployment as part of the self-mutating process.
        During those phases, we set dummy config values, including this one which tells the bundler not to run and
        eat up extra build time for no purpose.

        This key is not present in our actual values set by the backend, so we set the default
        value here to True, since if the key is not present the config is likely coming from the real parameter
        """
        return self._config.get('should_bundle', True)


class UIStackFrontendAppConfigValues:
    """
    Class to access frontend application configuration values from the UI stack loaded from SSM.
    """

    def __init__(self, config_json: str):
        """
        Initialize with configuration JSON from SSM.

        :param config_json: JSON string containing configuration values
        """
        if not config_json:
            raise ValueError('UI Stack App Configuration Parameter is required.')

        self._config: dict[str, str] = json.loads(config_json)

    @staticmethod
    def load_ui_stack_values_from_ssm_parameter(stack: Stack) -> Optional['UIStackFrontendAppConfigValues']:
        """
        Load configuration values from an existing SSM Parameter.

        :param stack: The CDK stack

        :return: An instance of UIAppConfigValues with loaded configuration if the parameter exists, otherwise None
        """
        config_value = StringParameter.value_from_lookup(
            stack, UI_STACK_FRONTEND_APP_CONFIGURATION_PARAMETER_NAME, default_value=None
        )
        # The first time synth is run, CDK returns a dummy value without actually looking up the value
        # the second time, it will either return a value if the parameter exists, or None. So we check for both of
        # those cases here.
        if (
            config_value is not None
            and config_value != f'dummy-value-for-{UI_STACK_FRONTEND_APP_CONFIGURATION_PARAMETER_NAME}'
        ):
            return UIStackFrontendAppConfigValues(config_value)
        if config_value == f'dummy-value-for-{UI_STACK_FRONTEND_APP_CONFIGURATION_PARAMETER_NAME}':
            return UIStackFrontendAppConfigValues._create_dummy_values()

        return None

    @staticmethod
    def _create_dummy_values() -> 'UIStackFrontendAppConfigValues':
        """
        Create a mock instance with default values for testing.

        This method is intended for use where bundling is not required (ie unit tests) or CDK returns a dummy parameter
        value, and we just populate the config with dummy values.
        """
        test_config = {
            'ui_bucket_arn': 'arn:aws:s3:::test-ui-bucket',
        }
        return UIStackFrontendAppConfigValues(json.dumps(test_config))

    @property
    def ui_bucket_arn(self) -> str:
        """Get the ARN of the access logs bucket."""
        return self._config['ui_bucket_arn']
