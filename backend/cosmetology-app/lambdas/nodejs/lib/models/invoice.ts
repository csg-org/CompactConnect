export type InvoiceCategory = 'new' | 'renewal';

export interface InvoiceLineItem {
    givenName: string;
    familyName: string;
    homeState: string;
    licenseNumber: string;
    licenseType: string;
    category: InvoiceCategory;
    fee: number;
}

export interface StateInvoiceSection {
    jurisdictionName: string;
    postalAbbreviation: string;
    lineItems: InvoiceLineItem[];
    /** Licenses uploaded this month for this state and license type, including ones that are not billable. */
    totalUploaded: number;
}

export interface InvoiceReport {
    compactName: string;
    licenseType: string;
    billingMonth: string;
    stateSections: StateInvoiceSection[];
    totalUploaded: number;
    totalBillable: number;
    totalOwed: number;
}

export interface LicenseUploadsForMonth {
    lineItems: InvoiceLineItem[];
    /** Index hits for the jurisdiction, across every license type. */
    totalUploaded: number;
    byLicenseType: Record<string, InvoiceLineItem[]>;
    /** Unique licenses per type, including uploads that produced no billable line item. */
    uploadedByLicenseType: Record<string, number>;
}

export interface InvoiceReporterEvent {
    eventType: 'monthly' | 'manual';
    billingMonth?: string;
    /** Manual runs only. Monthly runs always use the compact operations team. */
    recipientEmail?: string;
}
