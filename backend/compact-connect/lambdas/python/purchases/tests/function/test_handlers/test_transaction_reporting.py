# ruff: noqa: E501  line-too-long The lines displaying the csv file contents are long, but they are necessary for the test.
import json
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import call, patch
from zipfile import ZipFile

from cc_common.exceptions import CCInternalException, CCNotFoundException
from moto import mock_aws

from .. import TstFunction

TEST_COMPACT = 'aslp'
TEST_AUD_LICENSE_TYPE_ABBR = 'aud'
# Test transaction data
MOCK_TRANSACTION_ID = 'mockTransactionIdPlaceholder'
MOCK_BATCH_ID = '67890'
MOCK_SUBMIT_TIME_UTC = '2024-01-01T12:00:00.000Z'
MOCK_SETTLEMENT_TIME_UTC = '2024-01-01T13:00:00.000Z'
MOCK_SETTLEMENT_TIME_LOCAL = '2024-01-01T09:00:00'
TEST_TRANSACTION_SUCCESSFUL_STATUS = 'settledSuccessfully'
TEST_TRANSACTION_ERROR_STATUS = 'settlementError'
# Mock compact config values
MOCK_COMPACT_FEE = '10.50'
MOCK_JURISDICTION_FEE = '100'
MOCK_TRANSACTION_FEE = '3.00'

# these are used to generate jurisdiction data in the DB
OHIO_JURISDICTION = {'postalAbbreviation': 'oh', 'jurisdictionName': 'ohio', 'sk': 'aslp#JURISDICTION#oh'}
KENTUCKY_JURISDICTION = {'postalAbbreviation': 'ky', 'jurisdictionName': 'kentucky', 'sk': 'aslp#JURISDICTION#ky'}
NEBRASKA_JURISDICTION = {'postalAbbreviation': 'ne', 'jurisdictionName': 'nebraska', 'sk': 'aslp#JURISDICTION#ne'}

# mock privilege ids
MOCK_OHIO_PRIVILEGE_ID = 'mock-privilege-id-oh'
MOCK_KENTUCKY_PRIVILEGE_ID = 'mock-privilege-id-ky'
MOCK_NEBRASKA_PRIVILEGE_ID = 'mock-privilege-id-ne'

MOCK_PRIVILEGE_ID_MAPPING = {
    'oh': MOCK_OHIO_PRIVILEGE_ID,
    'ky': MOCK_KENTUCKY_PRIVILEGE_ID,
    'ne': MOCK_NEBRASKA_PRIVILEGE_ID,
    'xx': 'UNKNOWN',
}


def generate_mock_event(reporting_cycle: str = 'weekly'):
    return {'compact': TEST_COMPACT, 'reportingCycle': reporting_cycle}


def _generate_mock_transaction(
    jurisdictions: list[str],
    licensee_id: str,
    month_iso_string: str,
    transaction_settlement_time_utc: datetime,
    transaction_id: str = MOCK_TRANSACTION_ID,
    batch_id: str = MOCK_BATCH_ID,
    include_licensee_transaction_fees: bool = False,
    include_unknown_line_item_fees: bool = False,
    transaction_status: str = TEST_TRANSACTION_SUCCESSFUL_STATUS,
) -> dict:
    """
    Generate a mock transaction with privileges for the specified jurisdictions.

    :param jurisdictions: List of jurisdiction postal codes (e.g. ['oh', 'ky'])
    :param licensee_id: The licensee ID
    :param month_iso_string: Month in YYYY-MM format
    :param transaction_settlement_time_utc: Settlement time in UTC
    :param transaction_id: Optional transaction ID
    :param batch_id: Optional batch ID
    :param include_licensee_transaction_fees: Whether to include licensee transaction fees
    :param include_unknown_line_item_fees: Whether to include unknown line item fees
    :return: Mock transaction record
    """
    # Create line items for each jurisdiction
    line_items = [
        {
            'description': f'Compact Privilege for {jurisdiction.upper()}',
            'itemId': f'priv:{TEST_COMPACT}-{jurisdiction}-{TEST_AUD_LICENSE_TYPE_ABBR}',
            'name': f'{jurisdiction.upper()} Compact Privilege',
            # setting this as '1.0' to simulate behavior we've seen returned from authorize.net
            'quantity': '1.0',
            'taxable': False,
            'unitPrice': MOCK_JURISDICTION_FEE,
            'privilegeId': MOCK_PRIVILEGE_ID_MAPPING[jurisdiction],
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

    # adding licensee transaction fees if the flag is set
    if include_licensee_transaction_fees:
        line_items.append(
            {
                'description': 'Credit card transaction fee',
                'itemId': 'credit-card-transaction-fee',
                'name': 'Credit Card Transaction Fee',
                'quantity': str(len(jurisdictions)),
                'taxable': 'False',
                'unitPrice': MOCK_TRANSACTION_FEE,
            }
        )

    # adding unknown line item fees if the flag is set
    if include_unknown_line_item_fees:
        line_items.append(
            {
                'description': 'Unknown line item fee',
                'itemId': 'unknown-line-item-fee',
                'name': 'Unknown Line Item Fee',
                'quantity': '1.0',
                'taxable': 'False',
                'unitPrice': '2.00',
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
        'transactionStatus': transaction_status,
        'transactionType': 'authCaptureTransaction',
        'transactionProcessor': 'authorize.net',
    }


def _set_default_email_service_client_behavior(mock_email_service_client):
    """Set the default behavior for the mock email service client."""
    mock_email_service_client.send_compact_transaction_report_email.return_value = {
        'StatusCode': 200,
        'LogResult': 'string',
        'Payload': '{"message": "Email message sent"}',
        'ExecutedVersion': '1',
    }

    mock_email_service_client.send_jurisdiction_transaction_report_email.return_value = {
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
        include_licensee_transaction_fees: bool = False,
        include_unknown_line_item_fees: bool = False,
        transaction_status: str = TEST_TRANSACTION_SUCCESSFUL_STATUS,
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
            include_licensee_transaction_fees,
            include_unknown_line_item_fees,
            transaction_status,
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

    def _validate_compact_email_notification(self, mock_email_service_client, reporting_cycle, start_time, end_time):
        date_range = f'{start_time.strftime("%Y-%m-%d")}--{end_time.strftime("%Y-%m-%d")}'
        # Check compact report email notification
        expected_compact_path = (
            f'compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/{reporting_cycle}/'
            f'{end_time.strftime("%Y/%m/%d")}/'
            f'{TEST_COMPACT}-{date_range}-report.zip'
        )
        mock_email_service_client.send_compact_transaction_report_email.assert_called_once_with(
            compact=TEST_COMPACT,
            report_s3_path=expected_compact_path,
            reporting_cycle=reporting_cycle,
            start_date=start_time,
            end_date=end_time,
        )

        return expected_compact_path

    def _validate_jurisdiction_email_notification(
        self, mock_email_service_client, jurisdiction, reporting_cycle, start_time, end_time
    ):
        date_range = f'{start_time.strftime("%Y-%m-%d")}--{end_time.strftime("%Y-%m-%d")}'

        expected_jurisdiction_path = (
            f'compact/{TEST_COMPACT}/reports/jurisdiction-transactions/jurisdiction/{jurisdiction}/'
            f'reporting-cycle/{reporting_cycle}/{end_time.strftime("%Y/%m/%d")}/'
            f'{jurisdiction}-{date_range}-report.zip'
        )
        email_service_client_calls = mock_email_service_client.send_jurisdiction_transaction_report_email.call_args_list
        expected_call = call(
            compact=TEST_COMPACT,
            jurisdiction=jurisdiction,
            report_s3_path=expected_jurisdiction_path,
            reporting_cycle=reporting_cycle,
            start_date=start_time,
            end_date=end_time,
        )
        self.assertIn(expected_call, email_service_client_calls)

        return expected_jurisdiction_path

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.email_service_client')
    def test_generate_transaction_reports_sends_csv_with_zero_values_when_no_transactions(
        self, mock_email_service_client
    ):
        """Test successful processing of settled transactions."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_email_service_client_behavior(mock_email_service_client)

        self._add_compact_configuration_data([OHIO_JURISDICTION])

        # Calculate expected date range
        # the end time should be Friday at 10:00 PM UTC
        end_time = datetime.fromisoformat('2025-04-05T22:00:00+00:00')
        # the start time should be 7 days ago at 10:00 PM UTC
        start_time = end_time - timedelta(days=7)
        date_range = f'{start_time.strftime("%Y-%m-%d")}--{end_time.strftime("%Y-%m-%d")}'

        # Generate the reports
        generate_transaction_reports(generate_mock_event(), self.mock_context)

        expected_compact_path = self._validate_compact_email_notification(
            mock_email_service_client=mock_email_service_client,
            reporting_cycle='weekly',
            start_time=start_time,
            end_time=end_time,
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
                    'Privileges purchased for Ohio,0\n'
                    'State Fees (Ohio),$0.00\n'
                    'Administrative Fees,$0.00\n'
                    ',\n'
                    'Total Processed Amount,$0.00\n',
                    summary_content,
                )

            # Check transaction detail
            with zip_file.open(f'{TEST_COMPACT}-transaction-detail-{date_range}.csv') as f:
                detail_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date UTC,State,State Fee,Administrative Fee,Collected Transaction Fee,Transaction Id,Privilege Id,Transaction Status\n'
                    'No transactions for this period,,,,,,,,,,\n',
                    detail_content,
                )

        # Check jurisdiction report email
        expected_ohio_path = self._validate_jurisdiction_email_notification(
            mock_email_service_client=mock_email_service_client,
            jurisdiction='oh',
            reporting_cycle='weekly',
            start_time=start_time,
            end_time=end_time,
        )

        # Check jurisdiction report
        ohio_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name, Key=expected_ohio_path
        )

        with ZipFile(BytesIO(ohio_zip_obj['Body'].read())) as zip_file:
            with zip_file.open(f'oh-transaction-detail-{date_range}.csv') as f:
                ohio_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date UTC,State Fee,State,Transaction Id,Privilege Id,Transaction Status\n'
                    'No transactions for this period,,,,,,,,\n'
                    ',,,,,,,,\n'
                    'Privileges Purchased,Total State Amount,,,,,,,\n'
                    '0,$0.00,,,,,,,\n',
                    ohio_content,
                )

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.email_service_client')
    def test_generate_report_collects_transactions_across_two_months(self, mock_email_service_client):
        """Test successful processing of settled transactions."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_email_service_client_behavior(mock_email_service_client)

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
        date_range = f'{start_time.strftime("%Y-%m-%d")}--{end_time.strftime("%Y-%m-%d")}'

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        # Verify email notifications using the new pattern
        expected_compact_path = self._validate_compact_email_notification(
            mock_email_service_client=mock_email_service_client,
            reporting_cycle='weekly',
            start_time=start_time,
            end_time=end_time,
        )

        # Check jurisdiction report emails
        for jurisdiction in ['ky', 'oh']:
            self._validate_jurisdiction_email_notification(
                mock_email_service_client=mock_email_service_client,
                jurisdiction=jurisdiction,
                reporting_cycle='weekly',
                start_time=start_time,
                end_time=end_time,
            )

        # Verify S3 stored files for compact report
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name, Key=expected_compact_path
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Privileges purchased for Kentucky,1\n'
                    'State Fees (Kentucky),$100.00\n'
                    'Privileges purchased for Ohio,1\n'
                    'State Fees (Ohio),$100.00\n'
                    'Administrative Fees,$21.00\n'  # $10.50 x 2 privileges
                    ',\n'
                    'Total Processed Amount,$221.00\n',
                    summary_content,
                )

            # Check transaction detail
            with zip_file.open(f'{TEST_COMPACT}-transaction-detail-{date_range}.csv') as f:
                detail_content = f.read().decode('utf-8')
                self.assertEqual(
                    f'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date UTC,State,State Fee,Administrative Fee,Collected Transaction Fee,Transaction Id,Privilege Id,Transaction Status\n'
                    f'{mock_user_1["givenName"]},{mock_user_1["familyName"]},{mock_user_1["providerId"]},03-30-2025,OH,100,10.50,0,{MOCK_TRANSACTION_ID},{MOCK_OHIO_PRIVILEGE_ID},{TEST_TRANSACTION_SUCCESSFUL_STATUS}\n'
                    f'{mock_user_2["givenName"]},{mock_user_2["familyName"]},{mock_user_2["providerId"]},04-01-2025,KY,100,10.50,0,{MOCK_TRANSACTION_ID},{MOCK_KENTUCKY_PRIVILEGE_ID},{TEST_TRANSACTION_SUCCESSFUL_STATUS}\n',
                    detail_content,
                )

        # Check jurisdiction reports
        for jurisdiction, user in [('ky', mock_user_2), ('oh', mock_user_1)]:
            jurisdiction_zip_obj = self.config.s3_client.get_object(
                Bucket=self.config.transaction_reports_bucket_name,
                Key=(
                    f'compact/{TEST_COMPACT}/reports/jurisdiction-transactions/jurisdiction/{jurisdiction}/'
                    f'reporting-cycle/weekly/{end_time.strftime("%Y/%m/%d")}/'
                    f'{jurisdiction}-{date_range}-report.zip'
                ),
            )

            with ZipFile(BytesIO(jurisdiction_zip_obj['Body'].read())) as zip_file:
                with zip_file.open(f'{jurisdiction}-transaction-detail-{date_range}.csv') as f:
                    content = f.read().decode('utf-8')
                    transaction_date = '03-30-2025' if jurisdiction == 'oh' else '04-01-2025'
                    self.assertEqual(
                        'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date UTC,State Fee,State,Transaction Id,Privilege Id,Transaction Status\n'
                        f'{user["givenName"]},{user["familyName"]},{user["providerId"]},{transaction_date},100,{jurisdiction.upper()},{MOCK_TRANSACTION_ID},{MOCK_PRIVILEGE_ID_MAPPING[jurisdiction]},{TEST_TRANSACTION_SUCCESSFUL_STATUS}\n'
                        ',,,,,,,,\n'
                        'Privileges Purchased,Total State Amount,,,,,,,\n'
                        '1,$100.00,,,,,,,\n',
                        content,
                    )

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.email_service_client')
    def test_generate_report_with_multiple_privileges_in_single_transaction(self, mock_email_service_client):
        """Test processing of transactions with multiple privileges in a single transaction."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_email_service_client_behavior(mock_email_service_client)

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
        date_range = f'{start_time.strftime("%Y-%m-%d")}--{end_time.strftime("%Y-%m-%d")}'

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        # Verify compact email notification
        expected_compact_path = self._validate_compact_email_notification(
            mock_email_service_client=mock_email_service_client,
            reporting_cycle='weekly',
            start_time=start_time,
            end_time=end_time,
        )

        # Verify S3 stored files for compact report
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name, Key=expected_compact_path
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Privileges purchased for Kentucky,1\n'
                    'State Fees (Kentucky),$100.00\n'
                    'Privileges purchased for Nebraska,1\n'
                    'State Fees (Nebraska),$100.00\n'
                    'Privileges purchased for Ohio,1\n'
                    'State Fees (Ohio),$100.00\n'
                    'Administrative Fees,$31.50\n'  # $10.50 x 3 privileges
                    ',\n'
                    'Total Processed Amount,$331.50\n',
                    summary_content,
                )

            # Check transaction detail
            with zip_file.open(f'{TEST_COMPACT}-transaction-detail-{date_range}.csv') as f:
                detail_content = f.read().decode('utf-8')
                expected_lines = [
                    'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date UTC,State,State Fee,Administrative Fee,Collected Transaction Fee,Transaction Id,Privilege Id,Transaction Status'
                ]
                for state in ['OH', 'KY', 'NE']:
                    expected_lines.append(
                        f'{mock_user["givenName"]},{mock_user["familyName"]},{mock_user["providerId"]},03-30-2025,{state},100,10.50,0,{MOCK_TRANSACTION_ID},{MOCK_PRIVILEGE_ID_MAPPING[state.lower()]},{TEST_TRANSACTION_SUCCESSFUL_STATUS}'
                    )
                self.assertEqual('\n'.join(expected_lines) + '\n', detail_content)

        # Check jurisdiction reports
        for jurisdiction in ['ky', 'ne', 'oh']:
            expected_jurisdiction_path = self._validate_jurisdiction_email_notification(
                mock_email_service_client=mock_email_service_client,
                jurisdiction=jurisdiction,
                reporting_cycle='weekly',
                start_time=start_time,
                end_time=end_time,
            )
            jurisdiction_zip_obj = self.config.s3_client.get_object(
                Bucket=self.config.transaction_reports_bucket_name,
                Key=expected_jurisdiction_path,
            )

            with ZipFile(BytesIO(jurisdiction_zip_obj['Body'].read())) as zip_file:
                with zip_file.open(f'{jurisdiction}-transaction-detail-{date_range}.csv') as f:
                    content = f.read().decode('utf-8')
                    self.assertEqual(
                        'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date UTC,State Fee,State,Transaction Id,Privilege Id,Transaction Status\n'
                        f'{mock_user["givenName"]},{mock_user["familyName"]},{mock_user["providerId"]},03-30-2025,100,{jurisdiction.upper()},{MOCK_TRANSACTION_ID},{MOCK_PRIVILEGE_ID_MAPPING[jurisdiction]},{TEST_TRANSACTION_SUCCESSFUL_STATUS}\n'
                        ',,,,,,,,\n'
                        'Privileges Purchased,Total State Amount,,,,,,,\n'
                        '1,$100.00,,,,,,,\n',
                        content,
                    )

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.email_service_client')
    def test_generate_report_with_large_number_of_transactions_and_providers(self, mock_email_service_client):
        """Test processing of a large number of transactions (>500) and providers (>100)."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_email_service_client_behavior(mock_email_service_client)

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
        date_range = f'{start_time.strftime("%Y-%m-%d")}--{end_time.strftime("%Y-%m-%d")}'

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        # Verify S3 stored files
        # Check compact reports
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name,
            Key=(
                f'compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/weekly/'
                f'{end_time.strftime("%Y/%m/%d")}/'
                f'{TEST_COMPACT}-{date_range}-report.zip'
            ),
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Privileges purchased for Kentucky,300\n'
                    'State Fees (Kentucky),$30000.00\n'
                    'Privileges purchased for Ohio,300\n'
                    'State Fees (Ohio),$30000.00\n'
                    'Administrative Fees,$6300.00\n'
                    ',\n'
                    'Total Processed Amount,$66300.00\n',
                    summary_content,
                )

            # Check transaction detail
            with zip_file.open(f'{TEST_COMPACT}-transaction-detail-{date_range}.csv') as f:
                detail_content = f.read().decode('utf-8').split('\n')
                # Verify header
                self.assertEqual(
                    'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date UTC,State,State Fee,Administrative Fee,Collected Transaction Fee,Transaction Id,Privilege Id,Transaction Status',
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
                    f'compact/{TEST_COMPACT}/reports/jurisdiction-transactions/jurisdiction/{jurisdiction}/'
                    f'reporting-cycle/weekly/{end_time.strftime("%Y/%m/%d")}/'
                    f'{jurisdiction}-{date_range}-report.zip'
                ),
            )

            with ZipFile(BytesIO(jurisdiction_zip_obj['Body'].read())) as zip_file:
                with zip_file.open(f'{jurisdiction}-transaction-detail-{date_range}.csv') as f:
                    content = f.read().decode('utf-8').split('\n')

                    # Verify header
                    self.assertEqual(
                        'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date UTC,State Fee,State,Transaction Id,Privilege Id,Transaction Status',
                        content[0],
                    )

                    # 300 transactions + 5 extra lines for the header, spacing, summary headers, summary values, and line at EOF
                    expected_csv_line_count = 305
                    self.assertEqual(expected_csv_line_count, len(content))
                    # Verify summary totals
                    self.assertEqual('Privileges Purchased,Total State Amount,,,,,,,', content[-3])
                    self.assertEqual('300,$30000.00,,,,,,,', content[-2])

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    def test_generate_report_raises_error_when_compact_not_found(self):
        """Test error handling when compact configuration is not found."""
        from handlers.transaction_reporting import generate_transaction_reports

        # Don't add any compact configuration data
        with self.assertRaises(CCNotFoundException) as exc_info:
            generate_transaction_reports(generate_mock_event(), self.mock_context)

        self.assertIn('Compact configuration not found', str(exc_info.exception.message))

    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.email_service_client')
    def test_generate_report_raises_error_when_email_service_client_raises_error(self, mock_email_service_client):
        """Test error handling when email service client raises an exception."""
        from handlers.transaction_reporting import generate_transaction_reports

        # Set up the mock to raise an exception
        mock_email_service_client.send_compact_transaction_report_email.side_effect = CCInternalException(
            'Something went wrong'
        )

        self._add_compact_configuration_data(jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION])

        with self.assertRaises(CCInternalException) as exc_info:
            generate_transaction_reports(generate_mock_event(), self.mock_context)

        self.assertIn('Something went wrong', str(exc_info.exception.message))

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.email_service_client')
    def test_generate_report_handles_unknown_jurisdiction(self, mock_email_service_client):
        """Test handling of transactions with jurisdictions not in configuration.

        This is unlikely to happen in practice, but we should handle it gracefully.
        """
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_email_service_client_behavior(mock_email_service_client)

        # Calculate expected date range
        # the end time should be Friday at 10:00 PM UTC
        end_time = datetime.fromisoformat('2025-04-05T22:00:00+00:00')
        # the start time should be 7 days ago at 10:00 PM UTC
        start_time = end_time - timedelta(days=7)
        date_range = f'{start_time.strftime("%Y-%m-%d")}--{end_time.strftime("%Y-%m-%d")}'

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
                f'compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/weekly/'
                f'{end_time.strftime("%Y/%m/%d")}/'
                f'{TEST_COMPACT}-{date_range}-report.zip'
            ),
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                # Verify compact summary includes unknown jurisdiction
                self.assertEqual(
                    'Privileges purchased for Kentucky,1\n'
                    'State Fees (Kentucky),$100.00\n'
                    'Privileges purchased for Ohio,1\n'
                    'State Fees (Ohio),$100.00\n'
                    'Privileges purchased for UNKNOWN (xx),1\n'
                    'State Fees (UNKNOWN (xx)),$100.00\n'
                    'Administrative Fees,$31.50\n'  # $10.50 x 3 privileges
                    ',\n'
                    'Total Processed Amount,$331.50\n',
                    summary_content,
                )

        # Verify we only sent reports for known jurisdictions
        self.assertEqual(1, mock_email_service_client.send_compact_transaction_report_email.call_count)

        # Check that we called send_jurisdiction_transaction_report_email for each known jurisdiction
        self.assertEqual(2, mock_email_service_client.send_jurisdiction_transaction_report_email.call_count)

        # Get the jurisdiction arguments from all calls
        jurisdiction_args = set(
            [
                call[1]['jurisdiction']
                for call in mock_email_service_client.send_jurisdiction_transaction_report_email.call_args_list
            ]
        )

        # Verify only OH and KY got reports
        self.assertEqual({'oh', 'ky'}, jurisdiction_args)

    # event bridge triggers the monthly report at the first day of the month 5 mins after midnight UTC
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2024-03-01T00:05:00+00:00'))
    @patch('handlers.transaction_reporting.config.email_service_client')
    def test_generate_monthly_report_includes_expected_settled_transactions_for_full_month_range(
        self, mock_email_service_client
    ):
        """Test processing monthly report with full month range for Feb 2024 (leap year)."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_email_service_client_behavior(mock_email_service_client)

        self._add_compact_configuration_data(
            jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION, NEBRASKA_JURISDICTION]
        )

        mock_user = self._add_mock_provider_to_db('12345', 'John', 'Doe')
        # Create a transaction with a privilege which is settled the first day of the month at midnight UTC
        # This transaction should be included in the monthly report
        self._add_mock_transaction_to_db(
            jurisdictions=['oh'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2024-02',
            transaction_settlement_time_utc=datetime.fromisoformat('2024-02-01T00:00:00+00:00'),
        )

        # Create a transaction with a privilege which is settled at the very end of the month
        # This transaction should be included in the monthly report
        self._add_mock_transaction_to_db(
            jurisdictions=['ky'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2024-02',
            transaction_settlement_time_utc=datetime.fromisoformat('2024-02-29T23:59:59+00:00'),
        )

        # Create a transaction with a privilege which is settled at the very end of the previous month
        # This transaction should NOT be included in the monthly report
        self._add_mock_transaction_to_db(
            jurisdictions=['ne'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2024-01',
            transaction_settlement_time_utc=datetime.fromisoformat('2024-01-31T23:59:59+00:00'),
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
        # the display end time should be the last day of the month
        display_end_time = datetime.fromisoformat('2024-02-29T00:00:00+00:00')
        # the start time should be the first day of the month
        display_start_time = datetime.fromisoformat('2024-02-01T00:00:00+00:00')
        date_range = f'{display_start_time.strftime("%Y-%m-%d")}--{display_end_time.strftime("%Y-%m-%d")}'

        generate_transaction_reports(generate_mock_event(reporting_cycle='monthly'), self.mock_context)

        # Verify email notifications using the new pattern
        expected_compact_path = self._validate_compact_email_notification(
            mock_email_service_client=mock_email_service_client,
            reporting_cycle='monthly',
            start_time=display_start_time,
            end_time=display_end_time,
        )

        # Verify S3 stored files for compact report
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name, Key=expected_compact_path
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Privileges purchased for Kentucky,1\n'
                    'State Fees (Kentucky),$100.00\n'
                    'Privileges purchased for Nebraska,0\n'
                    'State Fees (Nebraska),$0.00\n'
                    'Privileges purchased for Ohio,1\n'
                    'State Fees (Ohio),$100.00\n'
                    'Administrative Fees,$21.00\n'  # $10.50 x 2 privileges
                    ',\n'
                    'Total Processed Amount,$221.00\n',
                    summary_content,
                )

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-03-08T22:00:01+00:00'))
    @patch('handlers.transaction_reporting.config.email_service_client')
    def test_generate_weekly_report_includes_expected_settled_transactions_for_full_week_range(
        self, mock_email_service_client
    ):
        """Test processing weekly report with full week range for Mar 2024."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_email_service_client_behavior(mock_email_service_client)

        self._add_compact_configuration_data(
            jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION, NEBRASKA_JURISDICTION]
        )

        mock_user = self._add_mock_provider_to_db('12345', 'John', 'Doe')

        # Create a transaction with a privilege which is settled the first day of the week a second after 10:00 PM UTC
        self._add_mock_transaction_to_db(
            jurisdictions=['oh'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-01T22:00:01+00:00'),
        )

        # Create a transaction with a privilege which is settled the first day of the week right at 10:00 PM UTC
        # This transaction should be included in the weekly report
        self._add_mock_transaction_to_db(
            jurisdictions=['ky'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-01T22:00:00+00:00'),
        )

        # Create a transaction with a privilege which is settled the last day of the week right at 9:59:59 PM UTC
        # This transaction should be included in the weekly report
        self._add_mock_transaction_to_db(
            jurisdictions=['ne'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-08T21:59:59+00:00'),
        )

        # Create a transaction with a privilege which is settled at the end of the week at 10:00 PM UTC
        # This transaction should NOT be included in the weekly report
        self._add_mock_transaction_to_db(
            jurisdictions=['ky'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-08T22:00:00+00:00'),
        )

        # Create a transaction with a privilege which is settled the last day of the week a second after 10:00 PM UTC
        # This transaction should NOT be included in the weekly report
        self._add_mock_transaction_to_db(
            jurisdictions=['ne'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-08T22:00:01+00:00'),
        )

        # Calculate expected date range
        # the end time should be Friday at 10:00 PM UTC
        end_time = datetime.fromisoformat('2025-03-08T22:00:01+00:00')
        # the start time should be 7 days ago at 10:00 PM UTC
        start_time = end_time - timedelta(days=7)
        date_range = f'{start_time.strftime("%Y-%m-%d")}--{end_time.strftime("%Y-%m-%d")}'

        generate_transaction_reports(generate_mock_event(reporting_cycle='weekly'), self.mock_context)

        # Verify email notifications using the new pattern
        expected_compact_path = self._validate_compact_email_notification(
            mock_email_service_client=mock_email_service_client,
            reporting_cycle='weekly',
            start_time=start_time,
            end_time=end_time,
        )

        # Verify S3 stored files for compact report
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name, Key=expected_compact_path
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Privileges purchased for Kentucky,1\n'
                    'State Fees (Kentucky),$100.00\n'
                    'Privileges purchased for Nebraska,1\n'
                    'State Fees (Nebraska),$100.00\n'
                    'Privileges purchased for Ohio,1\n'
                    'State Fees (Ohio),$100.00\n'
                    'Administrative Fees,$31.50\n'  # $10.50 x 3 privileges
                    ',\n'
                    'Total Processed Amount,$331.50\n',
                    summary_content,
                )

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.email_service_client')
    def test_generate_report_with_licensee_transaction_fees(self, mock_email_service_client):
        """Test processing of transactions with multiple privileges in a single transaction."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_email_service_client_behavior(mock_email_service_client)

        self._add_compact_configuration_data(
            jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION, NEBRASKA_JURISDICTION]
        )

        mock_user = self._add_mock_provider_to_db('12345', 'John', 'Doe')
        # Create a transaction in which the licensee is charged transaction fees
        self._add_mock_transaction_to_db(
            jurisdictions=['oh', 'ky', 'ne'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-30T12:00:00+00:00'),
            include_licensee_transaction_fees=True,
        )

        # Calculate expected date range
        # the end time should be Friday at 10:00 PM UTC
        end_time = datetime.fromisoformat('2025-04-05T22:00:00+00:00')
        # the start time should be 7 days ago at 10:00 PM UTC
        start_time = end_time - timedelta(days=7)
        date_range = f'{start_time.strftime("%Y-%m-%d")}--{end_time.strftime("%Y-%m-%d")}'

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        expected_compact_path = (
            f'compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/weekly/'
            f'{end_time.strftime("%Y/%m/%d")}/'
            f'{TEST_COMPACT}-{date_range}-report.zip'
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
                    'Privileges purchased for Kentucky,1\n'
                    'State Fees (Kentucky),$100.00\n'
                    'Privileges purchased for Nebraska,1\n'
                    'State Fees (Nebraska),$100.00\n'
                    'Privileges purchased for Ohio,1\n'
                    'State Fees (Ohio),$100.00\n'
                    'Administrative Fees,$31.50\n'  # $10.50 x 3 privileges
                    'Credit Card Transaction Fees Collected From Licensee,$9.00\n'  # $3.00 x 3 privileges
                    ',\n'
                    'Total Processed Amount,$340.50\n',
                    summary_content,
                )

            # Check transaction detail
            with zip_file.open(f'{TEST_COMPACT}-transaction-detail-{date_range}.csv') as f:
                detail_content = f.read().decode('utf-8')
                expected_lines = [
                    'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date UTC,State,State Fee,Administrative Fee,Collected Transaction Fee,Transaction Id,Privilege Id,Transaction Status'
                ]
                for state in ['OH', 'KY', 'NE']:
                    expected_lines.append(
                        f'{mock_user["givenName"]},{mock_user["familyName"]},{mock_user["providerId"]},03-30-2025,{state},100,10.50,3.00,{MOCK_TRANSACTION_ID},{MOCK_PRIVILEGE_ID_MAPPING[state.lower()]},{TEST_TRANSACTION_SUCCESSFUL_STATUS}'
                    )
                self.assertEqual('\n'.join(expected_lines) + '\n', detail_content)

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.email_service_client')
    def test_generate_report_accounts_for_unknown_line_item_fees(self, mock_email_service_client):
        """Test processing of transactions with multiple privileges in a single transaction."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_email_service_client_behavior(mock_email_service_client)

        self._add_compact_configuration_data(
            jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION, NEBRASKA_JURISDICTION]
        )

        mock_user = self._add_mock_provider_to_db('12345', 'John', 'Doe')
        # Create a transaction with in which the licensee is charged transaction fees
        self._add_mock_transaction_to_db(
            jurisdictions=['oh', 'ky', 'ne'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-03-30T12:00:00+00:00'),
            include_licensee_transaction_fees=True,
            include_unknown_line_item_fees=True,
        )

        # Calculate expected date range
        # the end time should be Friday at 10:00 PM UTC
        end_time = datetime.fromisoformat('2025-04-05T22:00:00+00:00')
        # the start time should be 7 days ago at 10:00 PM UTC
        start_time = end_time - timedelta(days=7)
        date_range = f'{start_time.strftime("%Y-%m-%d")}--{end_time.strftime("%Y-%m-%d")}'

        with self.assertRaises(CCInternalException) as exc_info:
            generate_transaction_reports(generate_mock_event(), self.mock_context)

        # check that the error message contains the expected line item id
        self.assertEqual(
            'One or more errors occurred while generating reports. '
            "Errors: ['transaction line item id does not match any known pattern "
            f'- transactionId={MOCK_TRANSACTION_ID} '
            "- itemId=unknown-line-item-fee']",
            exc_info.exception.message,
        )

        expected_compact_path = (
            f'compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/weekly/'
            f'{end_time.strftime("%Y/%m/%d")}/'
            f'{TEST_COMPACT}-{date_range}-report.zip'
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
                    'Privileges purchased for Kentucky,1\n'
                    'State Fees (Kentucky),$100.00\n'
                    'Privileges purchased for Nebraska,1\n'
                    'State Fees (Nebraska),$100.00\n'
                    'Privileges purchased for Ohio,1\n'
                    'State Fees (Ohio),$100.00\n'
                    'Administrative Fees,$31.50\n'  # $10.50 x 3 privileges
                    'Credit Card Transaction Fees Collected From Licensee,$9.00\n'  # $3.00 x 3 privileges
                    'Unknown Line Item Fees,$2.00\n'
                    ',\n'
                    'Total Processed Amount,$342.50\n',
                    summary_content,
                )

    # event bridge triggers the weekly report at Friday 10:00 PM UTC (5:00 PM EST)
    @patch('cc_common.config._Config.current_standard_datetime', datetime.fromisoformat('2025-04-05T22:00:00+00:00'))
    @patch('handlers.transaction_reporting.config.email_service_client')
    def test_generate_report_does_not_include_transactions_with_settlement_errors(self, mock_email_service_client):
        """Test that transactions with settlement errors are not included in the report."""
        from handlers.transaction_reporting import generate_transaction_reports

        _set_default_email_service_client_behavior(mock_email_service_client)

        self._add_compact_configuration_data(jurisdictions=[OHIO_JURISDICTION, KENTUCKY_JURISDICTION])

        mock_user = self._add_mock_provider_to_db('12345', 'John', 'Doe')
        # Create a transaction with a privilege which failed settlement
        self._add_mock_transaction_to_db(
            jurisdictions=['oh'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-04-01T22:00:01+00:00'),
            transaction_status=TEST_TRANSACTION_ERROR_STATUS,
        )

        # Create a transaction with a privilege which is successfully settled
        self._add_mock_transaction_to_db(
            jurisdictions=['ky'],
            licensee_id=mock_user['providerId'],
            month_iso_string='2025-03',
            transaction_settlement_time_utc=datetime.fromisoformat('2025-04-01T22:00:00+00:00'),
            transaction_status=TEST_TRANSACTION_SUCCESSFUL_STATUS,
        )

        generate_transaction_reports(generate_mock_event(), self.mock_context)

        # Calculate expected date range
        # the end time should be Friday at 10:00 PM UTC
        end_time = datetime.fromisoformat('2025-04-05T22:00:00+00:00')
        # the start time should be 7 days ago at 10:00 PM UTC
        start_time = end_time - timedelta(days=7)
        date_range = f'{start_time.strftime("%Y-%m-%d")}--{end_time.strftime("%Y-%m-%d")}'
        expected_compact_path = (
            f'compact/{TEST_COMPACT}/reports/compact-transactions/reporting-cycle/weekly/'
            f'{end_time.strftime("%Y/%m/%d")}/'
            f'{TEST_COMPACT}-{date_range}-report.zip'
        )

        # Verify S3 stored files
        # Check compact reports
        compact_zip_obj = self.config.s3_client.get_object(
            Bucket=self.config.transaction_reports_bucket_name, Key=expected_compact_path
        )

        with ZipFile(BytesIO(compact_zip_obj['Body'].read())) as zip_file:
            # Check financial summary, which in this case should only include the successful transaction
            with zip_file.open(f'{TEST_COMPACT}-financial-summary-{date_range}.csv') as f:
                summary_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Privileges purchased for Kentucky,1\n'
                    'State Fees (Kentucky),$100.00\n'
                    'Privileges purchased for Ohio,0\n'
                    'State Fees (Ohio),$0.00\n'
                    'Administrative Fees,$10.50\n'
                    ',\n'
                    'Total Processed Amount,$110.50\n',
                    summary_content,
                )

            # Check transaction detail, which in this case should only include the successful transaction
            with zip_file.open(f'{TEST_COMPACT}-transaction-detail-{date_range}.csv') as f:
                detail_content = f.read().decode('utf-8')
                self.assertEqual(
                    'Licensee First Name,Licensee Last Name,Licensee Id,Transaction Settlement Date UTC,State,State Fee,Administrative Fee,Collected Transaction Fee,Transaction Id,Privilege Id,Transaction Status\n'
                    f'{mock_user["givenName"]},{mock_user["familyName"]},{mock_user["providerId"]},04-01-2025,KY,100,10.50,0,{MOCK_TRANSACTION_ID},{MOCK_KENTUCKY_PRIVILEGE_ID},{TEST_TRANSACTION_SUCCESSFUL_STATUS}\n',
                    detail_content,
                )
