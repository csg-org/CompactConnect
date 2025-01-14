# ruff: noqa: E501  line-too-long The lines displaying the csv file contents are long, but they are necessary for the test.
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from cc_common.exceptions import CCNotFoundException
from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'
# Test transaction data
MOCK_TRANSACTION_ID = 'mockTransactionIdPlaceholder'
MOCK_BATCH_ID = '67890'
MOCK_SUBMIT_TIME_UTC = '2024-01-01T12:00:00.000Z'
MOCK_SETTLEMENT_TIME_UTC = '2024-01-01T13:00:00.000Z'
MOCK_SETTLEMENT_TIME_LOCAL = '2024-01-01T09:00:00'

# Mock compact config values
MOCK_COMPACT_FEE = '10.50'
MOCK_JURISDICTION_FEE = '100'

# these are used to generate jurisdiction data in the DB
OHIO_JURISDICTION = {'postalAbbreviation': 'oh', 'jurisdictionName': 'ohio', 'sk': 'aslp#JURISDICTION#oh'}
KENTUCKY_JURISDICTION = {'postalAbbreviation': 'ky', 'jurisdictionName': 'kentucky', 'sk': 'aslp#JURISDICTION#ky'}
NEBRASKA_JURISDICTION = {'postalAbbreviation': 'ne', 'jurisdictionName': 'nebraska', 'sk': 'aslp#JURISDICTION#ne'}


def generate_mock_event():
    return {'compact': TEST_COMPACT}


def _generate_mock_transaction(
    jurisdictions: list[str],
    licensee_id: str,
    month_iso_string: str,
    transaction_settlement_time_utc: datetime,
    transaction_id: str = MOCK_TRANSACTION_ID,
    batch_id: str = MOCK_BATCH_ID,
) -> dict:
    """
    Generate a mock transaction with privileges for the specified jurisdictions.

    :param jurisdictions: List of jurisdiction postal codes (e.g. ['oh', 'ky'])
    :param licensee_id: The licensee ID
    :param month_iso_string: Month in YYYY-MM format
    :param transaction_settlement_time_utc: Settlement time in UTC
    :param transaction_id: Optional transaction ID
    :param batch_id: Optional batch ID
    :return: Mock transaction record
    """
    # Create line items for each jurisdiction
    line_items = [
        {
            'description': f'Compact Privilege for {jurisdiction.upper()}',
            'itemId': f'{TEST_COMPACT}-{jurisdiction}',
            'name': f'{jurisdiction.upper()} Compact Privilege',
            'quantity': '1',
            'taxable': False,
            'unitPrice': MOCK_JURISDICTION_FEE,
        }
        for jurisdiction in jurisdictions
    ]

    # Add compact fee (one per privilege)
    line_items.append(
        {
            'description': 'Compact fee applied for each privilege purchased',
            'itemId': f'{TEST_COMPACT}-compact-fee',
            'name': 'ASLP Compact Fee',
            'quantity': str(len(jurisdictions)),  # One fee per privilege
            'taxable': 'False',
            'unitPrice': MOCK_COMPACT_FEE,
        }
    )

    return {
        'batch': {
            'batchId': batch_id,
            'settlementState': 'settledSuccessfully',
            'settlementTimeLocal': '2024-01-01T09:00:00',
            'settlementTimeUTC': transaction_settlement_time_utc.isoformat(),
        },
        'compact': TEST_COMPACT,
        'licenseeId': licensee_id,
        'lineItems': line_items,
        'pk': f'COMPACT#{TEST_COMPACT}#TRANSACTIONS#MONTH#{month_iso_string}',
        'responseCode': '1',
        'settleAmount': str(
            float(MOCK_JURISDICTION_FEE) * len(jurisdictions) + float(MOCK_COMPACT_FEE) * len(jurisdictions)
        ),
        'sk': f'COMPACT#{TEST_COMPACT}#TIME#{int(transaction_settlement_time_utc.timestamp())}#BATCH#{batch_id}#'
        f'TX#{transaction_id}',
        'submitTimeUTC': MOCK_SUBMIT_TIME_UTC,
        'transactionId': transaction_id,
        'transactionStatus': 'settledSuccessfully',
        'transactionType': 'authCaptureTransaction',
        'transactionProcessor': 'authorize.net',
    }


@mock_aws
class TestGenerateTransactionReports(TstFunction):
    """Test the process_settled_transactions Lambda function."""

    def add_mock_provider_to_db(self, licensee_id, first_name, last_name) -> dict:
        def privilege_jurisdictions_to_set(obj: dict):
            if obj.get('type') == 'provider' and 'privilegeJurisdictions' in obj:
                obj['privilegeJurisdictions'] = set(obj['privilegeJurisdictions'])
            return obj

        with open('../common/tests/resources/dynamo/provider.json') as f:
            record = json.load(f, object_hook=privilege_jurisdictions_to_set, parse_float=Decimal)
            record['providerId'] = licensee_id
            record['pk'] = f'{TEST_COMPACT}#PROVIDER#{licensee_id}'
            record['givenName'] = first_name
            record['familyName'] = last_name
            self._provider_table.put_item(Item=record)

        return record

    def add_mock_transaction_to_db(
        self,
        jurisdictions: list[str],
        licensee_id: str,
        month_iso_string: str,
        transaction_settlement_time_utc: datetime,
        transaction_id: str = MOCK_TRANSACTION_ID,
        batch_id: str = MOCK_BATCH_ID,
    ) -> dict:
        """
        Add a mock transaction to the DB with privileges for the specified jurisdictions.

        :param jurisdictions: List of jurisdiction postal codes (e.g. ['oh', 'ky'])
        :param licensee_id: The licensee ID
        :param month_iso_string: Month in YYYY-MM format
        :param transaction_settlement_time_utc: Settlement time in UTC
        :param transaction_id: Optional transaction ID
        :param batch_id: Optional batch ID
        :return: The created transaction record
        """
        transaction = _generate_mock_transaction(
            jurisdictions,
            licensee_id,
            month_iso_string,
            transaction_settlement_time_utc,
            transaction_id,
            batch_id,
        )
        self._transaction_history_table.put_item(Item=transaction)
        return transaction

    def _add_compact_configuration_data(self, jurisdictions=None):
        """
        Use the canned test resources to load compact and jurisdiction information into the DB.

        If jurisdictions is None, it will default to only include Ohio.
        """
        if jurisdictions is None:
            jurisdictions = [OHIO_JURISDICTION]

        with open('../common/tests/resources/dynamo/compact.json') as f:
            record = json.load(f, parse_float=Decimal)
            self._compact_configuration_table.put_item(Item=record)

        with open('../common/tests/resources/dynamo/jurisdiction.json') as f:
            record = json.load(f, parse_float=Decimal)
            for jurisdiction in jurisdictions:
                record.update(jurisdiction)
                self._compact_configuration_table.put_item(Item=record)

    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_transaction_reports_sends_csv_with_zero_values_when_no_transactions(self, mock_lambda_client):
        """Test successful processing of settled transactions."""
        from handlers.transaction_reporting import generate_transaction_reports

        self._add_compact_configuration_data()

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        # assert that the email_notification_service_lambda_name was called with the correct payload
        call_args = mock_lambda_client.invoke.call_args_list
        compact_call = call_args[0][1]
        self.assertEqual(self.config.email_notification_service_lambda_name, compact_call['FunctionName'])
        self.assertEqual('RequestResponse', compact_call['InvocationType'])
        self.assertEqual(
            {
                'compact': TEST_COMPACT,
                'recipientType': 'COMPACT_SUMMARY_REPORT',
                'template': 'CompactTransactionReporting',
                'templateVariables': {
                    'compactFinancialSummaryReportCSV': 'Total Transactions,0\nTotal Compact Fees,$0.00\nState Fees (Ohio),$0.00\n',
                    'compactTransactionReportCSV': 'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Date,State,State Fee,Compact Fee,Transaction Id\nNo transactions for this period,,,,,,,\n',
                },
            },
            json.loads(compact_call['Payload']),
        )

        ohio_call = call_args[1][1]
        self.assertEqual(self.config.email_notification_service_lambda_name, ohio_call['FunctionName'])
        self.assertEqual('RequestResponse', ohio_call['InvocationType'])
        self.assertEqual(
            {
                'compact': TEST_COMPACT,
                'jurisdiction': 'oh',
                'recipientType': 'JURISDICTION_SUMMARY_REPORT',
                'template': 'JurisdictionTransactionReporting',
                'templateVariables': {
                    'jurisdictionTransactionReportCSV': 'First Name,Last Name,Licensee Id,Transaction Date,State Fee,State,Compact Fee,Transaction Id\nNo transactions for this period,,,,,,,\n,,,,,,,\nPrivileges Purchased,Total State Amount,,,,,,\n0,$0.00,,,,,,\n'
                },
            },
            json.loads(ohio_call['Payload']),
        )

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-02T23:59:59+00:00'))
    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_report_collects_transactions_across_two_months(self, mock_lambda_client):
        """Test successful processing of settled transactions."""
        from handlers.transaction_reporting import generate_transaction_reports

        self._add_compact_configuration_data(jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION])
        # Add a transaction that will be in the previous month
        mock_user_1 = self.add_mock_provider_to_db('12345', 'John', 'Doe')
        mock_user_2 = self.add_mock_provider_to_db('5678', 'Jane', 'Johnson')
        # in this case, there will be two transactions, one in march and the other in April
        # the lambda should pick up both transactions
        self.add_mock_transaction_to_db(
            jurisdictions=['oh'],
            licensee_id=mock_user_1['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-30T12:00:00+00:00'),
        )
        self.add_mock_transaction_to_db(
            jurisdictions=['ky'],
            licensee_id=mock_user_2['providerId'],
            month_iso_string='2025-04',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-04-01T12:00:00+00:00'),
        )

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        # assert that the email_notification_service_lambda_name was called with the correct payload
        calls_args = mock_lambda_client.invoke.call_args_list
        compact_call_payload = json.loads(calls_args[0][1]['Payload'])
        self.assertEqual(
            {
                'compact': 'aslp',
                'recipientType': 'COMPACT_SUMMARY_REPORT',
                'template': 'CompactTransactionReporting',
                'templateVariables': {
                    'compactFinancialSummaryReportCSV': 'Total Transactions,2\n'
                    'Total Compact Fees,$21.00\n'
                    'State Fees (Kentucky),$100.00\n'
                    'State Fees (Ohio),$100.00\n',
                    'compactTransactionReportCSV': f'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Date,State,State Fee,Compact Fee,Transaction Id\n'
                    f'{mock_user_1['givenName']},{mock_user_1['familyName']},{mock_user_1['providerId']},03-30-2025,OH,100,10.50,{MOCK_TRANSACTION_ID}\n'
                    f'{mock_user_2['givenName']},{mock_user_2['familyName']},{mock_user_2['providerId']},04-01-2025,KY,100,10.50,{MOCK_TRANSACTION_ID}\n',
                },
            },
            compact_call_payload,
        )

        kentucky_call_payload = json.loads(calls_args[1][1]['Payload'])
        self.assertEqual(
            {
                'compact': 'aslp',
                'jurisdiction': 'ky',
                'recipientType': 'JURISDICTION_SUMMARY_REPORT',
                'template': 'JurisdictionTransactionReporting',
                'templateVariables': {
                    'jurisdictionTransactionReportCSV': 'First Name,Last Name,Licensee Id,Transaction Date,State Fee,State,Compact Fee,Transaction Id\n'
                    f'{mock_user_2['givenName']},{mock_user_2['familyName']},{mock_user_2['providerId']},04-01-2025,100,KY,10.50,{MOCK_TRANSACTION_ID}\n'
                    ',,,,,,,\n'
                    'Privileges Purchased,Total State Amount,,,,,,\n'
                    '1,$100.00,,,,,,\n'
                },
            },
            kentucky_call_payload,
        )

        ohio_call_payload = json.loads(calls_args[2][1]['Payload'])
        self.assertEqual(
            {
                'compact': 'aslp',
                'jurisdiction': 'oh',
                'recipientType': 'JURISDICTION_SUMMARY_REPORT',
                'template': 'JurisdictionTransactionReporting',
                'templateVariables': {
                    'jurisdictionTransactionReportCSV': 'First Name,Last Name,Licensee Id,Transaction Date,State Fee,State,Compact Fee,Transaction Id\n'
                    f'{mock_user_1['givenName']},{mock_user_1['familyName']},{mock_user_1['providerId']},03-30-2025,100,OH,10.50,{MOCK_TRANSACTION_ID}\n'
                    ',,,,,,,\n'
                    'Privileges Purchased,Total State Amount,,,,,,\n'
                    '1,$100.00,,,,,,\n'
                },
            },
            ohio_call_payload,
        )

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-02T23:59:59+00:00'))
    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_report_with_multiple_privileges_in_single_transaction(self, mock_lambda_client):
        """Test processing of transactions with multiple privileges in a single transaction."""
        from handlers.transaction_reporting import generate_transaction_reports

        self._add_compact_configuration_data(
            jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION, NEBRASKA_JURISDICTION]
        )

        mock_user = self.add_mock_provider_to_db('12345', 'John', 'Doe')
        # Create a transaction with privileges for multiple jurisdictions
        self.add_mock_transaction_to_db(
            jurisdictions=['oh', 'ky', 'ne'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-30T12:00:00+00:00'),
        )

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        calls_args = mock_lambda_client.invoke.call_args_list
        compact_call_payload = json.loads(calls_args[0][1]['Payload'])

        # Verify compact summary shows correct totals
        self.assertEqual(
            'Total Transactions,1\n'
            'Total Compact Fees,$31.50\n'  # $10.50 x 3 privileges
            'State Fees (Kentucky),$100.00\n'
            'State Fees (Nebraska),$100.00\n'
            'State Fees (Ohio),$100.00\n',
            compact_call_payload['templateVariables']['compactFinancialSummaryReportCSV'],
        )

        # Verify each jurisdiction report shows the correct privilege
        for jurisdiction in ['ky', 'ne', 'oh']:
            jurisdiction_call = next(
                call for call in calls_args[1:] if json.loads(call[1]['Payload'])['jurisdiction'] == jurisdiction
            )
            jurisdiction_payload = json.loads(jurisdiction_call[1]['Payload'])
            self.assertIn(
                f'{mock_user['givenName']},{mock_user['familyName']},{mock_user['providerId']},03-30-2025,100,{jurisdiction.upper()},10.50,{MOCK_TRANSACTION_ID}',
                jurisdiction_payload['templateVariables']['jurisdictionTransactionReportCSV'],
            )

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-02T23:59:59+00:00'))
    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_report_with_large_number_of_transactions_and_providers(self, mock_lambda_client):
        """Test processing of a large number of transactions (>500) and providers (>100)."""
        from handlers.transaction_reporting import generate_transaction_reports

        self._add_compact_configuration_data(jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION])

        # Create 700 providers
        providers = []
        for i in range(700):
            provider = self.add_mock_provider_to_db(f'user_{i}', f'First{i}', f'Last{i}')
            providers.append(provider)

        # Create 600 transactions (300 per jurisdiction)
        base_time = datetime.fromisoformat('2025-03-30T12:00:00+00:00')
        for i in range(600):
            provider = providers[i]
            jurisdiction = 'oh' if i < 300 else 'ky'
            self.add_mock_transaction_to_db(
                jurisdictions=[jurisdiction],
                licensee_id=provider['providerId'],
                month_iso_string='2025-03',
                transaction_settlement_time_utc=base_time + timedelta(minutes=i),
                transaction_id=f'tx_{i}',
            )

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        calls_args = mock_lambda_client.invoke.call_args_list
        compact_call_payload = json.loads(calls_args[0][1]['Payload'])

        # Verify summary totals
        self.assertEqual(
            'Total Transactions,600\n'
            'Total Compact Fees,$6300.00\n'  # $10.50 x 600
            'State Fees (Kentucky),$30000.00\n'  # $100 x 300
            'State Fees (Ohio),$30000.00\n',  # $100 x 300
            compact_call_payload['templateVariables']['compactFinancialSummaryReportCSV'],
        )

        # Verify transaction reports
        ohio_transactions_in_report = [
            line
            for line in compact_call_payload['templateVariables']['compactTransactionReportCSV'].split('\n')
            if 'OH' in line
        ]
        kentucky_transactions_in_report = [
            line
            for line in compact_call_payload['templateVariables']['compactTransactionReportCSV'].split('\n')
            if 'KY' in line
        ]
        self.assertEqual(300, len(ohio_transactions_in_report))
        self.assertEqual(300, len(kentucky_transactions_in_report))
        # make sure all expected user ids in report
        for i in range(300):
            self.assertIn(f'user_{i}', ohio_transactions_in_report[i])
            self.assertIn(f'user_{i+300}', kentucky_transactions_in_report[i])

        # Verify jurisdiction reports
        for jurisdiction in ['oh', 'ky']:
            jurisdiction_call = next(
                call for call in calls_args[1:] if json.loads(call[1]['Payload'])['jurisdiction'] == jurisdiction
            )
            jurisdiction_payload = json.loads(jurisdiction_call[1]['Payload'])
            report_csv = jurisdiction_payload['templateVariables']['jurisdictionTransactionReportCSV']

            # 300 transactions + 5 extra lines for the header, spacing, summary headers, summary values, and line at EOF
            expected_csv_line_count = 305
            self.assertEqual(expected_csv_line_count, len(report_csv.split('\n')))
            # Verify the summary totals are correct
            self.assertIn('Privileges Purchased,Total State Amount,,,,,,', report_csv)
            self.assertIn('300,$30000.00,,,,,,', report_csv)

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-02T23:59:59+00:00'))
    def test_generate_report_raises_error_when_compact_not_found(self):
        """Test error handling when compact configuration is not found."""
        from handlers.transaction_reporting import generate_transaction_reports

        # Don't add any compact configuration data
        with self.assertRaises(CCNotFoundException) as exc_info:
            generate_transaction_reports(generate_mock_event(), self.mock_context)

        self.assertIn('Compact configuration not found', str(exc_info.exception.message))

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-02T23:59:59+00:00'))
    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_report_handles_unknown_jurisdiction(self, mock_lambda_client):
        """Test handling of transactions with jurisdictions not in configuration.

        This is unlikely to happen in practice, but we should handle it gracefully.
        """
        from handlers.transaction_reporting import generate_transaction_reports

        self._add_compact_configuration_data(jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION])

        mock_user = self.add_mock_provider_to_db('12345', 'John', 'Doe')
        # Create a transaction with a jurisdiction not in the configuration
        self.add_mock_transaction_to_db(
            jurisdictions=['oh', 'ky', 'xx'],  # 'xx' is not a configured jurisdiction
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-30T12:00:00+00:00'),
        )

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        calls_args = mock_lambda_client.invoke.call_args_list
        compact_call_payload = json.loads(calls_args[0][1]['Payload'])

        # Verify compact summary includes unknown jurisdiction
        self.assertEqual(
            'Total Transactions,1\n'
            'Total Compact Fees,$31.50\n'  # $10.50 x 3 privileges
            'State Fees (Kentucky),$100.00\n'
            'State Fees (Ohio),$100.00\n'
            'State Fees (UNKNOWN (xx)),$100.00\n',
            compact_call_payload['templateVariables']['compactFinancialSummaryReportCSV'],
        )

        # Verify we only sent reports for known jurisdictions
        jurisdiction_calls = [
            call
            for call in calls_args[1:]
            if json.loads(call[1]['Payload'])['template'] == 'JurisdictionTransactionReporting'
        ]
        self.assertEqual(2, len(jurisdiction_calls))  # Only OH and KY should get reports

        jurisdiction_report_payloads = [json.loads(call[1]['Payload']) for call in jurisdiction_calls]
        reported_jurisdictions = {payload['jurisdiction'] for payload in jurisdiction_report_payloads}
        self.assertEqual({'oh', 'ky'}, reported_jurisdictions)  # Verify only OH and KY got reports
