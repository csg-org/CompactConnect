# Email Notification Service Lambda

This package contains code required to generate system emails for users in compact connect, as well as
compacts/jurisdictions staff. It leverages [EmailBuilderJS](https://github.com/usewaypoint/email-builder-js) to dynamically render email HTML content that should
be rendered consistently across email clients.

The lambda is intended to be invoked directly, rather than through an API endpoint. It uses the following payload structure:
```
{
  template: string;           // Name of the template to use (ie transactionBatchSettlementFailure)
  recipientType: // must be one of the following
    | 'COMPACT_OPERATIONS_TEAM'              // compactOperationsTeamEmails
    | 'COMPACT_ADVERSE_ACTIONS'              // compactAdverseActionsNotificationEmails
    | 'COMPACT_SUMMARY_REPORT'               // compactSummaryReportNotificationEmails
    | 'JURISDICTION_OPERATIONS_TEAM'         // jurisdictionOperationsTeamEmails
    | 'JURISDICTION_ADVERSE_ACTIONS'         // jurisdictionAdverseActionsNotificationEmails
    | 'JURISDICTION_SUMMARY_REPORT'          // jurisdictionSummaryReportNotificationEmails
    | 'SPECIFIC';                           // specificEmails provided in payload
  compact: string;           // Compact identifier
  jurisdiction?: string;     // Optional jurisdiction identifier, must be specified if sending to a Jurisdiction based email list
  specificEmails?: string[]; // Optional list of specific email addresses to send the message to
  templateVariables: {              // Template variables for hydration
    [key: string]: any;
  };
}
```

This schema provides flexibility for adding new notification template types. Each template type corresponds to a
particular method in the `EmailServiceTemplater` class. The `recipientType` field is used to determine which email addresses to
send the email to, and correspond to email lists defined in the compact/jurisdiction configurations used by the system.
The `specificEmails` field is used to send the email to a specific list of email addresses, and is only used when
`recipientType` is set to `SPECIFIC`. The `templateVariables` field is used to hydrate the email template with dynamic content.
if needed.
