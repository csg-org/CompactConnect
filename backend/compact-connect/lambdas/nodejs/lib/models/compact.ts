export interface CompactCommissionFee {
    feeAmount: number;
    feeType: string;
}

export interface Compact {
    pk: string;
    sk: string;
    compactAdverseActionsNotificationEmails: string[];
    compactCommissionFee: CompactCommissionFee;
    compactName: string;
    compactOperationsTeamEmails: string[];
    compactSummaryReportNotificationEmails: string[];
    dateOfUpdate: string;
    type: string;
}
