import { InvoiceLineItem, InvoiceReport, StateInvoiceSection } from '../models/invoice';
import { BaseEmailService } from './base-email-service';

const BILLING_MONTH_FORMAT = new Intl.DateTimeFormat('en-US', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
});

export class InvoiceEmailService extends BaseEmailService {
    public generateInvoiceHtml(report: InvoiceReport): string {
        const licenseLabel = formatLicenseType(report.licenseType);
        const monthLabel = formatBillingMonth(report.billingMonth);
        const sections = report.stateSections.map((section) => this.renderStateSection(section)).join('\n');

        return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>${escapeHtml(licenseLabel)} Invoice — ${escapeHtml(monthLabel)}</title>
</head>
<body>
<h1>${escapeHtml(report.compactName)} ${escapeHtml(licenseLabel)} Invoice — ${escapeHtml(monthLabel)}</h1>
${sections}
<p>Total uploaded: ${report.totalUploaded}</p>
<p>Total billable: ${report.totalBillable}</p>
<p>Total owed to ${escapeHtml(report.compactName)}: ${formatCurrency(report.totalOwed)}</p>
</body>
</html>`;
    }

    public async sendInvoiceEmail(report: InvoiceReport, recipients: string[]): Promise<string> {
        this.logger.info('Sending invoice email', {
            recipients: this.maskEmails(recipients),
            licenseType: report.licenseType,
            billingMonth: report.billingMonth,
            totalBillable: report.totalBillable,
            totalOwed: report.totalOwed,
        });

        const messageId = await this.sendEmail({
            htmlContent: this.generateInvoiceHtml(report),
            subject: invoiceSubject(report),
            recipients,
            errorMessage: 'Error sending invoice email',
        });

        if (!messageId) {
            throw new Error('Invoice email was accepted without a message id');
        }

        return messageId;
    }

    private renderStateSection(section: StateInvoiceSection): string {
        const rows = section.lineItems.map((item) => this.renderLineItem(item)).join('\n');
        const count = section.lineItems.length;
        const owed = section.lineItems.reduce((sum, item) => sum + item.fee, 0);
        const licenseWord = count === 1 ? 'license' : 'licenses';
        const postal = section.postalAbbreviation.toUpperCase();

        return `<h2>${escapeHtml(section.jurisdictionName)} (${escapeHtml(postal)})</h2>
<table>
<thead>
<tr><th>Name</th><th>Home state</th><th>License number</th><th>Category</th><th>Fee</th></tr>
</thead>
<tbody>
${rows}
</tbody>
</table>
<p>${count} ${licenseWord} — ${formatCurrency(owed)} owed</p>`;
    }

    private renderLineItem(item: InvoiceLineItem): string {
        const category = item.category === 'new' ? 'New' : 'Renewal';

        return `<tr>
<td>${escapeHtml(`${item.givenName} ${item.familyName}`)}</td>
<td>${escapeHtml(item.homeState)}</td>
<td>${escapeHtml(item.licenseNumber)}</td>
<td>${category}</td>
<td>${formatCurrency(item.fee)}</td>
</tr>`;
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
    const monthLabel = formatBillingMonth(report.billingMonth);

    return `[${report.compactName}] ${licenseLabel} Invoice — ${monthLabel}`;
}

function formatCurrency(amount: number): string {
    return `$${amount.toFixed(2)}`;
}

function escapeHtml(value: string): string {
    return value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
