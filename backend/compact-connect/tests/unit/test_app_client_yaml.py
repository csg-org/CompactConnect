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
    """
    Finds and returns the path to the cdk.json file in the compact-connect directory.
    
    Starts from the current file's location and traverses parent directories until it
    locates the directory named 'compact-connect', then returns the path to its cdk.json file.
    """
    # Start with the current file and work up to find the cdk.json file
    current_dir = Path(os.path.dirname(os.path.abspath(__file__)))

    # Go up until we reach the compact-connect directory which should contain cdk.json
    while current_dir.name != 'compact-connect' and current_dir.parent != current_dir:
        current_dir = current_dir.parent

    return current_dir / 'cdk.json'


def _load_cdk_json_data():
    """
    Loads and returns the contents of the cdk.json file as a dictionary.
    
    Returns:
        The parsed JSON data from cdk.json, or None if the file does not exist or is invalid.
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
    Retrieves the list of compacts from the `context.compacts` section of the `cdk.json` file.
    
    Returns:
        A list of compact abbreviations if available, or None if the file cannot be loaded.
    """
    cdk_data = _load_cdk_json_data()
    if cdk_data:
        # Extract compacts from the context section
        return cdk_data.get('context', {}).get('compacts', [])
    return None


def get_jurisdictions_from_cdk_json():
    """
    Retrieves the list of jurisdictions from the `context.jurisdictions` section of `cdk.json`.
    
    Returns:
        The list of jurisdictions if available, or None if the data cannot be loaded.
    """
    cdk_data = _load_cdk_json_data()
    if not cdk_data:
        return None

    # Extract all jurisdictions from the context section
    return cdk_data.get('context', {})['jurisdictions']


def get_attestation_configuration():
    """
    Loads and returns the attestation configuration from the attestations.yml file.
    
    Returns:
        dict: The contents of attestations.yml as a dictionary, or an empty dictionary if the file does not exist.
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
        """
        Prepares test directories and computes valid scopes for test validation.
        
        Initializes paths to the app client and compact configuration directories based on the location of the `cdk.json` file, and generates the list of valid scopes for use in test assertions.
        """
        # Find the app_clients directory relative to the cdk.json file
        cdk_dir = os.path.dirname(get_cdk_json_path())
        self.app_clients_dir = os.path.join(cdk_dir, 'app_clients')
        self.compact_config_dir = os.path.join(cdk_dir, 'compact-config')

        # Generate valid scopes
        self.valid_scopes = self._generate_valid_scopes()

    def _generate_valid_scopes(self):
        """
        Constructs and returns a list of valid scope strings using compacts, jurisdictions, and scope actions from configuration.
        
        Returns:
            A list of valid scope strings in the format 'compact/action' and 'jurisdiction/compact.action'.
        """
        valid_scopes = []

        # Get compacts and generate compact-level scopes
        compacts = get_compacts_from_cdk_json()

        # Get active jurisdictions mapping
        cdk_data = _load_cdk_json_data()
        active_jurisdictions = cdk_data['context']['active_compact_member_jurisdictions']

        for compact in compacts:
            for action in SCOPE_ACTIONS:
                valid_scopes.append(f'{compact}/{action}')

            # Get jurisdictions for this compact and generate jurisdiction-level scopes
            for jurisdiction in active_jurisdictions.get(compact, []):
                for action in SCOPE_ACTIONS:
                    valid_scopes.append(f'{jurisdiction}/{compact}.{action}')

        return valid_scopes

    def test_all_app_client_yamls_are_valid(self):
        """
        Validates that all app client YAML files conform to the required schema and value constraints.
        
        Checks each YAML file in the app_clients directory for required fields, valid environments, a properly formatted ownerContact email, and that all listed scopes are among the set of valid scopes. Fails the test if no YAML files are found or if any validation fails.
        """
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
        """
        Tests that the attestations.yml file exists in the compact-config directory and that it contains a top-level 'attestations' list, with each attestation entry including the required fields: 'attestationId', 'displayName', 'text', and 'required'.
        """
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
