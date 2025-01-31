# ruff: noqa: E501  line-too-long The lines displaying the csv file contents are long, but they are necessary for the test.
import json
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

from cc_common.exceptions import CCInternalException, CCNotFoundException
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


def generate_mock_event(reporting_cycle: str = 'weekly'):
    return {'compact': TEST_COMPACT, 'reportingCycle': reporting_cycle}


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
            # setting this as '1.0' to simulate behavior we've seen returned from authorize.net
            'quantity': '1.0',
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


def _set_default_lambda_client_behavior(mock_lambda_client):
    """Set the default behavior for the mock lambda client."""
    mock_lambda_client.invoke.return_value = {
        'StatusCode': 200,
        'LogResult': 'string',
        'Payload': '{"message": "Email message sent"}',
        'ExecutedVersion': '1',
    }


@mock_aws
class TestGenerateTransactionReports(TstFunction):
    """Test the process_settled_transactions Lambda function."""

    def _add_mock_provider_to_db(self, licensee_id, first_name, last_name) -> dict:
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

    def _add_mock_transaction_to_db(
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

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_transaction_reports_sends_csv_with_zero_values_when_no_transactions(self, mock_lambda_client):
        """Test successful processing of settled transactions."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_lambda_client_behavior(mock_lambda_client)

        self._add_compact_configuration_data()

        # Set up mocked S3 bucket

        # Calculate expected date range
        # the end time should be Friday at 10:00 PM UTC
        end_time = datetime.fromisoformat('2025-04-05T22:00:00+00:00')
        # the start time should be 7 days ago at 10:00 PM UTC
        start_time = end_time - timedelta(days=7)
        date_range = f"{start_time.strftime('%Y-%m-%d')}--{end_time.strftime('%Y-%m-%d')}"

        # Generate the reports
        generate_transaction_reports(generate_mock_event(), self.mock_context)

        # Verify email notifications
        call_args = mock_lambda_client.invoke.call_args_list

        # Check compact report email
        compact_call = call_args[0][1]
        self.assertEqual(self.config.email_notification_service_lambda_name, compact_call['FunctionName'])
        self.assertEqual('RequestResponse', compact_call['InvocationType'])

        compact_payload = json.loads(compact_call['Payload'])
        expected_compact_path = (
            f"compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/weekly/"
            f"{end_time.strftime('%Y/%m/%d')}/"
            f"{TEST_COMPACT}-{date_range}-report.zip"
        )
        self.assertEqual(
            {
                'compact': TEST_COMPACT,
                'recipientType': 'COMPACT_SUMMARY_REPORT',
                'template': 'CompactTransactionReporting',
                'templateVariables': {
                    'reportS3Path': expected_compact_path,
                    'reportingCycle': 'weekly',
                    'startDate': start_time.strftime('%Y-%m-%d'),
                    'endDate': end_time.strftime('%Y-%m-%d'),
                },
            },
            compact_payload,
        )

        # Check jurisdiction report email
        ohio_call = call_args[1][1]
        self.assertEqual(self.config.email_notification_service_lambda_name, ohio_call['FunctionName'])
        self.assertEqual('RequestResponse', ohio_call['InvocationType'])

        ohio_payload = json.loads(ohio_call['Payload'])
        expected_ohio_path = (
            f"compact/{TEST_COMPACT}/reports/jurisdiction-transactions/jurisdiction/oh/"
            f"reporting-cycle/weekly/{end_time.strftime('%Y/%m/%d')}/"
            f"oh-{date_range}-report.zip"
        )
        self.assertEqual(
            {
                'compact': TEST_COMPACT,
                'jurisdiction': 'oh',
                'recipientType': 'JURISDICTION_SUMMARY_REPORT',
                'template': 'JurisdictionTransactionReporting',
                'templateVariables': {
                    'reportS3Path': expected_ohio_path,
                    'reportingCycle': 'weekly',
                    'startDate': start_time.strftime('%Y-%m-%d'),
                    'endDate': end_time.strftime('%Y-%m-%d'),
                },
            },
            ohio_payload,
        )

        # Verify S3 stored files
        # Check compact reports
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name, Key=expected_compact_path
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Total Transactions,0\nTotal Compact Fees,$0.00\nState Fees (Ohio),$0.00\n', summary_content
                )

            # Check transaction detail
            with zip_file.open(f'{TEST_COMPACT}-transaction-detail-{date_range}.csv') as f:
                detail_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date,State,State Fee,Compact Fee,Transaction Id\n'
                    'No transactions for this period,,,,,,,\n',
                    detail_content,
                )

        # Check jurisdiction report
        ohio_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name, Key=expected_ohio_path
        )

        with ZipFile(BytesIO(ohio_zip_obj['Body'].read())) as zip_file:
            with zip_file.open(f'oh-transaction-detail-{date_range}.csv') as f:
                ohio_content = f.read().decode('utf-8')
                self.assertEqual(
                    'First Name,Last Name,Licensee Id,Transaction Settlement Date,State Fee,State,Compact Fee,Transaction Id\n'
                    'No transactions for this period,,,,,,,\n'
                    ',,,,,,,\n'
                    'Privileges Purchased,Total State Amount,,,,,,\n'
                    '0,$0.00,,,,,,\n',
                    ohio_content,
                )

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_report_collects_transactions_across_two_months(self, mock_lambda_client):
        """Test successful processing of settled transactions."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_lambda_client_behavior(mock_lambda_client)

        self._add_compact_configuration_data(jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION])

        # Add test transactions
        mock_user_1 = self._add_mock_provider_to_db('12345', 'John', 'Doe')
        mock_user_2 = self._add_mock_provider_to_db('5678', 'Jane', 'Johnson')

        # in this case, there will be two transactions, one in march and the other in April
        # the lambda should pick up both transactions
        self._add_mock_transaction_to_db(
            jurisdictions=['oh'],
            licensee_id=mock_user_1['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-30T12:00:00+00:00'),
        )
        self._add_mock_transaction_to_db(
            jurisdictions=['ky'],
            licensee_id=mock_user_2['providerId'],
            month_iso_string='2025-04',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-04-01T12:00:00+00:00'),
        )

        # Calculate expected date range
        # the end time should be Friday at 10:00 PM UTC
        end_time = datetime.fromisoformat('2025-04-05T22:00:00+00:00')
        # the start time should be 7 days ago at 10:00 PM UTC
        start_time = end_time - timedelta(days=7)
        date_range = f"{start_time.strftime('%Y-%m-%d')}--{end_time.strftime('%Y-%m-%d')}"

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        # Verify email notifications
        calls_args = mock_lambda_client.invoke.call_args_list

        # Check compact report email
        compact_call = calls_args[0][1]
        self.assertEqual(self.config.email_notification_service_lambda_name, compact_call['FunctionName'])
        self.assertEqual('RequestResponse', compact_call['InvocationType'])

        expected_compact_path = (
            f"compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/weekly/"
            f"{end_time.strftime('%Y/%m/%d')}/"
            f"{TEST_COMPACT}-{date_range}-report.zip"
        )
        compact_payload = json.loads(compact_call['Payload'])
        self.assertEqual(
            {
                'compact': TEST_COMPACT,
                'recipientType': 'COMPACT_SUMMARY_REPORT',
                'template': 'CompactTransactionReporting',
                'templateVariables': {
                    'reportS3Path': expected_compact_path,
                    'reportingCycle': 'weekly',
                    'startDate': start_time.strftime('%Y-%m-%d'),
                    'endDate': end_time.strftime('%Y-%m-%d'),
                },
            },
            compact_payload,
        )

        # Check jurisdiction report emails
        for idx, jurisdiction in enumerate(['ky', 'oh']):
            jurisdiction_call = calls_args[idx + 1][1]
            self.assertEqual(self.config.email_notification_service_lambda_name, jurisdiction_call['FunctionName'])
            self.assertEqual('RequestResponse', jurisdiction_call['InvocationType'])

            expected_jurisdiction_path = (
                f"compact/{TEST_COMPACT}/reports/jurisdiction-transactions/jurisdiction/{jurisdiction}/"
                f"reporting-cycle/weekly/{end_time.strftime('%Y/%m/%d')}/"
                f"{jurisdiction}-{date_range}-report.zip"
            )
            jurisdiction_payload = json.loads(jurisdiction_call['Payload'])
            self.assertEqual(
                {
                    'compact': TEST_COMPACT,
                    'jurisdiction': jurisdiction,
                    'recipientType': 'JURISDICTION_SUMMARY_REPORT',
                    'template': 'JurisdictionTransactionReporting',
                    'templateVariables': {
                        'reportS3Path': expected_jurisdiction_path,
                        'reportingCycle': 'weekly',
                        'startDate': start_time.strftime('%Y-%m-%d'),
                        'endDate': end_time.strftime('%Y-%m-%d'),
                    },
                },
                jurisdiction_payload,
            )

        # Verify S3 stored files
        # Check compact reports
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name, Key=expected_compact_path
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Total Transactions,2\n'
                    'Total Compact Fees,$21.00\n'
                    'State Fees (Kentucky),$100.00\n'
                    'State Fees (Ohio),$100.00\n',
                    summary_content,
                )

            # Check transaction detail
            with zip_file.open(f'{TEST_COMPACT}-transaction-detail-{date_range}.csv') as f:
                detail_content = f.read().decode('utf-8')
                self.assertEqual(
                    f'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date,State,State Fee,Compact Fee,Transaction Id\n'
                    f'{mock_user_1["givenName"]},{mock_user_1["familyName"]},{mock_user_1["providerId"]},03-30-2025,OH,100,10.50,{MOCK_TRANSACTION_ID}\n'
                    f'{mock_user_2["givenName"]},{mock_user_2["familyName"]},{mock_user_2["providerId"]},04-01-2025,KY,100,10.50,{MOCK_TRANSACTION_ID}\n',
                    detail_content,
                )

        # Check jurisdiction reports
        for jurisdiction, user in [('ky', mock_user_2), ('oh', mock_user_1)]:
            jurisdiction_zip_obj = self.config.s3_client.get_object(
                Bucket=self.config.transaction_reports_bucket_name,
                Key=(
                    f"compact/{TEST_COMPACT}/reports/jurisdiction-transactions/jurisdiction/{jurisdiction}/"
                    f"reporting-cycle/weekly/{end_time.strftime('%Y/%m/%d')}/"
                    f"{jurisdiction}-{date_range}-report.zip"
                ),
            )

            with ZipFile(BytesIO(jurisdiction_zip_obj['Body'].read())) as zip_file:
                with zip_file.open(f'{jurisdiction}-transaction-detail-{date_range}.csv') as f:
                    content = f.read().decode('utf-8')
                    transaction_date = '03-30-2025' if jurisdiction == 'oh' else '04-01-2025'
                    self.assertEqual(
                        'First Name,Last Name,Licensee Id,Transaction Settlement Date,State Fee,State,Compact Fee,Transaction Id\n'
                        f'{user["givenName"]},{user["familyName"]},{user["providerId"]},{transaction_date},100,{jurisdiction.upper()},10.50,{MOCK_TRANSACTION_ID}\n'
                        ',,,,,,,\n'
                        'Privileges Purchased,Total State Amount,,,,,,\n'
                        '1,$100.00,,,,,,\n',
                        content,
                    )

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_report_with_multiple_privileges_in_single_transaction(self, mock_lambda_client):
        """Test processing of transactions with multiple privileges in a single transaction."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_lambda_client_behavior(mock_lambda_client)

        self._add_compact_configuration_data(
            jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION, NEBRASKA_JURISDICTION]
        )

        mock_user = self._add_mock_provider_to_db('12345', 'John', 'Doe')
        # Create a transaction with privileges for multiple jurisdictions
        self._add_mock_transaction_to_db(
            jurisdictions=['oh', 'ky', 'ne'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-30T12:00:00+00:00'),
        )

        # Calculate expected date range
        # the end time should be Friday at 10:00 PM UTC
        end_time = datetime.fromisoformat('2025-04-05T22:00:00+00:00')
        # the start time should be 7 days ago at 10:00 PM UTC
        start_time = end_time - timedelta(days=7)
        date_range = f"{start_time.strftime('%Y-%m-%d')}--{end_time.strftime('%Y-%m-%d')}"

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        # Verify email notifications
        calls_args = mock_lambda_client.invoke.call_args_list

        # Check compact report email
        compact_call = calls_args[0][1]
        self.assertEqual(self.config.email_notification_service_lambda_name, compact_call['FunctionName'])
        self.assertEqual('RequestResponse', compact_call['InvocationType'])

        expected_compact_path = (
            f"compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/weekly/"
            f"{end_time.strftime('%Y/%m/%d')}/"
            f"{TEST_COMPACT}-{date_range}-report.zip"
        )
        compact_payload = json.loads(compact_call['Payload'])
        self.assertEqual(
            {
                'compact': TEST_COMPACT,
                'recipientType': 'COMPACT_SUMMARY_REPORT',
                'template': 'CompactTransactionReporting',
                'templateVariables': {
                    'reportS3Path': expected_compact_path,
                    'reportingCycle': 'weekly',
                    'startDate': start_time.strftime('%Y-%m-%d'),
                    'endDate': end_time.strftime('%Y-%m-%d'),
                },
            },
            compact_payload,
        )

        # Check jurisdiction report emails
        for idx, jurisdiction in enumerate(['ky', 'ne', 'oh']):
            jurisdiction_call = calls_args[idx + 1][1]
            self.assertEqual(self.config.email_notification_service_lambda_name, jurisdiction_call['FunctionName'])
            self.assertEqual('RequestResponse', jurisdiction_call['InvocationType'])

            expected_jurisdiction_path = (
                f"compact/{TEST_COMPACT}/reports/jurisdiction-transactions/jurisdiction/{jurisdiction}/"
                f"reporting-cycle/weekly/{end_time.strftime('%Y/%m/%d')}/"
                f"{jurisdiction}-{date_range}-report.zip"
            )
            jurisdiction_payload = json.loads(jurisdiction_call['Payload'])
            self.assertEqual(
                {
                    'compact': TEST_COMPACT,
                    'jurisdiction': jurisdiction,
                    'recipientType': 'JURISDICTION_SUMMARY_REPORT',
                    'template': 'JurisdictionTransactionReporting',
                    'templateVariables': {
                        'reportS3Path': expected_jurisdiction_path,
                        'reportingCycle': 'weekly',
                        'startDate': start_time.strftime('%Y-%m-%d'),
                        'endDate': end_time.strftime('%Y-%m-%d'),
                    },
                },
                jurisdiction_payload,
            )

        # Verify S3 stored files
        # Check compact reports
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name, Key=expected_compact_path
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Total Transactions,1\n'
                    'Total Compact Fees,$31.50\n'  # $10.50 x 3 privileges
                    'State Fees (Kentucky),$100.00\n'
                    'State Fees (Nebraska),$100.00\n'
                    'State Fees (Ohio),$100.00\n',
                    summary_content,
                )

            # Check transaction detail
            with zip_file.open(f'{TEST_COMPACT}-transaction-detail-{date_range}.csv') as f:
                detail_content = f.read().decode('utf-8')
                expected_lines = [
                    'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date,State,State Fee,Compact Fee,Transaction Id'
                ]
                for state in ['OH', 'KY', 'NE']:
                    expected_lines.append(
                        f'{mock_user["givenName"]},{mock_user["familyName"]},{mock_user["providerId"]},03-30-2025,{state},100,10.50,{MOCK_TRANSACTION_ID}'
                    )
                self.assertEqual('\n'.join(expected_lines) + '\n', detail_content)

        # Check jurisdiction reports
        for jurisdiction in ['ky', 'ne', 'oh']:
            jurisdiction_zip_obj = self.config.s3_client.get_object(
                Bucket=self.config.transaction_reports_bucket_name,
                Key=(
                    f"compact/{TEST_COMPACT}/reports/jurisdiction-transactions/jurisdiction/{jurisdiction}/"
                    f"reporting-cycle/weekly/{end_time.strftime('%Y/%m/%d')}/"
                    f"{jurisdiction}-{date_range}-report.zip"
                ),
            )

            with ZipFile(BytesIO(jurisdiction_zip_obj['Body'].read())) as zip_file:
                with zip_file.open(f'{jurisdiction}-transaction-detail-{date_range}.csv') as f:
                    content = f.read().decode('utf-8')
                    self.assertEqual(
                        'First Name,Last Name,Licensee Id,Transaction Settlement Date,State Fee,State,Compact Fee,Transaction Id\n'
                        f'{mock_user["givenName"]},{mock_user["familyName"]},{mock_user["providerId"]},03-30-2025,100,{jurisdiction.upper()},10.50,{MOCK_TRANSACTION_ID}\n'
                        ',,,,,,,\n'
                        'Privileges Purchased,Total State Amount,,,,,,\n'
                        '1,$100.00,,,,,,\n',
                        content,
                    )

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_report_with_large_number_of_transactions_and_providers(self, mock_lambda_client):
        """Test processing of a large number of transactions (>500) and providers (>100)."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_lambda_client_behavior(mock_lambda_client)

        self._add_compact_configuration_data(jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION])

        # Create 700 providers
        providers = []
        for i in range(700):
            provider = self._add_mock_provider_to_db(f'user_{i}', f'First{i}', f'Last{i}')
            providers.append(provider)

        # Create 600 transactions (300 per jurisdiction)
        base_time = datetime.fromisoformat('2025-03-30T12:00:00+00:00')
        for i in range(600):
            provider = providers[i]
            jurisdiction = 'oh' if i < 300 else 'ky'
            self._add_mock_transaction_to_db(
                jurisdictions=[jurisdiction],
                licensee_id=provider['providerId'],
                month_iso_string='2025-03',
                transaction_settlement_time_utc=base_time + timedelta(minutes=i),
                transaction_id=f'tx_{i}',
            )

        # Calculate expected date range
        # the end time should be Friday at 10:00 PM UTC
        end_time = datetime.fromisoformat('2025-04-05T22:00:00+00:00')
        # the start time should be 7 days ago at 10:00 PM UTC
        start_time = end_time - timedelta(days=7)
        date_range = f"{start_time.strftime('%Y-%m-%d')}--{end_time.strftime('%Y-%m-%d')}"

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        # Verify S3 stored files
        # Check compact reports
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name,
            Key=(
                f"compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/weekly/"
                f"{end_time.strftime('%Y/%m/%d')}/"
                f"{TEST_COMPACT}-{date_range}-report.zip"
            ),
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Total Transactions,600\n'
                    'Total Compact Fees,$6300.00\n'  # $10.50 x 600
                    'State Fees (Kentucky),$30000.00\n'  # $100 x 300
                    'State Fees (Ohio),$30000.00\n',  # $100 x 300
                    summary_content,
                )

            # Check transaction detail
            with zip_file.open(f'{TEST_COMPACT}-transaction-detail-{date_range}.csv') as f:
                detail_content = f.read().decode('utf-8').split('\n')
                # Verify header
                self.assertEqual(
                    'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date,State,State Fee,Compact Fee,Transaction Id',
                    detail_content[0],
                )

                # Count transactions by state
                oh_transactions = [line for line in detail_content if ',OH,' in line]
                ky_transactions = [line for line in detail_content if ',KY,' in line]
                self.assertEqual(300, len(oh_transactions))
                self.assertEqual(300, len(ky_transactions))

                # Verify all providers are included
                for i in range(300):
                    # Check Ohio transactions (first 300 providers)
                    self.assertIn(f'First{i},Last{i},user_{i},', oh_transactions[i])
                    self.assertIn('tx_' + str(i), oh_transactions[i])

                    # Check Kentucky transactions (next 300 providers)
                    ky_idx = i + 300
                    self.assertIn(f'First{ky_idx},Last{ky_idx},user_{ky_idx},', ky_transactions[i])
                    self.assertIn('tx_' + str(ky_idx), ky_transactions[i])

        # Check jurisdiction reports
        for jurisdiction, _start_idx in [('oh', 0), ('ky', 300)]:
            jurisdiction_zip_obj = self.config.s3_client.get_object(
                Bucket=self.config.transaction_reports_bucket_name,
                Key=(
                    f"compact/{TEST_COMPACT}/reports/jurisdiction-transactions/jurisdiction/{jurisdiction}/"
                    f"reporting-cycle/weekly/{end_time.strftime('%Y/%m/%d')}/"
                    f"{jurisdiction}-{date_range}-report.zip"
                ),
            )

            with ZipFile(BytesIO(jurisdiction_zip_obj['Body'].read())) as zip_file:
                with zip_file.open(f'{jurisdiction}-transaction-detail-{date_range}.csv') as f:
                    content = f.read().decode('utf-8').split('\n')

                    # Verify header
                    self.assertEqual(
                        'First Name,Last Name,Licensee Id,Transaction Settlement Date,State Fee,State,Compact Fee,Transaction Id',
                        content[0],
                    )

                    # 300 transactions + 5 extra lines for the header, spacing, summary headers, summary values, and line at EOF
                    expected_csv_line_count = 305
                    self.assertEqual(expected_csv_line_count, len(content))
                    # Verify summary totals
                    self.assertEqual('Privileges Purchased,Total State Amount,,,,,,', content[-3])
                    self.assertEqual('300,$30000.00,,,,,,', content[-2])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    def test_generate_report_raises_error_when_compact_not_found(self):
        """Test error handling when compact configuration is not found."""
        from handlers.transaction_reporting import generate_transaction_reports

        # Don't add any compact configuration data
        with self.assertRaises(CCNotFoundException) as exc_info:
            generate_transaction_reports(generate_mock_event(), self.mock_context)

        self.assertIn('Compact configuration not found', str(exc_info.exception.message))

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_report_raises_error_when_lambda_returns_function_error(self, mock_lambda_client):
        """Test error handling when compact configuration is not found."""
        from handlers.transaction_reporting import generate_transaction_reports

        mock_lambda_client.invoke.return_value = {'FunctionError': 'Something went wrong'}
        self._add_compact_configuration_data(jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION])

        with self.assertRaises(CCInternalException) as exc_info:
            generate_transaction_reports(generate_mock_event(), self.mock_context)

        self.assertIn('Something went wrong', str(exc_info.exception.message))

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_report_handles_unknown_jurisdiction(self, mock_lambda_client):
        """Test handling of transactions with jurisdictions not in configuration.

        This is unlikely to happen in practice, but we should handle it gracefully.
        """
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_lambda_client_behavior(mock_lambda_client)

        # Calculate expected date range
        # the end time should be Friday at 10:00 PM UTC
        end_time = datetime.fromisoformat('2025-04-05T22:00:00+00:00')
        # the start time should be 7 days ago at 10:00 PM UTC
        start_time = end_time - timedelta(days=7)
        date_range = f"{start_time.strftime('%Y-%m-%d')}--{end_time.strftime('%Y-%m-%d')}"

        self._add_compact_configuration_data(jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION])

        mock_user = self._add_mock_provider_to_db('12345', 'John', 'Doe')
        # Create a transaction with a jurisdiction not in the configuration
        self._add_mock_transaction_to_db(
            jurisdictions=['oh', 'ky', 'xx'],  # 'xx' is not a configured jurisdiction
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-30T12:00:00+00:00'),
        )

        with self.assertRaises(CCInternalException) as exc_info:
            generate_transaction_reports(generate_mock_event(), self.mock_context)

        self.assertIn('Unknown jurisdiction', str(exc_info.exception.message))

        # Verify S3 stored files
        # Check compact reports
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name,
            Key=(
                f"compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/weekly/"
                f"{end_time.strftime('%Y/%m/%d')}/"
                f"{TEST_COMPACT}-{date_range}-report.zip"
            ),
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                # Verify compact summary includes unknown jurisdiction
                self.assertEqual(
                    'Total Transactions,1\n'
                    'Total Compact Fees,$31.50\n'  # $10.50 x 3 privileges
                    'State Fees (Kentucky),$100.00\n'
                    'State Fees (Ohio),$100.00\n'
                    'State Fees (UNKNOWN (xx)),$100.00\n',
                    summary_content,
                )

        calls_args = mock_lambda_client.invoke.call_args_list

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

    # event bridge triggers the monthly report at the first day of the month 5 mins after midnight UTC
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-01T00:05:00+00:00'))
    @patch('handlers.transaction_reporting.config.lambda_client')
    def test_generate_monthly_report_includes_expected_settled_transactions_for_full_month_range(
        self, mock_lambda_client
    ):
        """Test processing monthly report with full month range for Feb 2024 (leap year)."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_lambda_client_behavior(mock_lambda_client)

        self._add_compact_configuration_data(jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION])

        mock_user = self._add_mock_provider_to_db('12345', 'John', 'Doe')
        # Create a transaction with a privilege which is settled the first day of the month at midnight UTC
        self._add_mock_transaction_to_db(
            jurisdictions=['oh'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2024-02',
            transaction_settlement_time_utc=datetime.fromisoformat('2024-02-01T00:00:00+00:00'),
        )

        # Create a transaction with a priviliege which is settled at the end of the month
        # This transaction should be included in the monthly report
        self._add_mock_transaction_to_db(
            jurisdictions=['ky'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2024-02',
            # NOTE: the moto mock does not correctly mock the behavior of the BETWEEN condition, which according to AWS is inclusive
            # so for the purposes of this test we use a time that is just before midnight UTC
            transaction_settlement_time_utc=datetime.fromisoformat('2024-02-29T23:59:58+00:00'),
        )

        # Create a transaction with a privilege which is settled the last day of the month at midnight UTC
        # This transaction should NOT be included in the monthly report
        self._add_mock_transaction_to_db(
            jurisdictions=['oh'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2024-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2024-03-01T00:00:00+00:00'),
        )

        # Calculate expected date range
        # the end time should be the last day of the month
        end_time = datetime.fromisoformat('2024-02-29T23:59:59:9999+00:00')
        # the start time should be the first day of the month
        start_time = datetime.fromisoformat('2024-02-01T00:00:00+00:00')
        date_range = f"{start_time.strftime('%Y-%m-%d')}--{end_time.strftime('%Y-%m-%d')}"

        generate_transaction_reports(generate_mock_event(reporting_cycle='monthly'), self.mock_context)

        # Verify email notifications
        calls_args = mock_lambda_client.invoke.call_args_list

        # Check compact report email
        compact_call = calls_args[0][1]
        self.assertEqual(self.config.email_notification_service_lambda_name, compact_call['FunctionName'])
        self.assertEqual('RequestResponse', compact_call['InvocationType'])

        expected_compact_path = (
            f"compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/monthly/"
            f"{end_time.strftime('%Y/%m/%d')}/"
            f"{TEST_COMPACT}-{date_range}-report.zip"
        )
        compact_payload = json.loads(compact_call['Payload'])
        self.assertEqual(
            {
                'compact': TEST_COMPACT,
                'recipientType': 'COMPACT_SUMMARY_REPORT',
                'template': 'CompactTransactionReporting',
                'templateVariables': {
                    'reportS3Path': expected_compact_path,
                    'reportingCycle': 'monthly',
                    'startDate': start_time.strftime('%Y-%m-%d'),
                    'endDate': end_time.strftime('%Y-%m-%d'),
                },
            },
            compact_payload,
        )

        # Verify S3 stored files
        # Check compact reports
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name, Key=expected_compact_path
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Total Transactions,2\n'
                    'Total Compact Fees,$21.00\n'  # $10.50 x 2 privileges
                    'State Fees (Kentucky),$100.00\n'
                    'State Fees (Ohio),$100.00\n',
                    summary_content,
                )
