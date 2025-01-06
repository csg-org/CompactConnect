import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from marshmallow import ValidationError
from moto import mock_aws

from .. import TstFunction

TEST_ENVIRONMENT_NAME = 'test'
MOCK_CURRENT_TIMESTAMP = '2024-11-08T23:59:59+00:00'


def generate_mock_attestation():
    return {
        'attestationId': 'jurisprudence-confirmation',
        'displayName': 'Jurisprudence Confirmation',
        'description': 'For displaying the jurisprudence confirmation',
        'text': 'You attest that you have read and understand the jurisprudence requirements '
        'for all states you are purchasing privileges for.',
        'required': True,
        'locale': 'en',
    }


def generate_single_root_compact_config(compact_name: str, active_environments: list):
    return {
        'compactName': compact_name,
        'compactCommissionFee': {'feeType': 'FLAT_RATE', 'feeAmount': 3.5},
        'compactOperationsTeamEmails': [],
        'compactAdverseActionsNotificationEmails': [],
        'compactSummaryReportNotificationEmails': [],
        'activeEnvironments': active_environments,
        'attestations': [generate_mock_attestation()],
    }


def generate_single_jurisdiction_config(jurisdiction_name: str, postal_abbreviation: str, active_environments: list):
    return {
        'jurisdictionName': jurisdiction_name,
        'postalAbbreviation': postal_abbreviation,
        'jurisdictionFee': 100,
        'militaryDiscount': {'active': True, 'discountType': 'FLAT_RATE', 'discountAmount': 10},
        'jurisdictionOperationsTeamEmails': ['cloud-team@example.com'],
        'jurisdictionAdverseActionsNotificationEmails': [],
        'jurisdictionSummaryReportNotificationEmails': [],
        'jurisprudenceRequirements': {'required': True},
        'activeEnvironments': active_environments,
    }


def generate_mock_compact_configuration():
    return {
        'compacts': [
            generate_single_root_compact_config('aslp', active_environments=[TEST_ENVIRONMENT_NAME]),
            generate_single_root_compact_config('octp', active_environments=[]),
        ],
        'jurisdictions': {
            'aslp': [
                generate_single_jurisdiction_config('nebraska', 'ne', active_environments=[TEST_ENVIRONMENT_NAME]),
                generate_single_jurisdiction_config('ohio', 'oh', active_environments=[]),
            ],
            'octp': [
                generate_single_jurisdiction_config('nebraska', 'ne', active_environments=['sandbox']),
                generate_single_jurisdiction_config('ohio', 'oh', active_environments=['sandbox']),
            ],
        },
    }


@mock_aws
class TestCompactConfigurationUploader(TstFunction):
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_TIMESTAMP))
    def test_compact_configuration_uploader_store_all_config(self):
        from handlers.compact_config_uploader import on_event

        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'compact_configuration': json.dumps(generate_mock_compact_configuration()),
            },
        }

        on_event(event, self.mock_context)

        # now query for all the aslp compact configurations
        aslp_response = self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq('aslp#CONFIGURATION'),
        )

        octp_response = self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq('octp#CONFIGURATION'),
        )

        items = aslp_response['Items'] + octp_response['Items']

        self.assertEqual(
            [
                {
                    'compactAdverseActionsNotificationEmails': [],
                    'compactCommissionFee': {'feeAmount': Decimal('3.5'), 'feeType': 'FLAT_RATE'},
                    'compactName': 'aslp',
                    'compactOperationsTeamEmails': [],
                    'compactSummaryReportNotificationEmails': [],
                    'dateOfUpdate': MOCK_CURRENT_TIMESTAMP,
                    'pk': 'aslp#CONFIGURATION',
                    'sk': 'aslp#CONFIGURATION',
                    'type': 'compact',
                },
                {
                    'compact': 'aslp',
                    'dateOfUpdate': MOCK_CURRENT_TIMESTAMP,
                    'jurisdictionAdverseActionsNotificationEmails': [],
                    'jurisdictionFee': Decimal('100'),
                    'jurisdictionName': 'nebraska',
                    'jurisdictionOperationsTeamEmails': ['cloud-team@example.com'],
                    'jurisdictionSummaryReportNotificationEmails': [],
                    'jurisprudenceRequirements': {'required': True},
                    'militaryDiscount': {'active': True, 'discountAmount': Decimal('10'), 'discountType': 'FLAT_RATE'},
                    'pk': 'aslp#CONFIGURATION',
                    'postalAbbreviation': 'ne',
                    'sk': 'aslp#JURISDICTION#ne',
                    'type': 'jurisdiction',
                },
                {
                    'compact': 'aslp',
                    'dateOfUpdate': MOCK_CURRENT_TIMESTAMP,
                    'jurisdictionAdverseActionsNotificationEmails': [],
                    'jurisdictionFee': Decimal('100'),
                    'jurisdictionName': 'ohio',
                    'jurisdictionOperationsTeamEmails': ['cloud-team@example.com'],
                    'jurisdictionSummaryReportNotificationEmails': [],
                    'jurisprudenceRequirements': {'required': True},
                    'militaryDiscount': {'active': True, 'discountAmount': Decimal('10'), 'discountType': 'FLAT_RATE'},
                    'pk': 'aslp#CONFIGURATION',
                    'postalAbbreviation': 'oh',
                    'sk': 'aslp#JURISDICTION#oh',
                    'type': 'jurisdiction',
                },
                {
                    'compactAdverseActionsNotificationEmails': [],
                    'compactCommissionFee': {'feeAmount': Decimal('3.5'), 'feeType': 'FLAT_RATE'},
                    'compactName': 'octp',
                    'compactOperationsTeamEmails': [],
                    'compactSummaryReportNotificationEmails': [],
                    'dateOfUpdate': MOCK_CURRENT_TIMESTAMP,
                    'pk': 'octp#CONFIGURATION',
                    'sk': 'octp#CONFIGURATION',
                    'type': 'compact',
                },
                {
                    'compact': 'octp',
                    'dateOfUpdate': MOCK_CURRENT_TIMESTAMP,
                    'jurisdictionAdverseActionsNotificationEmails': [],
                    'jurisdictionFee': Decimal('100'),
                    'jurisdictionName': 'nebraska',
                    'jurisdictionOperationsTeamEmails': ['cloud-team@example.com'],
                    'jurisdictionSummaryReportNotificationEmails': [],
                    'jurisprudenceRequirements': {'required': True},
                    'militaryDiscount': {'active': True, 'discountAmount': Decimal('10'), 'discountType': 'FLAT_RATE'},
                    'pk': 'octp#CONFIGURATION',
                    'postalAbbreviation': 'ne',
                    'sk': 'octp#JURISDICTION#ne',
                    'type': 'jurisdiction',
                },
                {
                    'compact': 'octp',
                    'dateOfUpdate': MOCK_CURRENT_TIMESTAMP,
                    'jurisdictionAdverseActionsNotificationEmails': [],
                    'jurisdictionFee': Decimal('100'),
                    'jurisdictionName': 'ohio',
                    'jurisdictionOperationsTeamEmails': ['cloud-team@example.com'],
                    'jurisdictionSummaryReportNotificationEmails': [],
                    'jurisprudenceRequirements': {'required': True},
                    'militaryDiscount': {'active': True, 'discountAmount': Decimal('10'), 'discountType': 'FLAT_RATE'},
                    'pk': 'octp#CONFIGURATION',
                    'postalAbbreviation': 'oh',
                    'sk': 'octp#JURISDICTION#oh',
                    'type': 'jurisdiction',
                },
            ],
            items,
        )

    def test_compact_configuration_uploader_raises_exception_on_invalid_jurisdiction_config(self):
        from handlers.compact_config_uploader import on_event

        mock_configuration = generate_mock_compact_configuration()
        # An empty ops team email is not allowed
        mock_configuration['jurisdictions']['aslp'][0]['jurisdictionOperationsTeamEmails'] = []

        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'compact_configuration': json.dumps(mock_configuration),
            },
        }

        with self.assertRaises(ValidationError):
            on_event(event, self.mock_context)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_TIMESTAMP))
    def test_compact_configuration_uploader_uploads_attestations(self):
        """Test that attestations are correctly uploaded to DynamoDB."""
        from handlers.compact_config_uploader import on_event

        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'compact_configuration': json.dumps(generate_mock_compact_configuration()),
            },
        }

        on_event(event, self.mock_context)

        # Query for all attestations in the aslp compact
        attestation_response = self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq('COMPACT#aslp#ATTESTATIONS')
            & Key('sk').begins_with('COMPACT#aslp#ATTESTATION#jurisprudence-confirmation'),
        )

        self.assertEqual(1, len(attestation_response['Items']))
        attestation = attestation_response['Items'][0]

        expected_attestation = {
            'pk': 'COMPACT#aslp#ATTESTATIONS',
            'sk': 'COMPACT#aslp#ATTESTATION#jurisprudence-confirmation#LOCALE#en#VERSION#1',
            'type': 'attestation',
            'attestationId': 'jurisprudence-confirmation',
            'displayName': 'Jurisprudence Confirmation',
            'description': 'For displaying the jurisprudence confirmation',
            'version': '1',
            'dateCreated': MOCK_CURRENT_TIMESTAMP,
            'dateOfUpdate': MOCK_CURRENT_TIMESTAMP,
            'text': 'You attest that you have read and understand the jurisprudence requirements for all '
            'states you are purchasing privileges for.',
            'required': True,
            'locale': 'en',
            'compact': 'aslp',
        }

        self.assertEqual(expected_attestation, attestation)

    def test_compact_configuration_uploader_raises_exception_on_invalid_attestation(self):
        """Test that invalid attestation configurations raise validation errors."""
        from handlers.compact_config_uploader import on_event

        mock_configuration = generate_mock_compact_configuration()
        # Make the attestation invalid by removing a required field
        del mock_configuration['compacts'][0]['attestations'][0]['required']

        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'compact_configuration': json.dumps(mock_configuration),
            },
        }

        with self.assertRaises(ValidationError):
            on_event(event, self.mock_context)

    def _when_testing_attestation_field_updates(self, field_to_change, new_value):
        from handlers.compact_config_uploader import on_event

        original_attestation = generate_mock_attestation()
        # First upload - should create version 1
        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'compact_configuration': json.dumps(generate_mock_compact_configuration()),
            },
        }
        on_event(event, self.mock_context)

        # Modify the attestation text and upload again
        mock_configuration = generate_mock_compact_configuration()
        mock_configuration['compacts'][0]['attestations'][0][field_to_change] = new_value

        event = {
            'RequestType': 'Update',
            'ResourceProperties': {
                'compact_configuration': json.dumps(mock_configuration),
            },
        }
        on_event(event, self.mock_context)

        # Query for all attestations in the aslp compact
        attestation_response = self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq('COMPACT#aslp#ATTESTATIONS')
            & Key('sk').begins_with('COMPACT#aslp#ATTESTATION#jurisprudence-confirmation'),
        )

        # Should have two versions
        self.assertEqual(2, len(attestation_response['Items']))

        # Sort by version to get latest
        attestations = sorted(attestation_response['Items'], key=lambda x: int(x['version']))

        # Check version 1
        self.assertEqual('1', attestations[0]['version'])
        self.assertEqual(original_attestation[field_to_change], attestations[0][field_to_change])

        # Check version 2
        self.assertEqual('2', attestations[1]['version'])
        self.assertEqual(new_value, attestations[1][field_to_change])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_TIMESTAMP))
    def test_compact_configuration_uploader_handles_attestation_versioning_when_updating_text(self):
        """Test that attestation versioning works correctly when content changes."""
        self._when_testing_attestation_field_updates('text', 'New text')

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_TIMESTAMP))
    def test_compact_configuration_uploader_handles_attestation_versioning_when_updating_description(self):
        """Test that attestation versioning works correctly when content changes."""
        self._when_testing_attestation_field_updates('description', 'New description')

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_TIMESTAMP))
    def test_compact_configuration_uploader_handles_attestation_versioning_when_updating_display_name(self):
        """Test that attestation versioning works correctly when content changes."""
        self._when_testing_attestation_field_updates('displayName', 'New Display Name')

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_TIMESTAMP))
    def test_compact_configuration_uploader_handles_attestation_versioning_when_updating_required_field(self):
        """Test that attestation versioning works correctly when content changes."""
        self._when_testing_attestation_field_updates('required', False)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_TIMESTAMP))
    def test_compact_configuration_uploader_skips_upload_when_no_changes(self):
        """Test that attestation is not uploaded when content hasn't changed."""
        from handlers.compact_config_uploader import on_event

        # First upload - should create version 1
        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'compact_configuration': json.dumps(generate_mock_compact_configuration()),
            },
        }
        on_event(event, self.mock_context)

        # Upload again with no changes
        event = {
            'RequestType': 'Update',
            'ResourceProperties': {
                'compact_configuration': json.dumps(generate_mock_compact_configuration()),
            },
        }
        on_event(event, self.mock_context)

        # Query for all attestations in the aslp compact
        attestation_response = self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq('COMPACT#aslp#ATTESTATIONS')
            & Key('sk').begins_with('COMPACT#aslp#ATTESTATION#jurisprudence-confirmation'),
        )

        # Should still only have one version
        self.assertEqual(1, len(attestation_response['Items']))
        self.assertEqual('1', attestation_response['Items'][0]['version'])
