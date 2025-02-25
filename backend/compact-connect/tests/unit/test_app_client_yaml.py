import os
import re
import unittest
from glob import glob

import yaml

REQUIRED_FIELDS = ['clientName', 'description', 'createdDate', 'ownerContact', 'environments', 'scopes']

VALID_ENVIRONMENTS = {'test', 'prod'}
SCOPE_ACTIONS = {'readGeneral', 'readSSN', 'readPrivate', 'write', 'admin'}


def _configuration_is_active_for_environment(environment_name: str, active_environments: list[str]) -> bool:
    """Check if the compact configuration is active in the given environment."""
    return environment_name in active_environments


def get_list_of_configured_compacts() -> list[str]:
    """
    Currently, all configuration for compacts and jurisdictions is hardcoded in the compact-config directory.
    This reads the YAML configuration files and returns the list of compacts.
    """

    compacts = []
    # Read all compact configuration YAML files from top level compact-config directory
    for compact_config_file in os.listdir('compact-config'):
        if compact_config_file.endswith('.yml'):
            with open(os.path.join('compact-config', compact_config_file)) as f:
                # convert YAML to JSON
                formatted_compact = yaml.safe_load(f)
                compacts.append(formatted_compact['compactAbbr'])

    return compacts


def get_list_of_configured_jurisdictions_for_compact(compact: str) -> list[str]:
    """
    Get the list of jurisdiction postal codes which are active within a compact.

    Currently, all configuration for compacts and jurisdictions is hardcoded in the compact-config directory.
    This reads the YAML configuration files and returns the list of jurisdiction postal codes.
    """

    jurisdictions = []

    # Read all jurisdiction configuration YAML files from each active compact directory
    for jurisdiction_config_file in os.listdir(os.path.join('compact-config', compact)):
        if jurisdiction_config_file.endswith('.yml'):
            with open(os.path.join('compact-config', compact, jurisdiction_config_file)) as f:
                # convert YAML to JSON
                formatted_jurisdiction = yaml.safe_load(f)
                jurisdictions.append(formatted_jurisdiction['postalAbbreviation'].lower())

    return jurisdictions


class TestAppClientYaml(unittest.TestCase):
    """Test suite to validate app client YAML files against the expected schema."""

    def setUp(self):
        """Load the example schema that all app client YAMLs should follow."""
        self.app_clients_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app_clients')

        self.valid_scopes = []
        # The scopes may include any of the following patterns:
        # {compact}/{action}
        # {jurisdiction}/{compact}.{action}
        for compact in get_list_of_configured_compacts():
            for action in SCOPE_ACTIONS:
                self.valid_scopes.append(f'{compact}/{action}')

            for jurisdiction in get_list_of_configured_jurisdictions_for_compact(compact):
                for action in SCOPE_ACTIONS:
                    self.valid_scopes.append(f'{jurisdiction}/{compact}.{action}')

    def test_all_app_client_yamls_are_valid(self):
        """Verify all YAML files in app_clients directory match the example schema structure."""
        yaml_files = glob(os.path.join(self.app_clients_dir, '*.yml')) + glob(
            os.path.join(self.app_clients_dir, '*.yaml')
        )

        for yaml_file in yaml_files:
            with self.subTest(yaml_file=os.path.basename(yaml_file)):
                with open(yaml_file) as f:
                    yaml_content = yaml.safe_load(f)

                # Verify all required fields are present
                for field in REQUIRED_FIELDS:
                    self.assertIn(
                        field, yaml_content, f"Missing required field '{field}' in {os.path.basename(yaml_file)}"
                    )

                    # Verify environments are valid
                    for env in yaml_content['environments']:
                        self.assertIn(env, VALID_ENVIRONMENTS, f'Invalid environment: {env}')

                    # ensure ownerContact is an email address
                    # at least one @ and .
                    if not re.match(r'[^@]+@[^@]+\.[^@]+', yaml_content['ownerContact']):
                        self.fail(f'Invalid ownerContact: {yaml_content["ownerContact"]}')

                # ensure that each scope defined is in the list of possible valid scopes
                for scope in yaml_content['scopes']:
                    self.assertIn(scope, self.valid_scopes, f'Invalid scope: {scope}')
