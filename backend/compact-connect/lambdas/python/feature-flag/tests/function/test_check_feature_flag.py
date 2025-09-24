from unittest.mock import patch

from moto import mock_aws

from . import TstFunction


@mock_aws
class TestCheckFeatureFlag(TstFunction):
    """Test suite for feature flag endpoint."""

    def _generate_test_event(self) -> dict:
        return {
            'destinationTableArn': self.mock_destination_table_arn,
            'sourceTableArn': self.mock_source_table_arn,
            'tableNameRecoveryConfirmation': self.mock_destination_table_name,
        }

    def test_lambda_returns_expected_response_body(self):
        from handlers.check_feature_flag import check_feature_flag

        # TODO - mock feature flag client and call handler to check if it returns expected response
        pass

