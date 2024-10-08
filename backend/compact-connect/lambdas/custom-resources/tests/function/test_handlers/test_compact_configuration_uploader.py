import json
from decimal import Decimal

from tests.function import TstFunction
from moto import mock_aws
from boto3.dynamodb.conditions import Key

TEST_ENVIRONMENT_NAME = "test"

def generate_single_root_compact_config(compact_name: str, active_environments: list):
    return {
        "compactName": compact_name,
        "compactCommissionFee": {
            "feeType": "FLAT_RATE",
            "feeAmount": 3.5
        },
        "compactOperationsTeamEmails": [],
        "compactAdverseActionsNotificationEmails": [],
        "compactSummaryReportNotificationEmails": [],
        "activeEnvironments": active_environments
    }


def generate_single_jurisdiction_config(jurisdiction_name: str, postal_abbreviation: str, active_environments: list):
    return {
        "jurisdictionName": jurisdiction_name,
        "postalAbbreviation": postal_abbreviation,
        "jurisdictionFee": 100,
        "militaryDiscount": {
          "active": True,
          "discountType": "FLAT_RATE",
          "discountAmount": 10
        },
        "jurisdictionOperationsTeamEmails": [],
        "jurisdictionAdverseActionsNotificationEmails": [],
        "jurisdictionSummaryReportNotificationEmails": [],
        "jurisprudenceRequirements": {
          "required": True
        },
        "activeEnvironments": active_environments
      }


def generate_mock_compact_configuration():
    return json.dumps({
  "compacts": [
      generate_single_root_compact_config("aslp", active_environments=[TEST_ENVIRONMENT_NAME]),
      generate_single_root_compact_config("octp", active_environments=[]),
  ],
  "jurisdictions": {
    "aslp": [
        generate_single_jurisdiction_config("nebraska", "ne",
                                            active_environments=[TEST_ENVIRONMENT_NAME]),
        generate_single_jurisdiction_config("ohio", "oh",
                                            active_environments=[])
    ],
    "octp": [
        generate_single_jurisdiction_config("nebraska", "ne",
                                            active_environments=['sandbox']),
        generate_single_jurisdiction_config("ohio", "oh",
                                            active_environments=['sandbox'])
    ]
  }
})

@mock_aws
class TestCompactConfigurationUploader(TstFunction):

    def test_compact_configuration_uploader_store_config_for_active_environment(self):
        from handlers.compact_config_uploader import on_event
        event = {
            "RequestType": "Create",
            "ResourceProperties": {
                "environment_name": TEST_ENVIRONMENT_NAME,
                "compact_configuration": generate_mock_compact_configuration()
            }
        }

        on_event(event, self.mock_context)

        # now query for all the aslp compact configurations
        response = self.config.provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'aslp#CONFIGURATION')
        )

        # note we don't store the activeEnvironments field in the database
        # as this is an implementation detail for the uploader
        self.assertEqual([
            {
              "compactAdverseActionsNotificationEmails": [],
              "compactCommissionFee": {
                "feeAmount": Decimal("3.5"),
                "feeType": "FLAT_RATE"
              },
              "compactName": "aslp",
              "compactOperationsTeamEmails": [],
              "compactSummaryReportNotificationEmails": [],
              "dateOfUpdate": "2024-10-08",
              "pk": "aslp#CONFIGURATION",
              "sk": "aslp#CONFIGURATION",
              "type": "compact"
            },
            {
              "compact": "aslp",
              "dateOfUpdate": "2024-10-08",
              "jurisdictionAdverseActionsNotificationEmails": [],
              "jurisdictionFee": Decimal("100"),
              "jurisdictionName": "nebraska",
              "jurisdictionOperationsTeamEmails": [],
              "jurisdictionSummaryReportNotificationEmails": [],
              "jurisprudenceRequirements": {
                "required": True
              },
              "militaryDiscount": {
                "active": True,
                "discountAmount": Decimal("10"),
                "discountType": "FLAT_RATE"
              },
              "pk": "aslp#CONFIGURATION",
              "postalAbbreviation": "ne",
              "sk": "aslp#JURISDICTION#ne",
              "type": "jurisdiction"
            }
        ], response['Items'])

    def test_compact_configuration_uploader_does_not_store_any_config_for_inactive_environment(self):
        from handlers.compact_config_uploader import on_event
        event = {
            "RequestType": "Create",
            "ResourceProperties": {
                "environment_name": "production",
                "compact_configuration": generate_mock_compact_configuration()
            }
        }

        on_event(event, self.mock_context)

        # now query for all the aslp compact configurations
        aslp_response = self.config.provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'aslp#CONFIGURATION')
        )

        octp_response = self.config.provider_table.query(
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression=Key('pk').eq(f'octp#CONFIGURATION')
        )

        items = aslp_response['Items'] + octp_response['Items']

        self.assertEqual([], items)
