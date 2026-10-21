import { InvoiceLineItem, InvoiceReport, StateInvoiceSection } from '../models/invoice';
import { BaseEmailService } from './base-email-service';

const BILLING_MONTH_FORMAT = new Intl.DateTimeFormat('en-US', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
});

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
    public generateInvoiceCsv(report: InvoiceReport): string {
        const rows: string[][] = [CSV_HEADERS];

        for (const section of report.stateSections) {
            for (const item of section.lineItems) {
                rows.push(this.lineItemRow(section, item));
            }
        }

        rows.push([]);
        rows.push(['Jurisdiction', 'Licenses', 'Amount Owed']);
        for (const section of report.stateSections) {
            const owed = section.lineItems.reduce((sum, item) => sum + item.fee, 0);

            rows.push([
                section.jurisdictionName,
                String(section.lineItems.length),
                formatCurrency(owed),
            ]);
        }

        rows.push([]);
        rows.push(['Total Uploaded', String(report.totalUploaded)]);
        rows.push(['Total Billable', String(report.totalBillable)]);
        rows.push(['Total Owed', formatCurrency(report.totalOwed)]);

        return `${rows.map((row) => row.map(csvCell).join(',')).join('\n')}\n`;
    }

    public async sendInvoiceEmail(report: InvoiceReport, recipients: string[]): Promise<string> {
        this.logger.info('Sending invoice email', {
            recipients: this.maskEmails(recipients),
            licenseType: report.licenseType,
            billingMonth: report.billingMonth,
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
            attachments: [
                {
                    filename: invoiceFilename(report),
                    content: this.generateInvoiceCsv(report),
                    contentType: 'text/csv',
                },
            ],
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

    return BILLING_MONTH_FORMAT.format(new Date(Date.UTC(year, month - 1, 1)));
}

export function formatLicenseType(licenseType: string): string {
    return licenseType.charAt(0).toUpperCase() + licenseType.slice(1);
}

export function invoiceSubject(report: InvoiceReport): string {
    const licenseLabel = formatLicenseType(report.licenseType);

    return `Monthly ${licenseLabel} Invoice for ${report.compactName}`;
}

export function invoiceBody(report: InvoiceReport): string {
    const licenseLabel = formatLicenseType(report.licenseType);
    const monthLabel = formatBillingMonth(report.billingMonth);

    return `Please find attached the monthly ${licenseLabel} invoice for the ${report.compactName} for ${monthLabel}.`;
}

export function invoiceFilename(report: InvoiceReport): string {
    return `${report.licenseType}-invoice-${report.billingMonth}.csv`;
}

function formatCurrency(amount: number): string {
    return `$${amount.toFixed(2)}`;
}

function csvCell(value: string): string {
    if (/[",\n]/.test(value)) {
        return `"${value.replace(/"/g, '""')}"`;
    }

    return value;
}
