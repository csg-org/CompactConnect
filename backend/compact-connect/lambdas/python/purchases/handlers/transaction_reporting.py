from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.compact import COMPACT_TYPE, Compact
from cc_common.data_model.schema.jurisdiction import JURISDICTION_TYPE
from cc_common.exceptions import CCInternalException, CCNotFoundException


def _get_display_date_range(reporting_cycle: str) -> tuple[datetime, datetime]:
    """Get the display date range for reports.

    These dates are used for report filenames and email notifications.

    :param reporting_cycle: Either 'weekly' or 'monthly'
    :return: Tuple of (start_time, end_time) in UTC for display purposes
    """
    if reporting_cycle == 'weekly':
        end_time = config.current_standard_datetime
        # Go back 7 days to capture the full week
        start_time = end_time - timedelta(days=7)
        return start_time, end_time
    if reporting_cycle == 'monthly':
        # Reports run shortly after midnight on the first day of the month.
        # Knowing this, we can use the current date to get the start and end of the month.
        # By going back 1 day from the first day of the current month, we get the last day of the previous month.
        end_time = config.current_standard_datetime.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
        # Start time is the first day of the previous month
        start_time = end_time.replace(day=1)
        return start_time, end_time
    raise ValueError(f'Invalid reporting cycle: {reporting_cycle}')


def _get_query_date_range(reporting_cycle: str) -> tuple[datetime, datetime]:
    """Get the query date range for DynamoDB queries.

    Our Sort Key format for transactions includes additional components after the timestamp
    (COMPACT#name#TIME#timestamp#BATCH#id#TX#id), So the DynamoDB BETWEEN condition is INCLUSIVE for the beginning
    range and EXCLUSIVE at the end range. This is because DynamoDB performs lexicographical comparison on the entire
    sort key string. When the sort key continues beyond the comparison value:

    - For the lower bound: Additional characters after the comparison point make the full key "greater than" the bound,
      satisfying the >= condition
    - For the upper bound: Additional characters after the comparison point make the full key "greater than" the bound,
     failing the <= condition

    We need to adjust our timestamps accordingly to ensure we capture all settled transactions exactly once.

    :param reporting_cycle: Either 'weekly' or 'monthly'
    :return: Tuple of (start_time, end_time) in UTC for DynamoDB queries
    """
    if reporting_cycle == 'weekly':
        # Reports run on Friday 10:00 PM UTC
        end_time = config.current_standard_datetime.replace(hour=22, minute=0, second=0, microsecond=0)
        # Go back 7 days to capture the full week
        start_time = end_time - timedelta(days=7)
        return start_time, end_time

    if reporting_cycle == 'monthly':
        # Reports run shortly after midnight on the first day of the month
        # End time is midnight, since that will be excluded from the BETWEEN key condition
        end_time = config.current_standard_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        # Start time is midnight of the previous month
        start_time = (end_time - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start_time, end_time

    raise ValueError(f'Invalid reporting cycle: {reporting_cycle}')


def _store_compact_reports_in_s3(
    compact: str,
    reporting_cycle: str,
    start_time: datetime,
    end_time: datetime,
    summary_report: str,
    transaction_detail: str,
    bucket_name: str,
) -> dict[str, str]:
    """Store compact reports in S3 with appropriate compression formats.

    :param compact: Compact name
    :param reporting_cycle: Either 'weekly' or 'monthly'
    :param start_time: Report start time
    :param end_time: Report end time
    :param summary_report: Financial summary report CSV content
    :param transaction_detail: Transaction detail report CSV content
    :param bucket_name: S3 bucket name
    :return: Dictionary of file types to their S3 paths
    """
    date_range = f"{start_time.strftime('%Y-%m-%d')}--{end_time.strftime('%Y-%m-%d')}"
    base_path = (
        f"compact/{compact}/reports/compact-transactions/reporting-cycle/{reporting_cycle}/"
        f"{end_time.strftime('%Y/%m/%d')}"
    )

    # Define paths for all report files
    # Currently, we are only sending the .zip file in the email reporting, but there is potential
    # to store .gz files in the future
    paths = {
        'report_zip': f'{base_path}/{compact}-{date_range}-report.zip',
    }

    s3_client = config.s3_client

    # Create and store combined zip with uncompressed CSVs
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w', compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr(f'{compact}-financial-summary-{date_range}.csv', summary_report.encode('utf-8'))
        zip_file.writestr(f'{compact}-transaction-detail-{date_range}.csv', transaction_detail.encode('utf-8'))
    s3_client.put_object(Bucket=bucket_name, Key=paths['report_zip'], Body=zip_buffer.getvalue())

    return paths


def _store_jurisdiction_reports_in_s3(
    compact: str,
    jurisdiction: str,
    reporting_cycle: str,
    start_time: datetime,
    end_time: datetime,
    transaction_detail: str,
    bucket_name: str,
) -> dict[str, str]:
    """Store jurisdiction reports in S3 with appropriate compression formats.

    :param compact: Compact name
    :param jurisdiction: Jurisdiction postal code
    :param reporting_cycle: Either 'weekly' or 'monthly'
    :param start_time: Report start time
    :param end_time: Report end time
    :param transaction_detail: Transaction detail report CSV content
    :param bucket_name: S3 bucket name
    :return: Dictionary of file types to their S3 paths
    """
    date_range = f"{start_time.strftime('%Y-%m-%d')}--{end_time.strftime('%Y-%m-%d')}"
    base_path = (
        f"compact/{compact}/reports/jurisdiction-transactions/jurisdiction/{jurisdiction}/"
        f"reporting-cycle/{reporting_cycle}/{end_time.strftime('%Y/%m/%d')}"
    )

    # Define paths for all report files
    # Currently, we are only sending the .zip file in the email reporting, but there is potential
    # to store .gz files in the future
    paths = {
        'report_zip': f'{base_path}/{jurisdiction}-{date_range}-report.zip',
    }

    s3_client = config.s3_client

    # Create and store zip with uncompressed CSV
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w', compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr(f'{jurisdiction}-transaction-detail-{date_range}.csv', transaction_detail.encode('utf-8'))
    s3_client.put_object(Bucket=bucket_name, Key=paths['report_zip'], Body=zip_buffer.getvalue())

    return paths


def generate_transaction_reports(event: dict, context: LambdaContext) -> dict:  # noqa: ARG001 unused-argument
    """
    Generate transaction reports for a compact and its jurisdictions.

    :param event: Event containing the compact name and reporting cycle
    :param context: Lambda context
    :return: Success message
    """
    compact = event['compact']
    reporting_cycle = event['reportingCycle']
    logger.info('Generating transaction reports', compact=compact, reporting_cycle=reporting_cycle)

    # this is used to track any errors that occur when generating the reports
    # without preventing valid reports from being sent
    lambda_error_messages = []

    # Initialize clients
    data_client = config.data_client
    transaction_client = config.transaction_client
    compact_configuration_client = config.compact_configuration_client

    # Get the S3 bucket name
    bucket_name = config.transaction_reports_bucket_name

    # Get both query and display date ranges
    query_start_time, query_end_time = _get_query_date_range(reporting_cycle)

    # Convert query times to epochs for DynamoDB
    start_epoch = int(query_start_time.timestamp())
    end_epoch = int(query_end_time.timestamp())

    # Get all transactions for the time period
    transactions = transaction_client.get_transactions_in_range(
        compact=compact, start_epoch=start_epoch, end_epoch=end_epoch
    )

    # Get compact configuration and jurisdictions
    compact_configuration_options = compact_configuration_client.get_privilege_purchase_options(compact=compact)

    compact_configuration = next(
        (Compact(item) for item in compact_configuration_options['items'] if item['type'] == COMPACT_TYPE), None
    )
    if not compact_configuration:
        message = f'Compact configuration not found for the specified compact: {compact}'
        logger.error(message)
        # we can't continue if this is missing, so we raise an exception
        raise CCNotFoundException(message)

    jurisdiction_configurations = [
        item for item in compact_configuration_options['items'] if item['type'] == JURISDICTION_TYPE
    ]

    # Get unique provider IDs from transactions and their details
    provider_ids = {t['licenseeId'] for t in transactions}
    providers = {}
    if provider_ids:
        providers = {p['providerId']: p for p in data_client.batch_get_providers_by_id(compact, list(provider_ids))}

        # the batch_get_item api call will silently omit any records that are not found, so we need to check for it here
        # This should not happen, but if it does, we log it
        missing_providers = provider_ids - providers.keys()
        if missing_providers:
            logger.error(
                'Some providers were not found in the database',
                missing_provider_ids=list(missing_providers),
                compact=compact,
            )
            # append the error so we can raise an exception after sending the reports
            lambda_error_messages.append(
                f'Some providers were not found in the database. Providers not found: {missing_providers}'
            )

    # Generate reports
    compact_summary_csv = _generate_compact_summary_report(
        transactions, compact_configuration, jurisdiction_configurations, lambda_error_messages
    )
    compact_transaction_csv = _generate_compact_transaction_report(transactions, providers)
    jurisdiction_reports = _generate_jurisdiction_reports(transactions, providers, jurisdiction_configurations)

    display_start_time, display_end_time = _get_display_date_range(reporting_cycle)

    # Store compact reports in S3 and get paths
    compact_paths = _store_compact_reports_in_s3(
        compact=compact,
        reporting_cycle=reporting_cycle,
        start_time=display_start_time,
        end_time=display_end_time,
        summary_report=compact_summary_csv,
        transaction_detail=compact_transaction_csv,
        bucket_name=bucket_name,
    )

    # Send compact summary report with S3 paths
    compact_response = config.lambda_client.invoke(
        FunctionName=config.email_notification_service_lambda_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(
            {
                'compact': compact,
                'template': 'CompactTransactionReporting',
                'recipientType': 'COMPACT_SUMMARY_REPORT',
                'templateVariables': {
                    'reportS3Path': compact_paths['report_zip'],
                    'reportingCycle': reporting_cycle,
                    'startDate': display_start_time.strftime('%Y-%m-%d'),
                    'endDate': display_end_time.strftime('%Y-%m-%d'),
                },
            }
        ),
    )

    if compact_response.get('FunctionError'):
        logger.error(
            'Failed to send compact summary report email',
            compact=compact,
            error=compact_response.get('FunctionError'),
        )
        lambda_error_messages.append(compact_response.get('FunctionError'))

    # Store and send jurisdiction reports
    for jurisdiction, report_csv in jurisdiction_reports.items():
        # Store jurisdiction report and get paths
        jurisdiction_paths = _store_jurisdiction_reports_in_s3(
            compact=compact,
            jurisdiction=jurisdiction,
            reporting_cycle=reporting_cycle,
            start_time=display_start_time,
            end_time=display_end_time,
            transaction_detail=report_csv,
            bucket_name=bucket_name,
        )

        jurisdiction_response = config.lambda_client.invoke(
            FunctionName=config.email_notification_service_lambda_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': compact,
                    'jurisdiction': jurisdiction,
                    'template': 'JurisdictionTransactionReporting',
                    'recipientType': 'JURISDICTION_SUMMARY_REPORT',
                    'templateVariables': {
                        'reportS3Path': jurisdiction_paths['report_zip'],
                        'reportingCycle': reporting_cycle,
                        'startDate': display_start_time.strftime('%Y-%m-%d'),
                        'endDate': display_end_time.strftime('%Y-%m-%d'),
                    },
                }
            ),
        )

        if jurisdiction_response.get('FunctionError'):
            logger.error(
                'Failed to send jurisdiction report email',
                compact=compact,
                jurisdiction=jurisdiction,
                error=jurisdiction_response.get('FunctionError'),
            )
            lambda_error_messages.append(jurisdiction_response.get('FunctionError'))

    if lambda_error_messages:
        raise CCInternalException(
            f'One or more errors occurred while generating reports. Errors: {lambda_error_messages}'
        )

    return {'message': 'reports sent successfully'}


def _get_jurisdiction_postal_abbreviations(jurisdiction_configs: list[dict]) -> set[str]:
    """Get the postal abbreviations for all jurisdictions."""
    return {j['postalAbbreviation'].lower() for j in jurisdiction_configs}


def _generate_compact_summary_report(
    transactions: list[dict],
    compact_config: Compact,
    jurisdiction_configs: list[dict],
    lambda_error_messages: list[str],
) -> str:
    """Generate the compact financial summary report CSV."""
    # Initialize variables
    compact_fees = 0
    transaction_fees = 0
    configured_jurisdictions = _get_jurisdiction_postal_abbreviations(jurisdiction_configs)
    jurisdiction_fees: dict[str, Decimal] = {j['postalAbbreviation'].lower(): Decimal(0) for j in jurisdiction_configs}
    jurisdiction_privileges: dict[str, int] = {j['postalAbbreviation'].lower(): 0 for j in jurisdiction_configs}
    unknown_jurisdiction_fees: dict[str, Decimal]= {}
    unknown_jurisdictions_privileges: dict[str, int] = {}
    total_processed_amount = 0

    # Single pass through transactions to calculate all fees
    for transaction in transactions:
        for item in transaction['lineItems']:
            # sometimes authorize.net has returned this quantity field as '1.0'
            # so we need to account for this by first casting to a float, then an int
            quantity = int(float(item['quantity']))
            fee = Decimal(item['unitPrice']) * quantity

            if item['itemId'].endswith('-compact-fee'):
                compact_fees += fee
            elif item['itemId'] == 'credit-card-transaction-fee':
                transaction_fees += fee
            elif item['itemId'].startswith('priv:'):
                jurisdiction = item['itemId'].split('-')[1].lower()
                if jurisdiction in configured_jurisdictions:
                    # Add fee to jurisdiction and increment privilege count
                    jurisdiction_fees[jurisdiction] += fee
                    jurisdiction_privileges[jurisdiction] += quantity
                else:
                    # jurisdiction does not match with our known jurisdictions, add it to the report
                    unknown_jurisdictions_privileges[jurisdiction] = unknown_jurisdictions_privileges.get(jurisdiction,
                                                                                                          0) + quantity
                    unknown_jurisdiction_fees[jurisdiction] = unknown_jurisdiction_fees.get(jurisdiction, 0) + fee

            total_processed_amount += fee

    if unknown_jurisdictions_privileges:
        logger.error(
            'Unknown jurisdictions found in transactions.',
            jurisdictions=unknown_jurisdictions_privileges.keys(),
            compact=compact_config.compact_abbr,
        )
        # we can still generate the reports, but we need to add this so an exception is thrown after sending the reports
        lambda_error_messages.append(
            f'Unknown jurisdictions found in transactions. Jurisdictions: {unknown_jurisdictions_privileges.keys()}'
        )

    # Generate CSV
    output = StringIO()
    writer = csv.writer(output, lineterminator='\n', dialect='excel')

    # Write jurisdiction fees and privileges
    for jurisdiction in jurisdiction_configs:
        postal = jurisdiction['postalAbbreviation'].lower()
        fee_value = jurisdiction_fees.get(postal, 0)
        privilege_count = jurisdiction_privileges.get(postal, 0)
        writer.writerow([f'Privileges purchased for {jurisdiction["jurisdictionName"].capitalize()}', privilege_count])
        writer.writerow([f'State Fees ({jurisdiction["jurisdictionName"].capitalize()})', f'${fee_value:.2f}'])

    # Write unknown jurisdiction fees if any
    for jurisdiction in unknown_jurisdictions_privileges.keys():
        writer.writerow([f'Privileges purchased for UNKNOWN ({jurisdiction})', unknown_jurisdictions_privileges[jurisdiction]])
        writer.writerow([f'State Fees (UNKNOWN ({jurisdiction}))', f'${unknown_jurisdiction_fees[jurisdiction]:.2f}'])

    # Write compact fees
    writer.writerow(['Administrative Fees', f'${compact_fees:.2f}'])

    # Write transaction fees if applicable
    if transaction_fees > 0 or (hasattr(compact_config, 'transactionFeeConfiguration') and
                               getattr(compact_config.transactionFeeConfiguration, 'licenseeCharges', {}).get('active')):
        writer.writerow(['Credit Card Transaction Fees Collected From Licensee', f'${transaction_fees:.2f}'])

    # Add blank line before total
    writer.writerow(['', ''])
    writer.writerow(['Total Processed Amount', f'${total_processed_amount:.2f}'])

    return output.getvalue()


def _generate_compact_transaction_report(transactions: list[dict], providers: dict) -> str:
    """Generate the compact transaction report CSV."""
    output = StringIO()
    writer = csv.writer(output, lineterminator='\n', dialect='excel')
    writer.writerow(
        [
            'Licensee First Name',
            'Licensee Last Name',
            'Licensee Id',
            'Transaction Settlement Date',
            'State',
            'State Fee',
            'Administrative Fee',
            'Collected Transaction Fee',
            'Transaction Id',
        ]
    )

    if not transactions:
        writer.writerow(['No transactions for this period'] + [''] * 8)
        return output.getvalue()

    for transaction in transactions:
        provider = providers.get(transaction['licenseeId'], {})
        transaction_date = datetime.fromisoformat(transaction['batch']['settlementTimeUTC']).strftime('%m-%d-%Y')
        compact_fee_item = next(item for item in transaction['lineItems'] if item['itemId'].endswith('-compact-fee'))
        
        # Get transaction fee if it exists
        transaction_fee_item = next(
            (item for item in transaction['lineItems'] if item['itemId'] == 'credit-card-transaction-fee'),
            None
        )

        # Write a row for each state privilege in the transaction
        for item in transaction['lineItems']:
            if item['itemId'].startswith('priv:'):
                # Extract jurisdiction from itemId (format: priv:compact-jurisdiction)
                state = item['itemId'].split('-')[1].upper()

                writer.writerow(
                    [
                        provider.get('givenName', 'UNKNOWN'),
                        provider.get('familyName', 'UNKNOWN'),
                        transaction['licenseeId'],
                        transaction_date,
                        state,
                        item['unitPrice'],
                        compact_fee_item['unitPrice'],
                        transaction_fee_item['unitPrice'] if transaction_fee_item else '0',
                        transaction['transactionId'],
                    ]
                )

    return output.getvalue()


def _generate_jurisdiction_reports(
    transactions: list[dict], providers: dict[str, dict], jurisdiction_configurations: list[dict]
) -> dict[str, str]:
    """Generate transaction reports for each jurisdiction."""
    jurisdiction_transactions: dict[str, list[tuple[dict, dict]]] = {
        j['postalAbbreviation'].lower(): [] for j in jurisdiction_configurations
    }

    # Group transactions by jurisdiction
    for transaction in transactions:
        for item in transaction['lineItems']:
            if item['itemId'].startswith('priv:'):
                state = item['itemId'].split('-')[1].lower()
                if state in jurisdiction_transactions:
                    jurisdiction_transactions[state].append((transaction, item))

    # Generate report for each jurisdiction
    reports = {}
    for jurisdiction, trans_items in jurisdiction_transactions.items():
        logger.info('Generating report for jurisdiction', jurisdiction=jurisdiction)
        output = StringIO()
        writer = csv.writer(output, lineterminator='\n', dialect='excel')
        writer.writerow(
            [
                'First Name',
                'Last Name',
                'Licensee Id',
                'Transaction Settlement Date',
                'State Fee',
                'State',
                'Compact Fee',
                'Transaction Id',
            ]
        )

        if not trans_items:
            writer.writerow(['No transactions for this period'] + [''] * 7)
            writer.writerow([''] * 8)
            writer.writerow(['Privileges Purchased', 'Total State Amount'] + [''] * 6)
            writer.writerow(['0', '$0.00'] + [''] * 6)
            reports[jurisdiction] = output.getvalue()
            continue

        total_privileges = 0
        total_amount = 0

        for transaction, item in trans_items:
            provider = providers.get(transaction['licenseeId'], {})
            transaction_date = datetime.fromisoformat(transaction['batch']['settlementTimeUTC']).strftime('%m-%d-%Y')

            compact_fee_item = next(i for i in transaction['lineItems'] if i['itemId'].endswith('-compact-fee'))

            writer.writerow(
                [
                    provider.get('givenName', 'UNKNOWN'),
                    provider.get('familyName', 'UNKNOWN'),
                    transaction['licenseeId'],
                    transaction_date,
                    item['unitPrice'],
                    jurisdiction.upper(),
                    compact_fee_item['unitPrice'],
                    transaction['transactionId'],
                ]
            )

            # sometimes authorize.net has returned this quantity field as '1.0'
            # so we need to account for this by first casting to a float, then an int
            total_privileges += int(float(item['quantity']))
            total_amount += float(item['unitPrice']) * int(float(item['quantity']))

        # Add summary rows
        writer.writerow([''] * 8)
        writer.writerow(['Privileges Purchased', 'Total State Amount'] + [''] * 6)
        writer.writerow([int(total_privileges), f'${total_amount:.2f}'] + [''] * 6)

        reports[jurisdiction] = output.getvalue()

    return reports
