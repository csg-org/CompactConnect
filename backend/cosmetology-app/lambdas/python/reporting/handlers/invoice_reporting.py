"""Generate monthly cosmetology invoices.

This follows the compact-connect transaction report split. This Lambda queries license
uploads, writes one zip of per-state CSVs to S3, and asks the Node email service to
attach that zip. It does not send mail itself.
"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Key
from cc_common.config import config, logger
from cc_common.exceptions import CCInternalException, CCNotFoundException
from invoice_report import (
    BILLING_MONTH,
    INVOICE_LICENSE_TYPES,
    indexed_licenses,
    invoice_filename,
    invoice_object_key,
    invoice_zip,
    jurisdiction_invoice,
    previous_billing_month,
    run_stamp,
    state_invoice_csv,
)

EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
BATCH_GET_LIMIT = 100
# UnprocessedKeys is retried with capped exponential backoff. Past this budget the run fails
# so a partial license fetch is never stored or emailed.
MAX_UNPROCESSED_RETRIES = 3
UNPROCESSED_BASE_SLEEP_SECONDS = 0.5
UNPROCESSED_MAX_SLEEP_SECONDS = 5


def generate_invoice_reports(event: dict, context: LambdaContext) -> dict:  # noqa: ARG001 unused-argument
    billing_month = _resolve_billing_month(event)
    recipient_email = _resolve_manual_recipient(event)
    generated_at = run_stamp(datetime.now(tz=UTC))
    sent = []

    for compact in config.compacts:
        try:
            compact_config = config.compact_configuration_client.get_compact_configuration(compact)
        except CCNotFoundException as error:
            logger.warning('Compact configuration not found, skipping compact', compact=compact, error=str(error))
            continue

        jurisdictions = _jurisdiction_configurations(compact)
        sections_by_license_type = {license_type: [] for license_type in INVOICE_LICENSE_TYPES}

        for jurisdiction in jurisdictions:
            postal = jurisdiction['postalAbbreviation']
            gsi_items = _query_upload_index(compact.lower(), postal.lower(), billing_month)
            records = _batch_get_licenses(_license_keys(compact.lower(), postal.lower(), gsi_items))
            records_by_key = {f'{record["pk"]}|{record["sk"]}': record for record in records if record.get('pk')}
            by_type, uploaded_by_type = jurisdiction_invoice(
                compact.lower(),
                postal.lower(),
                billing_month,
                gsi_items,
                records_by_key,
                _fee_per_license(),
            )
            for license_type in INVOICE_LICENSE_TYPES:
                sections_by_license_type[license_type].append(
                    {
                        'jurisdictionName': jurisdiction['jurisdictionName'],
                        'postalAbbreviation': postal,
                        'lineItems': by_type.get(license_type, []),
                        'totalUploaded': uploaded_by_type.get(license_type, 0),
                    }
                )

        for license_type, sections in sections_by_license_type.items():
            line_items = [item for section in sections for item in section['lineItems']]
            total_uploaded = sum(section['totalUploaded'] for section in sections)
            total_billable = len(line_items)
            total_owed = sum(item['fee'] for item in line_items)
            entries = [
                (
                    invoice_filename(
                        license_type,
                        billing_month,
                        section['jurisdictionName'],
                        section['postalAbbreviation'],
                        generated_at,
                    ),
                    state_invoice_csv(section['jurisdictionName'], section['lineItems']),
                )
                for section in sections
            ]
            object_key = invoice_object_key(compact.lower(), license_type, billing_month, generated_at)
            # generated_at is in the key, so this run does not replace an earlier zip.
            config.s3_client.put_object(
                Bucket=config.invoice_reports_bucket_name,
                Key=object_key,
                Body=invoice_zip(entries),
                ContentType='application/zip',
            )
            try:
                config.email_service_client.send_compact_invoice_email(
                    compact=compact,
                    report_s3_path=object_key,
                    license_type=license_type,
                    billing_month=billing_month,
                    total_billable=total_billable,
                    total_owed=total_owed,
                    recipient_email=recipient_email,
                )
            except CCInternalException:
                logger.error(
                    'Failed to send invoice email after storing the report',
                    compact=compact,
                    license_type=license_type,
                    billing_month=billing_month,
                    report_s3_path=object_key,
                )
                raise
            logger.info(
                'Sent invoice email',
                compact=compact_config.compactAbbr,
                license_type=license_type,
                billing_month=billing_month,
                total_uploaded=total_uploaded,
                total_billable=total_billable,
                total_owed=total_owed,
                report_s3_path=object_key,
            )
            sent.append(object_key)

    return {'message': 'Invoice reports sent', 'reportS3Paths': sent}


def _resolve_billing_month(event: dict) -> str:
    billing_month = event.get('billingMonth')
    if billing_month is None:
        return previous_billing_month(datetime.now(tz=UTC))
    if not BILLING_MONTH.fullmatch(billing_month):
        raise ValueError(f'billingMonth must be YYYY-MM, got {billing_month}')
    return billing_month


def _resolve_manual_recipient(event: dict) -> str | None:
    if event.get('eventType') != 'manual':
        return None
    email = (event.get('recipientEmail') or '').strip()
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError(f'Manual invoice runs require a recipientEmail, got {event.get("recipientEmail") or ""}')
    return email


def _fee_per_license() -> int:
    raw = config.fee_per_license
    try:
        return int(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f'Invalid FEE_PER_LICENSE: {raw}') from error


def _jurisdiction_configurations(compact: str) -> list[dict]:
    jurisdictions = []
    query_kwargs = {
        'KeyConditionExpression': Key('pk').eq(f'{compact}#CONFIGURATION')
        & Key('sk').begins_with(f'{compact}#JURISDICTION#'),
    }
    while True:
        response = config.compact_configuration_table.query(**query_kwargs)
        for item in response.get('Items', []):
            name = item.get('jurisdictionName')
            postal = item.get('postalAbbreviation')
            if name and postal:
                jurisdictions.append({'jurisdictionName': name, 'postalAbbreviation': postal})
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            return jurisdictions
        query_kwargs['ExclusiveStartKey'] = last_key


def _query_upload_index(compact: str, jurisdiction: str, billing_month: str) -> list[dict]:
    partition_key = f'C#{compact}#J#{jurisdiction}#D#{billing_month}'
    logger.info(
        'Querying license uploads for invoice',
        compact=compact,
        jurisdiction=jurisdiction,
        billing_month=billing_month,
        partition_key=partition_key,
    )
    items = []
    query_kwargs = {
        'IndexName': config.license_upload_date_invoice_index_name,
        'KeyConditionExpression': Key('licenseUploadDateGSIPK').eq(partition_key),
    }
    while True:
        response = config.provider_table.query(**query_kwargs)
        items.extend(response.get('Items', []))
        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            return items
        query_kwargs['ExclusiveStartKey'] = last_key


def _license_keys(compact: str, jurisdiction: str, gsi_items: list[dict]) -> list[dict]:
    return [indexed['key'] for indexed in indexed_licenses(compact, jurisdiction, gsi_items)]


def _batch_get_licenses(keys: list[dict]) -> list[dict]:
    if not keys:
        return []
    table_name = config.provider_table_name
    dynamodb = boto3.resource('dynamodb')
    records = []
    for offset in range(0, len(keys), BATCH_GET_LIMIT):
        pending = keys[offset : offset + BATCH_GET_LIMIT]
        attempt = 0
        while pending:
            if attempt:
                time.sleep(min(UNPROCESSED_BASE_SLEEP_SECONDS * (2 ** (attempt - 1)), UNPROCESSED_MAX_SLEEP_SECONDS))
            response = dynamodb.batch_get_item(RequestItems={table_name: {'Keys': pending}})
            records.extend(response.get('Responses', {}).get(table_name, []))
            pending = response.get('UnprocessedKeys', {}).get(table_name, {}).get('Keys', [])
            if not pending:
                break
            attempt += 1
            if attempt > MAX_UNPROCESSED_RETRIES:
                logger.error(
                    'License batch get left keys unprocessed',
                    unprocessed_key_count=len(pending),
                    retries=MAX_UNPROCESSED_RETRIES,
                )
                raise CCInternalException('Failed to load all licenses for the invoice after retrying unprocessed keys')
    return records
