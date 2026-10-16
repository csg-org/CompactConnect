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
    totalUploaded: number;
    byLicenseType: Record<string, InvoiceLineItem[]>;
}

export interface InvoiceReporterEvent {
    eventType: 'monthly' | 'manual';
    billingMonth?: string;
}
