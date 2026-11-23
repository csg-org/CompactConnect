"""Build the cosmetology invoice CSVs and the zip stored for each license-type email.

Billing matches the previous Node invoice client. A license is new when its firstUploadDate
falls in the billing month. It is a renewal when a renewal upload was processed in that month
and it was not first uploaded then. dateOfRenewal is display-only. Upload Date is the upload
that caused the charge: firstUploadDate for a new license, otherwise the earliest renewal
upload in the billing month.
"""

from __future__ import annotations

import io
import re
from datetime import UTC, date, datetime
from zipfile import ZIP_DEFLATED, ZipFile

INVOICE_LICENSE_TYPES = ('cosmetologist', 'esthetician')
CSV_HEADERS = [
    'Jurisdiction',
    'First Name',
    'Last Name',
    'Home State',
    'License Number',
    'Category',
    'Upload Date',
    'Issuance Date',
    'Renewal Date',
    'Fee',
]
SPREADSHEET_FORMULA_START = re.compile(r'^[-+=@\t\r\n\uFF1D\uFF0B\uFF0D\uFF20]')
DATE_ONLY = re.compile(r'^\d{4}-\d{2}-\d{2}$')
BILLING_MONTH = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')
SORT_KEY_TIME = re.compile(r'^TIME#(\d+)#')
SORT_KEY_LICENSE_TYPE = re.compile(r'#LT#([^#]+)#PID#')
SORT_KEY_PROVIDER = re.compile(r'#PID#(.+)$')


def previous_billing_month(now: datetime) -> str:
    """The calendar month before now, in UTC."""
    year = now.astimezone(UTC).year
    month = now.astimezone(UTC).month - 1
    if month == 0:
        month = 12
        year -= 1
    return f'{year:04d}-{month:02d}'


def calendar_date(value: object) -> str | None:
    """Date-only values stay as YYYY-MM-DD. Timestamps use the UTC calendar date."""
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).strftime('%Y-%m-%d')
    if isinstance(value, date):
        return value.isoformat()

    text = str(value)
    if DATE_ONLY.fullmatch(text):
        return text
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed.astimezone(UTC).strftime('%Y-%m-%d')


def is_in_billing_month(value: object, billing_month: str) -> bool:
    rendered = calendar_date(value)
    return bool(rendered and rendered.startswith(billing_month))


def run_stamp(now: datetime) -> str:
    """UTC date and time this report was generated, safe to put in a file name."""
    return now.astimezone(UTC).strftime('%Y-%m-%dT%H%M%SZ')


def invoice_object_key(compact: str, license_type: str, billing_month: str, generated_at: str) -> str:
    """One object per license type, billing month, and run.

    generated_at is the UTC stamp from run_stamp. A later run of the same month writes a new
    key, so the zip that was emailed is left in place. After a license-upload rollback, run
    the invoice again and diff that new zip with the one that was emailed.
    """
    year, month = billing_month.split('-')
    filename = f'{license_type}-{billing_month}-invoice-run-{generated_at}.zip'
    return (
        f'compact/{compact}/reports/invoices/license-type/{license_type}/{year}/{month}/{filename}'
    )


def state_slug(jurisdiction_name: str, postal_abbreviation: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', jurisdiction_name.lower()).strip('-')
    return slug or postal_abbreviation.lower()


def invoice_filename(
    license_type: str,
    billing_month: str,
    jurisdiction_name: str,
    postal_abbreviation: str,
    generated_at: str,
) -> str:
    """State CSV name. The billing month and the run stamp are both in the name."""
    slug = state_slug(jurisdiction_name, postal_abbreviation)
    return f'{slug}-{license_type}-invoice-{billing_month}-run-{generated_at}.csv'


def _category(record: dict, billing_month: str, renewal_uploaded: bool) -> str | None:
    if is_in_billing_month(record.get('firstUploadDate'), billing_month):
        return 'new'
    if renewal_uploaded:
        return 'renewal'
    return None


def line_item(
    record: dict,
    jurisdiction: str,
    billing_month: str,
    renewal_uploaded: bool,
    fee: int,
    renewal_uploaded_at: object = None,
) -> dict | None:
    if record.get('jurisdictionUploadedCompactEligibility') != 'eligible':
        return None
    category = _category(record, billing_month, renewal_uploaded)
    if not category or not record.get('licenseType') or not record.get('licenseNumber'):
        return None
    # A first upload in the month is the charge. A later renewal in that month does not replace it.
    if category == 'new':
        upload_date = calendar_date(record.get('firstUploadDate'))
    else:
        upload_date = calendar_date(renewal_uploaded_at)
    return {
        'givenName': record.get('givenName') or '',
        'familyName': record.get('familyName') or '',
        'homeState': str(record.get('jurisdiction') or jurisdiction).upper(),
        'licenseNumber': record['licenseNumber'],
        'licenseType': record['licenseType'],
        'category': category,
        'uploadDate': upload_date,
        'issuanceDate': calendar_date(record.get('dateOfIssuance')),
        'renewalDate': calendar_date(record.get('dateOfRenewal')) if category == 'renewal' else None,
        'fee': fee,
    }


def indexed_licenses(compact: str, jurisdiction: str, gsi_items: list[dict]) -> list[dict]:
    """Collapse index hits to one license.

    A renewal upload on any hit marks the license renewed. renewalUploadedAt is the earliest
    renewal upload in the month, taken from the index sort key the query already returned.
    """
    indexed: dict[str, dict] = {}
    for item in gsi_items:
        sort_key = item.get('licenseUploadDateGSISK') or ''
        provider_id = item.get('providerId') or _provider_id_from_sort_key(sort_key)
        license_type_abbr = _license_type_abbr_from_sort_key(sort_key)
        if not provider_id or not license_type_abbr:
            continue
        key = {
            'pk': f'{compact}#PROVIDER#{provider_id}',
            'sk': f'{compact}#PROVIDER#license/{jurisdiction}/{license_type_abbr}#',
        }
        key_id = f'{key["pk"]}|{key["sk"]}'
        renewal_uploaded = item.get('updateType') == 'renewal'
        renewal_uploaded_at = _upload_time_from_sort_key(sort_key) if renewal_uploaded else None
        existing = indexed.get(key_id)
        if existing:
            existing['renewalUploaded'] = existing['renewalUploaded'] or renewal_uploaded
            existing['renewalUploadedAt'] = _earliest(existing.get('renewalUploadedAt'), renewal_uploaded_at)
            continue
        indexed[key_id] = {
            'key': key,
            'renewalUploaded': renewal_uploaded,
            'renewalUploadedAt': renewal_uploaded_at,
        }
    return list(indexed.values())


def jurisdiction_invoice(
    compact: str,
    jurisdiction: str,
    billing_month: str,
    gsi_items: list[dict],
    records_by_key: dict[str, dict],
    fee: int,
) -> tuple[dict[str, list[dict]], dict[str, int]]:
    """Billable lines and upload counts, grouped by the license type on the license record."""
    by_license_type: dict[str, list[dict]] = {}
    uploaded_by_license_type: dict[str, int] = {}
    for indexed in indexed_licenses(compact, jurisdiction, gsi_items):
        key = indexed['key']
        record = records_by_key.get(f'{key["pk"]}|{key["sk"]}')
        if record and record.get('licenseType'):
            license_type = record['licenseType']
            uploaded_by_license_type[license_type] = uploaded_by_license_type.get(license_type, 0) + 1
        item = (
            line_item(
                record,
                jurisdiction,
                billing_month,
                indexed['renewalUploaded'],
                fee,
                indexed.get('renewalUploadedAt'),
            )
            if record
            else None
        )
        if not item:
            continue
        by_license_type.setdefault(item['licenseType'], []).append(item)
    return by_license_type, uploaded_by_license_type


def format_currency(amount: int | float) -> str:
    return f'${amount:.2f}'


def _csv_cell(value: str) -> str:
    text = f"'{value}" if SPREADSHEET_FORMULA_START.match(value) else value
    if re.search(r'[",\r\n]', text):
        return f'"{text.replace(chr(34), chr(34) * 2)}"'
    return text


def state_invoice_csv(jurisdiction_name: str, line_items: list[dict]) -> str:
    rows: list[list[str]] = [CSV_HEADERS]
    for item in line_items:
        rows.append(
            [
                jurisdiction_name,
                item['givenName'],
                item['familyName'],
                item['homeState'],
                item['licenseNumber'],
                'New' if item['category'] == 'new' else 'Renewal',
                item.get('uploadDate') or '',
                item.get('issuanceDate') or '',
                item.get('renewalDate') or '',
                format_currency(item['fee']),
            ]
        )
    owed = sum(item['fee'] for item in line_items)
    rows.append([])
    rows.append(['Total Billable', str(len(line_items))])
    rows.append(['Total Owed', format_currency(owed)])
    return ''.join(f'{",".join(_csv_cell(cell) for cell in row)}\n' for row in rows)


def invoice_zip(entries: list[tuple[str, str]]) -> bytes:
    """entries are (filename, csv text)."""
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w', compression=ZIP_DEFLATED) as archive:
        for filename, content in entries:
            archive.writestr(filename, content.encode('utf-8'))
    return buffer.getvalue()


def _upload_time_from_sort_key(sort_key: str) -> datetime | None:
    """The TIME# epoch on an index hit is the upload that placed the row in this billing month."""
    match = SORT_KEY_TIME.match(sort_key)
    if not match:
        return None
    return datetime.fromtimestamp(int(match.group(1)), UTC)


def _earliest(current: datetime | None, candidate: datetime | None) -> datetime | None:
    if candidate is None:
        return current
    if current is None or candidate < current:
        return candidate
    return current


def _license_type_abbr_from_sort_key(sort_key: str) -> str | None:
    match = SORT_KEY_LICENSE_TYPE.search(sort_key)
    return match.group(1) if match else None


def _provider_id_from_sort_key(sort_key: str) -> str | None:
    match = SORT_KEY_PROVIDER.search(sort_key)
    return match.group(1) if match else None


def read_zip_entries(payload: bytes) -> dict[str, str]:
    with ZipFile(io.BytesIO(payload)) as archive:
        return {name: archive.read(name).decode('utf-8') for name in archive.namelist()}
