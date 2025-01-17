import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal
from io import StringIO

from aws_lambda_powertools.utilities.typing import LambdaContext
from cc_common.config import config, logger
from cc_common.data_model.schema.compact import COMPACT_TYPE, Compact
from cc_common.data_model.schema.jurisdiction import JURISDICTION_TYPE
from cc_common.exceptions import CCInternalException, CCNotFoundException


def generate_transaction_reports(event: dict, context: LambdaContext) -> dict:  # noqa: ARG001 unused-argument
    """
    Generate weekly transaction reports for a compact and its jurisdictions.

    :param event: Event containing the compact name
    :param context: Lambda context
    :return: Success message
    """
    compact = event['compact']
    logger.info('Generating transaction reports', compact=compact)
    # this is used to track any errors that occur when generating the reports
    # without preventing valid reports from being sent
    lambda_error_messages = []

    # Initialize clients
    data_client = config.data_client
    transaction_client = config.transaction_client

    # Calculate time range for the past week
    # Use 12:00:00.0 AM UTC of the next day for end time to ensure we capture full day
    end_time = config.current_standard_datetime.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start_time = end_time - timedelta(days=7)
    start_epoch = int(start_time.timestamp())
    end_epoch = int(end_time.timestamp())

    # Get all transactions for the past week
    transactions = transaction_client.get_transactions_in_range(
        compact=compact, start_epoch=start_epoch, end_epoch=end_epoch
    )

    # Get compact configuration and jurisdictions
    compact_configuration_options = data_client.get_privilege_purchase_options(compact=compact)

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

    # Send compact summary report
    compact_response = config.lambda_client.invoke(
        FunctionName=config.email_notification_service_lambda_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(
            {
                'compact': compact,
                'template': 'CompactTransactionReporting',
                'recipientType': 'COMPACT_SUMMARY_REPORT',
                'templateVariables': {
                    'compactFinancialSummaryReportCSV': compact_summary_csv,
                    'compactTransactionReportCSV': compact_transaction_csv,
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
    # Send jurisdiction reports
    for jurisdiction, report in jurisdiction_reports.items():
        jurisdiction_response = config.lambda_client.invoke(
            FunctionName=config.email_notification_service_lambda_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(
                {
                    'compact': compact,
                    'jurisdiction': jurisdiction,
                    'template': 'JurisdictionTransactionReporting',
                    'recipientType': 'JURISDICTION_SUMMARY_REPORT',
                    'templateVariables': {'jurisdictionTransactionReportCSV': report},
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
        raise CCInternalException(f'Failed to send one or more reports. Errors: {lambda_error_messages}')

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
    configured_jurisdictions = _get_jurisdiction_postal_abbreviations(jurisdiction_configs)
    jurisdiction_fees: dict[str, Decimal] = {j['postalAbbreviation'].lower(): Decimal(0) for j in jurisdiction_configs}
    unknown_jurisdictions = set()

    # Single pass through transactions to calculate all fees
    for transaction in transactions:
        for item in transaction['lineItems']:
            fee = Decimal(item['unitPrice']) * int(item['quantity'])

            if item['itemId'].endswith('-compact-fee'):
                compact_fees += fee
            else:
                jurisdiction = item['itemId'].split('-')[1]
                if jurisdiction not in configured_jurisdictions:
                    unknown_jurisdictions.add(jurisdiction)
                    if jurisdiction not in jurisdiction_fees:
                        jurisdiction_fees[jurisdiction] = fee
                        continue

                # Add fee to jurisdiction
                jurisdiction_fees[jurisdiction] += fee

    if unknown_jurisdictions:
        logger.error(
            'Unknown jurisdictions found in transactions.',
            jurisdictions=list(unknown_jurisdictions),
            compact=compact_config.compact_name,
        )
        # we can still generate the reports, but we need to add this so an exception is thrown after sending the reports
        lambda_error_messages.append(
            f'Unknown jurisdictions found in transactions. Jurisdictions: {unknown_jurisdictions}'
        )

    # Generate CSV
    output = StringIO()
    writer = csv.writer(output, lineterminator='\n', dialect='excel')
    writer.writerow(['Total Transactions', len(transactions)])
    writer.writerow(['Total Compact Fees', f'${compact_fees:.2f}'])

    for jurisdiction in jurisdiction_configs:
        postal = jurisdiction['postalAbbreviation'].lower()
        fee_value = jurisdiction_fees.get(postal, 0)
        writer.writerow([f'State Fees ({jurisdiction["jurisdictionName"].capitalize()})', f'${fee_value:.2f}'])
    for jurisdiction in unknown_jurisdictions:
        writer.writerow([f'State Fees (UNKNOWN ({jurisdiction}))', f'${jurisdiction_fees[jurisdiction]:.2f}'])

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
            'Transaction Date',
            'State',
            'State Fee',
            'Compact Fee',
            'Transaction Id',
        ]
    )

    if not transactions:
        writer.writerow(['No transactions for this period'] + [''] * 7)
        return output.getvalue()

    for transaction in transactions:
        provider = providers.get(transaction['licenseeId'], {})
        transaction_date = datetime.fromisoformat(transaction['batch']['settlementTimeUTC']).strftime('%m-%d-%Y')
        compact_fee_item = next(item for item in transaction['lineItems'] if item['itemId'].endswith('-compact-fee'))

        # Write a row for each state privilege in the transaction
        for item in transaction['lineItems']:
            if item['itemId'].endswith('-compact-fee'):
                continue

            # Extract state from itemId (format: compact-state)
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
            if item['itemId'].endswith('-compact-fee'):
                continue

            state = item['itemId'].split('-')[1]
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
                'Transaction Date',
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

            total_privileges += float(item['quantity'])
            total_amount += float(item['unitPrice']) * float(item['quantity'])

        # Add summary rows
        writer.writerow([''] * 8)
        writer.writerow(['Privileges Purchased', 'Total State Amount'] + [''] * 6)
        writer.writerow([int(total_privileges), f'${total_amount:.2f}'] + [''] * 6)

        reports[jurisdiction] = output.getvalue()

    return reports
