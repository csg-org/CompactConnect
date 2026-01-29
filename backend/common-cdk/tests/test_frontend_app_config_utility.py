"""
Tests for the frontend_app_config_utility module.
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from common_constructs.frontend_app_config_utility import (
    AppId,
    PersistentStackFrontendAppConfigUtility,
    PersistentStackFrontendAppConfigValues,
    ProviderUsersStackFrontendAppConfigValues,
    _get_persistent_stack_parameter_name,
    _get_provider_users_stack_parameter_name,
)


class TestAppId(TestCase):
    """Tests for the AppId enum."""

    def test_jcc_value(self):
        """Test JCC app ID has expected value."""
        self.assertEqual('jcc', AppId.JCC.value)

    def test_cosmetology_value(self):
        """Test COSMETOLOGY app ID has expected value."""
        self.assertEqual('cosmetology', AppId.COSMETOLOGY.value)


class TestParameterNameGeneration(TestCase):
    """Tests for SSM parameter name generation functions."""

    def test_persistent_stack_parameter_name_default(self):
        """Test default parameter name uses JCC."""
        name = _get_persistent_stack_parameter_name()
        self.assertEqual('/app/jcc/deployment/persistent-stack/frontend_app_configuration', name)

    def test_persistent_stack_parameter_name_jcc(self):
        """Test parameter name for JCC app."""
        name = _get_persistent_stack_parameter_name(AppId.JCC)
        self.assertEqual('/app/jcc/deployment/persistent-stack/frontend_app_configuration', name)

    def test_persistent_stack_parameter_name_cosmetology(self):
        """Test parameter name for COSMETOLOGY app."""
        name = _get_persistent_stack_parameter_name(AppId.COSMETOLOGY)
        self.assertEqual('/app/cosmetology/deployment/persistent-stack/frontend_app_configuration', name)

    def test_provider_users_stack_parameter_name_default(self):
        """Test default parameter name uses JCC."""
        name = _get_provider_users_stack_parameter_name()
        self.assertEqual('/app/jcc/deployment/provider-users-stack/frontend_app_configuration', name)

    def test_provider_users_stack_parameter_name_jcc(self):
        """Test parameter name for JCC app."""
        name = _get_provider_users_stack_parameter_name(AppId.JCC)
        self.assertEqual('/app/jcc/deployment/provider-users-stack/frontend_app_configuration', name)

    def test_provider_users_stack_parameter_name_cosmetology(self):
        """Test parameter name for COSMETOLOGY app."""
        name = _get_provider_users_stack_parameter_name(AppId.COSMETOLOGY)
        self.assertEqual('/app/cosmetology/deployment/provider-users-stack/frontend_app_configuration', name)


class TestPersistentStackFrontendAppConfigUtility(TestCase):
    """Tests for the PersistentStackFrontendAppConfigUtility class."""

    def test_default_app_id_is_jcc(self):
        """Test that default app_id is JCC."""
        util = PersistentStackFrontendAppConfigUtility()
        self.assertEqual(AppId.JCC, util._app_id)  # noqa: SLF001

    def test_cosmetology_app_id(self):
        """Test setting COSMETOLOGY app_id."""
        util = PersistentStackFrontendAppConfigUtility(app_id=AppId.COSMETOLOGY)
        self.assertEqual(AppId.COSMETOLOGY, util._app_id)  # noqa: SLF001

    def test_set_staff_cognito_values(self):
        """Test setting staff Cognito values."""
        util = PersistentStackFrontendAppConfigUtility()
        util.set_staff_cognito_values(domain_name='test-domain', client_id='test-client')

        config = json.loads(util.get_config_json())
        self.assertEqual('test-domain', config['staff_cognito_domain'])
        self.assertEqual('test-client', config['staff_cognito_client_id'])

    def test_set_domain_names(self):
        """Test setting domain names."""
        util = PersistentStackFrontendAppConfigUtility()
        util.set_domain_names(
            ui_domain_name='ui.example.com',
            api_domain_name='api.example.com',
            search_api_domain_name='search.example.com',
        )

        config = json.loads(util.get_config_json())
        self.assertEqual('ui.example.com', config['ui_domain_name'])
        self.assertEqual('api.example.com', config['api_domain_name'])
        self.assertEqual('search.example.com', config['search_api_domain_name'])


class TestPersistentStackFrontendAppConfigValues(TestCase):
    """Tests for the PersistentStackFrontendAppConfigValues class."""

    def test_load_jcc_uses_string_parameter_lookup(self):
        """Test that JCC app uses standard StringParameter.value_from_lookup."""
        mock_stack = MagicMock()
        with patch('common_constructs.frontend_app_config_utility.StringParameter.value_from_lookup') as mock_lookup:
            mock_lookup.return_value = json.dumps(
                {
                    'staff_cognito_domain': 'test-domain',
                    'staff_cognito_client_id': 'test-client',
                }
            )

            result = PersistentStackFrontendAppConfigValues.load_persistent_stack_values_from_ssm_parameter(
                mock_stack,
                app_id=AppId.JCC,
            )

            mock_lookup.assert_called_once()
            self.assertIsNotNone(result)
            self.assertEqual('test-domain', result.staff_cognito_domain)

    def test_load_cosmetology_uses_string_parameter_lookup(self):
        """Test that COSMETOLOGY app uses standard StringParameter.value_from_lookup (same-account)."""
        mock_stack = MagicMock()
        with patch('common_constructs.frontend_app_config_utility.StringParameter.value_from_lookup') as mock_lookup:
            mock_lookup.return_value = json.dumps(
                {
                    'staff_cognito_domain': 'cosmo-domain',
                    'staff_cognito_client_id': 'cosmo-client',
                }
            )

            result = PersistentStackFrontendAppConfigValues.load_persistent_stack_values_from_ssm_parameter(
                mock_stack,
                app_id=AppId.COSMETOLOGY,
            )

            mock_lookup.assert_called_once()
            self.assertIsNotNone(result)
            self.assertEqual('cosmo-domain', result.staff_cognito_domain)

    def test_dummy_value_returns_dummy_config(self):
        """Test that dummy value returns dummy configuration."""
        mock_stack = MagicMock()
        parameter_name = _get_persistent_stack_parameter_name(AppId.JCC)

        with patch('common_constructs.frontend_app_config_utility.StringParameter.value_from_lookup') as mock_lookup:
            mock_lookup.return_value = f'dummy-value-for-{parameter_name}'

            result = PersistentStackFrontendAppConfigValues.load_persistent_stack_values_from_ssm_parameter(
                mock_stack,
                app_id=AppId.JCC,
            )

            self.assertIsNotNone(result)
            # Verify it returns dummy values
            self.assertEqual('test-staff-domain', result.staff_cognito_domain)


class TestProviderUsersStackFrontendAppConfigValues(TestCase):
    """Tests for the ProviderUsersStackFrontendAppConfigValues class."""

    def test_load_jcc_uses_string_parameter_lookup(self):
        """Test that JCC app uses standard StringParameter.value_from_lookup."""
        mock_stack = MagicMock()
        with patch('common_constructs.frontend_app_config_utility.StringParameter.value_from_lookup') as mock_lookup:
            mock_lookup.return_value = json.dumps(
                {
                    'provider_cognito_domain': 'test-provider-domain',
                    'provider_cognito_client_id': 'test-provider-client',
                }
            )

            result = ProviderUsersStackFrontendAppConfigValues.load_provider_users_stack_values_from_ssm_parameter(
                mock_stack,
                app_id=AppId.JCC,
            )

            mock_lookup.assert_called_once()
            self.assertIsNotNone(result)
            self.assertEqual('test-provider-domain', result.provider_cognito_domain)
