import json
from unittest import TestCase

from common_constructs.frontend_app_config_utility import (
    PersistentStackFrontendAppConfigUtility,
    PersistentStackFrontendAppConfigValues,
)


class TestPersistentStackFrontendAppConfigUtility(TestCase):
    """Tests for the PersistentStackFrontendAppConfigUtility class"""

    def test_setters_set_expected_fields(self):
        """Test that values can be set and retrieved as JSON"""
        # Create a new utility instance
        util = PersistentStackFrontendAppConfigUtility()

        # Set values
        util.set_staff_cognito_values(domain_name='staff-domain.example.com', client_id='staff-client-123')
        util.set_provider_cognito_values(domain_name='provider-domain.example.com', client_id='provider-client-456')
        util.set_domain_names(ui_domain_name='ui.example.com', api_domain_name='api.example.com')

        # Get JSON representation
        config_json = util.get_config_json()
        config_dict = json.loads(config_json)

        # Verify values as a full dictionary
        self.assertEqual(
            {
                'staff_cognito_domain': 'staff-domain.example.com',
                'staff_cognito_client_id': 'staff-client-123',
                'provider_cognito_domain': 'provider-domain.example.com',
                'provider_cognito_client_id': 'provider-client-456',
                'ui_domain_name': 'ui.example.com',
                'api_domain_name': 'api.example.com',
            },
            config_dict,
        )

    def test_getters_return_expected_values(self):
        """Test that getters return expected values"""
        # Create a new utility instance
        util = PersistentStackFrontendAppConfigValues(
            json.dumps(
                {
                    'staff_cognito_domain': 'staff-domain.example.com',
                    'staff_cognito_client_id': 'staff-client-123',
                    'provider_cognito_domain': 'provider-domain.example.com',
                    'provider_cognito_client_id': 'provider-client-456',
                    'ui_domain_name': 'ui.example.com',
                    'api_domain_name': 'api.example.com',
                }
            )
        )

        # Test getters
        self.assertEqual(util.staff_cognito_domain, 'staff-domain.example.com')
        self.assertEqual(util.staff_cognito_client_id, 'staff-client-123')
        self.assertEqual(util.provider_cognito_domain, 'provider-domain.example.com')
        self.assertEqual(util.provider_cognito_client_id, 'provider-client-456')
        self.assertEqual(util.ui_domain_name, 'ui.example.com')
        self.assertEqual(util.api_domain_name, 'api.example.com')
