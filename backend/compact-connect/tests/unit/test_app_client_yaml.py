import json
import os
import re
import unittest
from glob import glob
from pathlib import Path

import yaml

REQUIRED_FIELDS = ['clientName', 'description', 'createdDate', 'ownerContact', 'environments', 'scopes']

VALID_ENVIRONMENTS = {'test', 'beta', 'prod'}
SCOPE_ACTIONS = {'readGeneral', 'readSSN', 'readPrivate', 'write', 'admin'}


def get_cdk_json_path():
    """Get the path to the CDK.json file."""
    # Start with the current file and work up to find the cdk.json file
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    # Go up until we reach the compact-connect directory which should contain cdk.json
    while current_dir.name != 'compact-connect' and current_dir.parent != current_dir:
        current_dir = current_dir.parent

    return current_dir / 'cdk.json'


def _load_cdk_json_data():
    """
    Helper function to load data from the CDK.json file.

    return: the loaded CDK data or None if loading fails
    """
    cdk_json_path = get_cdk_json_path()

    if cdk_json_path.exists():
        try:
            with open(cdk_json_path) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    return None


def get_compacts_from_cdk_json():
    """
    Get the list of compacts from the CDK.json file.

    return: the list of compact abbreviations or None if the data couldn't be loaded
    """
    cdk_data = _load_cdk_json_data()
    if cdk_data:
        # Extract compacts from the context section
        return cdk_data.get('context', {}).get('compacts', [])
    return None


def get_jurisdictions_from_cdk_json():
    """
    Get the list of jurisdictions from the CDK.json file.

    param: compact: Optional compact to filter jurisdictions for.
                If None, returns a dictionary of jurisdictions for all compacts.

    return: the list of jurisdictions for the specified compact,
                     or dictionary mapping compacts to jurisdictions
    """
    cdk_data = _load_cdk_json_data()
    if not cdk_data:
        return None

    # Extract all jurisdictions from the context section
    return cdk_data.get('context', {})['jurisdictions']


def get_attestation_configuration():
    """
    Get attestation configuration from attestations.yml file.

    We keep using the YAML file for attestations as this will not be self-serve.
    """
    # Get the base directory where attestations.yml is located
    compact_config_dir = os.path.join(os.path.dirname(get_cdk_json_path()), 'compact-config')
    attestations_file = os.path.join(compact_config_dir, 'attestations.yml')

    if os.path.exists(attestations_file):
        with open(attestations_file) as f:
            return yaml.safe_load(f)
    return {}


class TestAppClientYaml(unittest.TestCase):
    """Test suite to validate app client YAML files against the expected schema."""

    def setUp(self):
        """Set up the test environment and determine valid scopes."""
        # Find the app_clients directory relative to the cdk.json file
        cdk_dir = os.path.dirname(get_cdk_json_path())
        self.app_clients_dir = os.path.join(cdk_dir, 'app_clients')
        self.compact_config_dir = os.path.join(cdk_dir, 'compact-config')

        # Generate valid scopes
        self.valid_scopes = self._generate_valid_scopes()

    def _generate_valid_scopes(self):
        """Generate a list of valid scopes based on configured compacts and jurisdictions."""
        valid_scopes = []

        # Get compacts and generate compact-level scopes
        compacts = get_compacts_from_cdk_json()
        for compact in compacts:
            for action in SCOPE_ACTIONS:
                valid_scopes.append(f'{compact}/{action}')

            # Get jurisdictions for this compact and generate jurisdiction-level scopes
            jurisdictions = get_jurisdictions_from_cdk_json()
            for jurisdiction in jurisdictions:
                for action in SCOPE_ACTIONS:
                    valid_scopes.append(f'{jurisdiction}/{compact}.{action}')

        return valid_scopes

    def test_all_app_client_yamls_are_valid(self):
        """Verify all YAML files in app_clients directory match the expected schema structure."""
        yaml_files = glob(os.path.join(self.app_clients_dir, '*.yml')) + glob(
            os.path.join(self.app_clients_dir, '*.yaml')
        )

        # Skip the README or other non-app client files
        if not yaml_files:
            self.fail('No app client YAML files found to validate')

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

                # Ensure ownerContact is a valid email address
                if not re.match(r'[^@]+@[^@]+\.[^@]+', yaml_content['ownerContact']):
                    self.fail(f'Invalid ownerContact: {yaml_content["ownerContact"]}')

                # Ensure that each scope defined is in the list of possible valid scopes
                for scope in yaml_content['scopes']:
                    self.assertIn(scope, self.valid_scopes, f'Invalid scope: {scope} in {os.path.basename(yaml_file)}')

    def test_attestations_yaml_is_valid(self):
        """Verify the attestations.yml file exists and has a valid structure."""
        attestations_file = os.path.join(self.compact_config_dir, 'attestations.yml')

        # Skip if attestations.yml doesn't exist
        if not os.path.exists(attestations_file):
            self.fail('Missing attestations file')

        with open(attestations_file) as f:
            attestations_data = yaml.safe_load(f)

        # Verify the structure
        self.assertIn('attestations', attestations_data, "attestations.yml must contain an 'attestations' key")
        self.assertIsInstance(attestations_data['attestations'], list, 'attestations must be a list')

        # Verify each attestation has required fields
        for attestation in attestations_data['attestations']:
            self.assertIn('attestationId', attestation, 'Each attestation must have an attestationId')
            self.assertIn('displayName', attestation, 'Each attestation must have a displayName')
            self.assertIn('text', attestation, 'Each attestation must have text content')
            self.assertIn('required', attestation, "Each attestation must specify if it's required")
