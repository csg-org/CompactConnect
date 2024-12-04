import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from boto3.dynamodb.conditions import Key
from moto import mock_aws

from .. import TstFunction

TEST_ENVIRONMENT_NAME = 'test'
MOCK_CURRENT_TIMESTAMP = '2024-11-08T23:59:59+00:00'


def generate_single_root_compact_config(compact_name: str, active_environments: list):
    return {
        'compactName': compact_name,
        'compactCommissionFee': {'feeType': 'FLAT_RATE', 'feeAmount': 3.5},
        'compactOperationsTeamEmails': [],
        'compactAdverseActionsNotificationEmails': [],
        'compactSummaryReportNotificationEmails': [],
        'activeEnvironments': active_environments,
    }


def generate_single_jurisdiction_config(jurisdiction_name: str, postal_abbreviation: str, active_environments: list):
    return {
        'jurisdictionName': jurisdiction_name,
        'postalAbbreviation': postal_abbreviation,
        'jurisdictionFee': 100,
        'militaryDiscount': {'active': True, 'discountType': 'FLAT_RATE', 'discountAmount': 10},
        'jurisdictionOperationsTeamEmails': [],
        'jurisdictionAdverseActionsNotificationEmails': [],
        'jurisdictionSummaryReportNotificationEmails': [],
        'jurisprudenceRequirements': {'required': True},
        'activeEnvironments': active_environments,
    }


def generate_mock_compact_configuration():
    return json.dumps(
        {
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
        },
    )


@mock_aws
class TestCompactConfigurationUploader(TstFunction):
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat(MOCK_CURRENT_TIMESTAMP))
    def test_compact_configuration_uploader_store_all_config(self):
        from handlers.compact_config_uploader import on_event

        event = {
            'RequestType': 'Create',
            'ResourceProperties': {
                'compact_configuration': generate_mock_compact_configuration(),
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
                    'jurisdictionOperationsTeamEmails': [],
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
                    'jurisdictionOperationsTeamEmails': [],
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
                    'jurisdictionOperationsTeamEmails': [],
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
                    'jurisdictionOperationsTeamEmails': [],
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
