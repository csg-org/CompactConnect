export interface IJurisdiction {
    pk: string;
    sk: string;

    jurisdictionName: string;
    postalAbbreviation: string;
    compact: string;
    jurisdictionOperationsTeamEmails: string[];
    jurisdictionAdverseActionsNotificationEmails: string[];
    jurisdictionSummaryReportNotificationEmails: string[];
}
