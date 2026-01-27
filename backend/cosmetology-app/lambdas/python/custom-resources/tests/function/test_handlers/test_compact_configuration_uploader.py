import json
from datetime import datetime
from unittest.mock import patch

from moto import mock_aws

from .. import TstFunction

TEST_ENVIRONMENT_NAME = 'test'
MOCK_CURRENT_TIMESTAMP = '2024-11-08T23:59:59+00:00'

COSM_COMPACT_ABBREVIATION = 'cosm'


@mock_aws
@patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_TIMESTAMP))
class TestCompactConfigurationUploader(TstFunction):
    def test_active_member_jurisdictions_are_stored_correctly(self):
        """Test that active member jurisdictions are correctly stored in DynamoDB."""
        from handlers.compact_config_uploader import on_event

        member_jurisdictions = {
            COSM_COMPACT_ABBREVIATION: ['al', 'az', 'co', 'ks', 'ky', 'md', 'oh', 'tn', 'va', 'wa'],
        }

        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'active_compact_member_jurisdictions': json.dumps(member_jurisdictions),
            },
        }

        on_event(event, self.mock_context)

        # Check active member jurisdictions for COSM
        active_member_response = self.config.compact_configuration_table.get_item(
            Key={
                'pk': f'COMPACT#{COSM_COMPACT_ABBREVIATION}#ACTIVE_MEMBER_JURISDICTIONS',
                'sk': f'COMPACT#{COSM_COMPACT_ABBREVIATION}#ACTIVE_MEMBER_JURISDICTIONS',
            }
        )

        self.assertIn('Item', active_member_response)
        self.assertIn('active_member_jurisdictions', active_member_response['Item'])

        active_members = active_member_response['Item']['active_member_jurisdictions']
        self.assertEqual(10, len(active_members))

        # Check that the expected jurisdictions are in the list with the correct structure
        for jurisdiction in active_members:
            self.assertIn('postalAbbreviation', jurisdiction)
            self.assertIn('jurisdictionName', jurisdiction)
            self.assertIn('compact', jurisdiction)
            self.assertEqual(COSM_COMPACT_ABBREVIATION, jurisdiction['compact'])
            self.assertIn(jurisdiction['postalAbbreviation'], member_jurisdictions[COSM_COMPACT_ABBREVIATION])
