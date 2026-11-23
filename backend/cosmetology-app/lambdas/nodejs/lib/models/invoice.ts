/** Fields the email service needs to describe a zip the Python reporter already stored. */
export interface InvoiceReport {
    compactName: string;
    licenseType: string;
    billingMonth: string;
    totalBillable: number;
    totalOwed: number;
}
