from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from io import BytesIO, StringIO
from zipfile import ZIP_DEFLATED, ZipFile

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.compact import Compact
from cc_common.data_model.schema.compact.common import COMPACT_TYPE
from cc_common.data_model.schema.jurisdiction.common import JURISDICTION_TYPE
from cc_common.exceptions import CCInternalException
from report_window import ReportCycle, ReportWindow


class ReportableTransactionStatuses(StrEnum):
    """Transaction statuses that should be included in financial reports."""

    SettledSuccessfully = 'settledSuccessfully'


def _store_compact_reports_in_s3(
    compact: str,
    reporting_cycle: str,
    report_window: ReportWindow,
    summary_report: str,
    transaction_detail: str,
    bucket_name: str,
) -> dict[str, str]:
    """Store compact reports in S3 with appropriate compression formats.

    :param compact: Compact name
    :param reporting_cycle: Either 'weekly' or 'monthly'
    :param report_window: the Report Window
    :param summary_report: Financial summary report CSV content
    :param transaction_detail: Transaction detail report CSV content
    :param bucket_name: S3 bucket name
    :return: Dictionary of file types to their S3 paths
    """
    base_path = (
        f'compact/{compact}/reports/compact-transactions/reporting-cycle/{reporting_cycle}/'
        f'{report_window.display_end.strftime("%Y/%m/%d")}'
    )

    # Define paths for all report files
    # Currently, we are only sending the .zip file in the email reporting, but there is potential
    # to store .gz files in the future
    paths = {
        'report_zip': f'{base_path}/{compact}-{report_window.display_text}-report.zip',
    }

    s3_client = config.s3_client

    # Create and store combined zip with uncompressed CSVs
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w', compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr(f'financial-summary-{report_window.display_text}.csv', summary_report.encode('utf-8'))
        zip_file.writestr(f'transaction-detail-{report_window.display_text}.csv', transaction_detail.encode('utf-8'))
    s3_client.put_object(Bucket=bucket_name, Key=paths['report_zip'], Body=zip_buffer.getvalue())

    return paths


def _store_jurisdiction_reports_in_s3(
    compact: str,
    jurisdiction: str,
    reporting_cycle: str,
    report_window: ReportWindow,
    transaction_detail: str,
    bucket_name: str,
) -> dict[str, str]:
    """Store jurisdiction reports in S3 with appropriate compression formats.

    :param compact: Compact name
    :param jurisdiction: Jurisdiction postal code
    :param reporting_cycle: Either 'weekly' or 'monthly'
    :param report_window: The report window
    :param transaction_detail: Transaction detail report CSV content
    :param bucket_name: S3 bucket name
    :return: Dictionary of file types to their S3 paths
    """
    base_path = (
        f'compact/{compact}/reports/jurisdiction-transactions/jurisdiction/{jurisdiction}/'
        f'reporting-cycle/{reporting_cycle}/{report_window.display_end.strftime("%Y/%m/%d")}'
    )

    # Define paths for all report files
    # Currently, we are only sending the .zip file in the email reporting, but there is potential
    # to store .gz files in the future
    paths = {
        'report_zip': f'{base_path}/{jurisdiction}-{report_window.display_text}-report.zip',
    }

    s3_client = config.s3_client

    # Create and store zip with uncompressed CSV
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w', compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            f'{jurisdiction}-transaction-detail-{report_window.display_text}.csv', transaction_detail.encode('utf-8')
        )
    s3_client.put_object(Bucket=bucket_name, Key=paths['report_zip'], Body=zip_buffer.getvalue())

    return paths


def generate_transaction_reports(event: dict, context: LambdaContext) -> dict:  # noqa: ARG001 unused-argument
    """
    Generate transaction reports for a compact and its jurisdictions.

    For compacts, we generate a financial summary report and a transaction detail report.
    For jurisdictions, we generate a transaction detail report.

    Reports are stored in compressed zip files in S3. We send the zip files in email reports.

    :param event: Event containing the compact name and reporting cycle
    :param context: Lambda context
    :return: Success message
    """
    compact = event['compact']
    reporting_cycle = ReportCycle(event['reportingCycle'])

    # Support 'manual' report date overrides for re-runs
    report_start_override = event.get('reportStartOverride')
    report_end_override = event.get('reportEndOverride')
    if report_start_override and report_end_override:
        report_window = ReportWindow(
            reporting_cycle,
            _display_start_date=date.fromisoformat(report_start_override),
            _display_end_date=date.fromisoformat(report_end_override),
        )
    else:
        report_window = ReportWindow(reporting_cycle)

    logger.info(
        'Generating transaction reports',
        compact=compact,
        reporting_cycle=reporting_cycle,
        window=report_window.display_text,
    )

    # this is used to track any errors that occur when generating the reports
    # without preventing valid reports from being sent
    lambda_error_messages = []

    # Initialize clients
    data_client = config.data_client
    transaction_client = config.transaction_client
    compact_configuration_client = config.compact_configuration_client
    email_service_client = config.email_service_client

    # Get compact configuration and jurisdictions that are live for licensee registration
    compact_configuration_options = compact_configuration_client.get_privilege_purchase_options(compact=compact)

    compact_configuration = next(
        (Compact(item) for item in compact_configuration_options['items'] if item['type'] == COMPACT_TYPE), None
    )
    jurisdiction_configurations = [
        item for item in compact_configuration_options['items'] if item['type'] == JURISDICTION_TYPE
    ]

    if not compact_configuration or not jurisdiction_configurations:
        logger.warning('The compact is not yet live - skipping reports')
        return {'message': 'Compact not live yet'}

    # Get the S3 bucket name
    bucket_name = config.transaction_reports_bucket_name

    # Get all transactions for the time period
    transactions = transaction_client.get_transactions_in_range(
        compact=compact, start_epoch=report_window.start_epoch, end_epoch=report_window.end_epoch
    )

    # For now, we only report on transactions that have been successfully settled, so we filter to only include
    # transactions with a 'settledSuccessfully' status. This is because in the case of a settlement error, no money was
    # transferred for that transaction, and the transaction will be reprocessed in a future batch by Authorize.net after
    # the account owners have worked with their MSP to resolve the issue that caused the settlement error.
    # See https://community.developer.cybersource.com/t5/Integration-and-Testing/What-happens-to-a-batch-having-a-settlementState-of/td-p/58993
    # for more information on how settlement errors are reprocessed.
    transactions = [t for t in transactions if t.get('transactionStatus') in ReportableTransactionStatuses]

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

    # Store compact reports in S3 and get paths
    compact_paths = _store_compact_reports_in_s3(
        compact=compact,
        reporting_cycle=reporting_cycle,
        report_window=report_window,
        summary_report=compact_summary_csv,
        transaction_detail=compact_transaction_csv,
        bucket_name=bucket_name,
    )

    # Send compact summary report with S3 paths
    try:
        email_service_client.send_compact_transaction_report_email(
            compact=compact,
            report_s3_path=compact_paths['report_zip'],
            reporting_cycle=reporting_cycle,
            start_date=report_window.display_start,
            end_date=report_window.display_end,
        )
    except CCInternalException as e:
        logger.error(
            'Failed to send compact summary report email',
            compact=compact,
            error=str(e),
        )
        lambda_error_messages.append(str(e))

    # Store and send jurisdiction reports
    for jurisdiction, report_csv in jurisdiction_reports.items():
        # Store jurisdiction report and get paths
        jurisdiction_paths = _store_jurisdiction_reports_in_s3(
            compact=compact,
            jurisdiction=jurisdiction,
            reporting_cycle=reporting_cycle,
            report_window=report_window,
            transaction_detail=report_csv,
            bucket_name=bucket_name,
        )

        try:
            email_service_client.send_jurisdiction_transaction_report_email(
                compact=compact,
                jurisdiction=jurisdiction,
                report_s3_path=jurisdiction_paths['report_zip'],
                reporting_cycle=reporting_cycle,
                start_date=report_window.display_start,
                end_date=report_window.display_end,
            )
        except CCInternalException as e:
            logger.error(
                'Failed to send jurisdiction report email',
                compact=compact,
                jurisdiction=jurisdiction,
                error=str(e),
            )
            lambda_error_messages.append(str(e))

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
    unknown_jurisdiction_fees: dict[str, Decimal] = {}
    unknown_jurisdictions_privileges: dict[str, int] = {}
    unknown_fees = 0
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
                    unknown_jurisdictions_privileges[jurisdiction] = (
                        unknown_jurisdictions_privileges.get(jurisdiction, 0) + quantity
                    )
                    unknown_jurisdiction_fees[jurisdiction] = unknown_jurisdiction_fees.get(jurisdiction, 0) + fee
            # This should never happen in production, but our test envs have a legacy transaction line items
            # that use the pattern {compact}-{jurisdiction postal code}. We check for unknown item ids here to make sure
            # every possible line item is accounted for in the report
            else:
                error_message = 'transaction line item id does not match any known pattern'
                lambda_error_messages.append(
                    f'{error_message} - transactionId={transaction["transactionId"]} - itemId={item["itemId"]}'
                )
                logger.error(
                    error_message,
                    item_id=item['itemId'],
                    description=item.get('description', ''),
                    transactionId=transaction['transactionId'],
                )
                unknown_fees += fee

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
        writer.writerow(
            [f'Privileges purchased for UNKNOWN ({jurisdiction})', unknown_jurisdictions_privileges[jurisdiction]]
        )
        writer.writerow([f'State Fees (UNKNOWN ({jurisdiction}))', f'${unknown_jurisdiction_fees[jurisdiction]:.2f}'])

    # Write compact fees
    writer.writerow(['Administrative Fees', f'${compact_fees:.2f}'])

    # Write transaction fees if applicable
    if transaction_fees > 0 or (
        hasattr(compact_config, 'transactionFeeConfiguration')
        and getattr(compact_config.transactionFeeConfiguration, 'licenseeCharges', {}).get('active')
    ):
        writer.writerow(['Credit Card Transaction Fees Collected From Licensee', f'${transaction_fees:.2f}'])

    # Reporting unknown line item fees so they can be accounted for towards the total processed amount
    # we never expect this to show up in prod, but are including it here so nothing slips through the cracks.
    if unknown_fees > 0:
        writer.writerow(['Unknown Line Item Fees', f'${unknown_fees:.2f}'])

    # Add blank line before total
    writer.writerow(['', ''])
    writer.writerow(['Total Processed Amount', f'${total_processed_amount:.2f}'])

    return output.getvalue()


def _generate_compact_transaction_report(transactions: list[dict], providers: dict) -> str:
    """Generate the compact transaction report CSV."""
    output = StringIO()
    writer = csv.writer(output, lineterminator='\n', dialect='excel')
    column_headers = [
        'Licensee First Name',
        'Licensee Last Name',
        'Licensee Id',
        'Transaction Settlement Date UTC',
        'State',
        'State Fee',
        'Administrative Fee',
        'Collected Transaction Fee',
        'Transaction Id',
        'Privilege Id',
        'Transaction Status',
    ]
    writer.writerow(column_headers)

    if not transactions:
        writer.writerow(['No transactions for this period'] + [''] * (len(column_headers) - 1))
        return output.getvalue()

    for transaction in transactions:
        provider = providers.get(transaction['licenseeId'], {})
        transaction_date = datetime.fromisoformat(transaction['batch']['settlementTimeUTC']).strftime('%m-%d-%Y')
        compact_fee_item = next(item for item in transaction['lineItems'] if item['itemId'].endswith('-compact-fee'))

        # Get transaction fee if it exists
        transaction_fee_item = next(
            (item for item in transaction['lineItems'] if item['itemId'] == 'credit-card-transaction-fee'), None
        )

        # Write a row for each state privilege in the transaction
        for item in transaction['lineItems']:
            if item['itemId'].startswith('priv:'):
                # Extract jurisdiction from itemId (format: priv:{compact}-{jurisdiction})
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
                        item.get('privilegeId', 'UNKNOWN'),
                        transaction['transactionStatus'],
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
        column_headers = [
            'Licensee First Name',
            'Licensee Last Name',
            'Licensee Id',
            'Transaction Settlement Date UTC',
            'State Fee',
            'State',
            'Transaction Id',
            'Privilege Id',
            'Transaction Status',
        ]
        writer.writerow(column_headers)

        if not trans_items:
            writer.writerow(['No transactions for this period'] + [''] * (len(column_headers) - 1))
            writer.writerow([''] * len(column_headers))
            writer.writerow(['Privileges Purchased', 'Total State Amount'] + [''] * (len(column_headers) - 2))
            writer.writerow(['0', '$0.00'] + [''] * (len(column_headers) - 2))
            reports[jurisdiction] = output.getvalue()
            continue

        total_privileges = 0
        total_amount = 0

        for transaction, item in trans_items:
            provider = providers.get(transaction['licenseeId'], {})
            transaction_date = datetime.fromisoformat(transaction['batch']['settlementTimeUTC']).strftime('%m-%d-%Y')

            writer.writerow(
                [
                    provider.get('givenName', 'UNKNOWN'),
                    provider.get('familyName', 'UNKNOWN'),
                    transaction['licenseeId'],
                    transaction_date,
                    item['unitPrice'],
                    jurisdiction.upper(),
                    transaction['transactionId'],
                    item.get('privilegeId', 'UNKNOWN'),
                    transaction['transactionStatus'],
                ]
            )

            # sometimes authorize.net has returned this quantity field as '1.0'
            # so we need to account for this by first casting to a float, then an int
            total_privileges += int(float(item['quantity']))
            total_amount += float(item['unitPrice']) * int(float(item['quantity']))

        # Add summary rows
        writer.writerow([''] * len(column_headers))
        writer.writerow(['Privileges Purchased', 'Total State Amount'] + [''] * (len(column_headers) - 2))
        writer.writerow([int(total_privileges), f'${total_amount:.2f}'] + [''] * (len(column_headers) - 2))

        reports[jurisdiction] = output.getvalue()

    return reports
