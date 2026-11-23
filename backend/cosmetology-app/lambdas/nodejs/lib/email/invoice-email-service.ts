import { InvoiceReport } from '../models/invoice';

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
        + `Billable licenses: ${report.totalBillable}. `
        + `Total owed: ${formatCurrency(report.totalOwed)}.`;
}

function formatCurrency(amount: number): string {
    return `$${amount.toFixed(2)}`;
}
