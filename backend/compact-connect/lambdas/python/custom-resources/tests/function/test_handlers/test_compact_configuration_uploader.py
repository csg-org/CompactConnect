import json
from datetime import datetime
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from marshmallow import ValidationError
from moto import mock_aws

from .. import TstFunction

TEST_ENVIRONMENT_NAME = 'test'
MOCK_CURRENT_TIMESTAMP = '2024-11-08T23:59:59+00:00'

ASLP_COMPACT_ABBREVIATION = 'aslp'
OT_COMPACT_ABBREVIATION = 'octp'


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


def generate_mock_attestations():
    """Generate mock attestations data"""
    return [generate_mock_attestation()]


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_TIMESTAMP))
class TestCompactConfigurationUploader(TstFunction):
    def test_attestation_uploader_uploads_attestations(self):
        """Test that attestations are correctly uploaded to DynamoDB."""
        from handlers.compact_config_uploader import on_event

        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'active_compact_member_jurisdictions': json.dumps(
                    {ASLP_COMPACT_ABBREVIATION: ['ky', 'oh', 'ne'], OT_COMPACT_ABBREVIATION: ['ky', 'oh', 'ne']}
                ),
                'attestations': json.dumps(generate_mock_attestations()),
            },
        }

        on_event(event, self.mock_context)

        # Query for all attestations in the aslp compact
        attestation_response = self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq('COMPACT#aslp#ATTESTATIONS')
            & Key('sk').begins_with('COMPACT#aslp#LOCALE#en#ATTESTATION#jurisprudence-confirmation'),
        )

        self.assertEqual(1, len(attestation_response['Items']))
        attestation = attestation_response['Items'][0]

        expected_attestation = {
            'pk': 'COMPACT#aslp#ATTESTATIONS',
            'sk': 'COMPACT#aslp#LOCALE#en#ATTESTATION#jurisprudence-confirmation#VERSION#1',
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
            'compact': ASLP_COMPACT_ABBREVIATION,
        }

        self.assertEqual(expected_attestation, attestation)

    def test_attestation_uploader_raises_exception_on_invalid_attestation(self):
        """Test that invalid attestation configurations raise validation errors."""
        from handlers.compact_config_uploader import on_event

        mock_attestations = generate_mock_attestations()
        # Make the attestation invalid by removing a required field
        del mock_attestations[0]['required']

        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'active_compact_member_jurisdictions': json.dumps({ASLP_COMPACT_ABBREVIATION: ['ky']}),
                'attestations': json.dumps(mock_attestations),
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
                'active_compact_member_jurisdictions': json.dumps({ASLP_COMPACT_ABBREVIATION: ['ky']}),
                'attestations': json.dumps(generate_mock_attestations()),
            },
        }
        on_event(event, self.mock_context)

        # Modify the attestation text and upload again
        mock_attestations = generate_mock_attestations()
        mock_attestations[0][field_to_change] = new_value

        event = {
            'RequestType': 'Update',
            'ResourceProperties': {
                'active_compact_member_jurisdictions': json.dumps({ASLP_COMPACT_ABBREVIATION: ['ky']}),
                'attestations': json.dumps(mock_attestations),
            },
        }
        on_event(event, self.mock_context)

        # Query for all attestations in the aslp compact
        attestation_response = self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq('COMPACT#aslp#ATTESTATIONS')
            & Key('sk').begins_with('COMPACT#aslp#LOCALE#en#ATTESTATION#jurisprudence-confirmation'),
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

    def test_attestation_uploader_handles_attestation_versioning_when_updating_text(self):
        """Test that attestation versioning works correctly when content changes."""
        self._when_testing_attestation_field_updates('text', 'New text')

    def test_attestation_uploader_handles_attestation_versioning_when_updating_description(self):
        """Test that attestation versioning works correctly when content changes."""
        self._when_testing_attestation_field_updates('description', 'New description')

    def test_attestation_uploader_handles_attestation_versioning_when_updating_display_name(self):
        """Test that attestation versioning works correctly when content changes."""
        self._when_testing_attestation_field_updates('displayName', 'New Display Name')

    def test_attestation_uploader_handles_attestation_versioning_when_updating_required_field(self):
        """Test that attestation versioning works correctly when content changes."""
        self._when_testing_attestation_field_updates('required', False)

    def test_attestation_uploader_skips_upload_when_no_changes(self):
        """Test that attestation is not uploaded when content hasn't changed."""
        from handlers.compact_config_uploader import on_event

        # First upload - should create version 1
        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'active_compact_member_jurisdictions': json.dumps({ASLP_COMPACT_ABBREVIATION: ['ky']}),
                'attestations': json.dumps(generate_mock_attestations()),
            },
        }
        on_event(event, self.mock_context)

        # Upload again with no changes
        event = {
            'RequestType': 'Update',
            'ResourceProperties': {
                'active_compact_member_jurisdictions': json.dumps({ASLP_COMPACT_ABBREVIATION: ['ky']}),
                'attestations': json.dumps(generate_mock_attestations()),
            },
        }
        on_event(event, self.mock_context)

        # Query for attestations
        attestation_response = self.config.compact_configuration_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq('COMPACT#aslp#ATTESTATIONS')
            & Key('sk').begins_with('COMPACT#aslp#LOCALE#en#ATTESTATION#jurisprudence-confirmation'),
        )

        # Should still only have one version
        self.assertEqual(1, len(attestation_response['Items']))
        self.assertEqual('1', attestation_response['Items'][0]['version'])

    def test_active_member_jurisdictions_are_stored_correctly(self):
        """Test that active member jurisdictions are correctly stored in DynamoDB."""
        from handlers.compact_config_uploader import on_event

        member_jurisdictions = {
            ASLP_COMPACT_ABBREVIATION: ['ky', 'oh', 'ne'],
            OT_COMPACT_ABBREVIATION: ['ky', 'oh', 'ne', 'wi'],
        }

        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'active_compact_member_jurisdictions': json.dumps(member_jurisdictions),
                'attestations': json.dumps(generate_mock_attestations()),
            },
        }

        on_event(event, self.mock_context)

        # Check active member jurisdictions for ASLP
        active_member_response = self.config.compact_configuration_table.get_item(
            Key={
                'pk': f'COMPACT#{ASLP_COMPACT_ABBREVIATION}#ACTIVE_MEMBER_JURISDICTIONS',
                'sk': f'COMPACT#{ASLP_COMPACT_ABBREVIATION}#ACTIVE_MEMBER_JURISDICTIONS',
            }
        )

        self.assertIn('Item', active_member_response)
        self.assertIn('active_member_jurisdictions', active_member_response['Item'])

        active_members = active_member_response['Item']['active_member_jurisdictions']
        self.assertEqual(3, len(active_members))

        # Check that the expected jurisdictions are in the list with the correct structure
        for jurisdiction in active_members:
            self.assertIn('postalAbbreviation', jurisdiction)
            self.assertIn('jurisdictionName', jurisdiction)
            self.assertIn('compact', jurisdiction)
            self.assertEqual(ASLP_COMPACT_ABBREVIATION, jurisdiction['compact'])
            self.assertIn(jurisdiction['postalAbbreviation'], member_jurisdictions[ASLP_COMPACT_ABBREVIATION])

        # Check active member jurisdictions for OT
        active_member_response = self.config.compact_configuration_table.get_item(
            Key={
                'pk': f'COMPACT#{OT_COMPACT_ABBREVIATION}#ACTIVE_MEMBER_JURISDICTIONS',
                'sk': f'COMPACT#{OT_COMPACT_ABBREVIATION}#ACTIVE_MEMBER_JURISDICTIONS',
            }
        )

        self.assertIn('active_member_jurisdictions', active_member_response['Item'])

        active_members = active_member_response['Item']['active_member_jurisdictions']
        self.assertEqual(
            [
                {'compact': 'octp', 'jurisdictionName': 'Kentucky', 'postalAbbreviation': 'ky'},
                {'compact': 'octp', 'jurisdictionName': 'Ohio', 'postalAbbreviation': 'oh'},
                {'compact': 'octp', 'jurisdictionName': 'Nebraska', 'postalAbbreviation': 'ne'},
                {'compact': 'octp', 'jurisdictionName': 'Wisconsin', 'postalAbbreviation': 'wi'},
            ],
            active_members,
        )
