import { InvoiceLineItem, InvoiceReport, StateInvoiceSection } from '../models/invoice';
import { BaseEmailService } from './base-email-service';

const MONTH_NAMES = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
] as const;

const CSV_HEADERS = [
    'Jurisdiction',
    'First Name',
    'Last Name',
    'Home State',
    'License Number',
    'Category',
    'Fee',
];

export class InvoiceEmailService extends BaseEmailService {
    public generateStateInvoiceCsv(section: StateInvoiceSection): string {
        const rows: string[][] = [CSV_HEADERS];

        for (const item of section.lineItems) {
            rows.push(this.lineItemRow(section, item));
        }

        const owed = section.lineItems.reduce((sum, item) => sum + item.fee, 0);

        rows.push([]);
        rows.push(['Total Uploaded', String(section.totalUploaded)]);
        rows.push(['Total Billable', String(section.lineItems.length)]);
        rows.push(['Total Owed', formatCurrency(owed)]);

        return `${rows.map((row) => row.map(csvCell).join(',')).join('\n')}\n`;
    }

    public invoiceAttachments(report: InvoiceReport): { filename: string; content: string; contentType: string }[] {
        return report.stateSections.map((section) => ({
            filename: invoiceFilename(report, section),
            content: this.generateStateInvoiceCsv(section),
            contentType: 'text/csv',
        }));
    }

    public async sendInvoiceEmail(report: InvoiceReport, recipients: string[]): Promise<string> {
        this.logger.info('Sending invoice email', {
            recipients: this.maskEmails(recipients),
            licenseType: report.licenseType,
            billingMonth: report.billingMonth,
            totalUploaded: report.totalUploaded,
            totalBillable: report.totalBillable,
            totalOwed: report.totalOwed,
        });

        const template = this.getNewEmailTemplate();
        const subject = invoiceSubject(report);

        this.insertHeader(template, subject);
        this.insertBody(template, invoiceBody(report), 'left');
        this.insertFooter(template);

        const messageId = await this.sendEmailWithAttachments({
            htmlContent: this.renderTemplate(template),
            subject,
            recipients,
            errorMessage: 'Error sending invoice email',
            attachments: this.invoiceAttachments(report),
        });

        if (!messageId) {
            throw new Error('Invoice email was accepted without a message id');
        }

        return messageId;
    }

    private lineItemRow(section: StateInvoiceSection, item: InvoiceLineItem): string[] {
        return [
            section.jurisdictionName,
            item.givenName,
            item.familyName,
            item.homeState,
            item.licenseNumber,
            item.category === 'new' ? 'New' : 'Renewal',
            formatCurrency(item.fee),
        ];
    }
}

export function formatBillingMonth(billingMonth: string): string {
    const [year, month] = billingMonth.split('-').map(Number);

    return `${MONTH_NAMES[month - 1]} ${year}`;
}

export function formatLicenseType(licenseType: string): string {
    return licenseType.charAt(0).toUpperCase() + licenseType.slice(1);
}

export function invoiceSubject(report: InvoiceReport): string {
    const licenseLabel = formatLicenseType(report.licenseType);

    return `Monthly ${licenseLabel} Invoice for ${report.compactName} Compact`;
}

export function invoiceBody(report: InvoiceReport): string {
    const licenseLabel = formatLicenseType(report.licenseType);
    const monthLabel = formatBillingMonth(report.billingMonth);

    return `Please find attached the monthly ${licenseLabel} invoices for the ${report.compactName} Compact for ${monthLabel}. `
        + `Uploaded licenses: ${report.totalUploaded}. Billable licenses: ${report.totalBillable}. `
        + `Total owed: ${formatCurrency(report.totalOwed)}.`;
}

export function invoiceFilename(report: InvoiceReport, section: StateInvoiceSection): string {
    return `${stateSlug(section)}-${report.licenseType}-invoice-${report.billingMonth}.csv`;
}

function stateSlug(section: StateInvoiceSection): string {
    const slug = section.jurisdictionName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

    return slug || section.postalAbbreviation.toLowerCase();
}

function formatCurrency(amount: number): string {
    return `$${amount.toFixed(2)}`;
}

// Spreadsheet apps execute a cell that starts with one of these as a formula.
// A leading apostrophe forces the cell to be read as text. See OWASP CSV Injection.
const SPREADSHEET_FORMULA_START = /^[-+=@\t\r\n\uFF1D\uFF0B\uFF0D\uFF20]/;

function csvCell(value: string): string {
    const text = SPREADSHEET_FORMULA_START.test(value) ? `'${value}` : value;

    if (/[",\r\n]/.test(text)) {
        return `"${text.replace(/"/g, '""')}"`;
    }

    return text;
}
