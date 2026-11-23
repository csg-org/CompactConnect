import { formatBillingMonth, invoiceBody, invoiceSubject } from '../../../lib/email/invoice-email-service';
import { InvoiceReport } from '../../../lib/models/invoice';

const report = (): InvoiceReport => ({
    compactName: 'Cosmetology',
    licenseType: 'cosmetologist',
    billingMonth: '2024-09',
    totalBillable: 3,
    totalOwed: 75,
});

describe('invoice email copy', () => {
    it('should format YYYY-MM as an English month and year', () => {
        expect(formatBillingMonth('2024-09')).toEqual('September 2024');
    });

    it('should set the subject from the license type and compact', () => {
        expect(invoiceSubject(report())).toEqual('Monthly Cosmetologist Invoice for Cosmetology Compact');
    });

    it('should describe the billing month, billable count, and amount owed', () => {
        expect(invoiceBody(report())).toEqual(
            'Please find attached the monthly Cosmetologist invoices for the Cosmetology Compact for September 2024. '
            + 'Billable licenses: 3. Total owed: $75.00.'
        );
    });
});
