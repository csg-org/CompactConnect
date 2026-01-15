import json
from datetime import datetime
from unittest.mock import patch

from moto import mock_aws

from .. import TstFunction

TEST_ENVIRONMENT_NAME = 'test'
MOCK_CURRENT_TIMESTAMP = '2024-11-08T23:59:59+00:00'

ASLP_COMPACT_ABBREVIATION = 'aslp'
OT_COMPACT_ABBREVIATION = 'octp'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_TIMESTAMP))
class TestCompactConfigurationUploader(TstFunction):
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
