import json
from decimal import Decimal
from unittest.mock import call, patch

from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'

def generate_mock_event():
    return {
        'compact': TEST_COMPACT
    }

def _load_compact_configuration_data(self,
                                     jurisdictions={"postalAbbreviation": "oh", "jurisdictionName": "ohio"}):

    with open('../common/tests/resources/dynamo/compact.json') as f:
        record = json.load(f, parse_float=Decimal)
        self._compact_configuration_table.put_item(Item=record)

    with open('../common/tests/resources/dynamo/jurisdiction.json') as f:
        record = json.load(f, parse_float=Decimal)
        for jurisdiction in jurisdictions:
            record.update(jurisdiction)
            self._compact_configuration_table.put_item(Item=record)


@mock_aws
class TestGenerateTransactionReports(TstFunction):
    """Test the process_settled_transactions Lambda function."""

    def _load_compact_configuration_data(self,
                                         jurisdictions=None):
        """
        Use the canned test resources to load compact and jurisdiction information into the DB.

        If jurisdictions is None, it will default to only include Ohio.
        """
        if jurisdictions is None:
            jurisdictions = [{"postalAbbreviation": "oh", "jurisdictionName": "ohio"}]

        with open('../common/tests/resources/dynamo/compact.json') as f:
            record = json.load(f, parse_float=Decimal)
            self._compact_configuration_table.put_item(Item=record)

        with open('../common/tests/resources/dynamo/jurisdiction.json') as f:
            record = json.load(f, parse_float=Decimal)
            for jurisdiction in jurisdictions:
                record.update(jurisdiction)
                self._compact_configuration_table.put_item(Item=record)

    def _when_testing_week_with_no_transactions(
        self,
    ):
        self._load_compact_configuration_data()


    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_transaction_reports_sends_csv_with_zero_values_when_no_transactions(self, mock_lambda_client):
        """Test successful processing of settled transactions."""
        from handlers.transaction_reporting import generate_transaction_reports
        self._when_testing_week_with_no_transactions()

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        # assert that the email_notification_service_lambda_name was called with the correct payload
        expected_calls = [
            call(FunctionName=self.config.email_notification_service_lambda_name,
                 InvocationType='RequestResponse',
                 Payload=json.dumps({
                     'compact': TEST_COMPACT,
                     'template': 'CompactTransactionReporting',
                     'recipientType': 'COMPACT_SUMMARY_REPORT',
                     'templateVariables': {
                         'compactFinancialSummaryReportCSV': 'Total Transactions,0\r\nTotal Compact Fees,$0.00\r\nState Fees (Ohio),$0.00\r\n',
                         'compactTransactionReportCSV': 'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Date,State,State Fee,Compact Fee,Transaction Id\r\nNo transactions for this period,,,,,,,\r\n',
                     },
                 })),
            call(FunctionName=self.config.email_notification_service_lambda_name,
                 InvocationType='RequestResponse',
                 Payload=json.dumps({
                     'compact': TEST_COMPACT,
                     'jurisdiction': 'oh',
                     'template': 'JurisdictionTransactionReporting',
                     'recipientType': 'JURISDICTION_SUMMARY_REPORT',
                     'templateVariables': {
                         'jurisdictionTransactionReportCSV': 'First Name,Last Name,Licensee Id,Transaction Date,State Fee,State,Compact Fee,Transaction Id\r\nNo transactions for this period,,,,,,,\r\n,,,,,,,\r\nPrivileges Purchased,Total State Amount,,,,,,\r\n0,$0.00,,,,,,\r\n'
                     },
                 })),
        ]


        mock_lambda_client.invoke.assert_has_calls(expected_calls)
