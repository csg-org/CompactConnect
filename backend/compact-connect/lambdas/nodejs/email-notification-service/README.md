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


## Table of Contents
- **[Prerequisites](#prerequisites)**
- **[Installing dependencies](#installing-dependencies)**
- **[Bundling the runtime](#bundling-the-runtime)**
- **[Local development](#local-development)**
- **[Tests](#tests)**

---
## Prerequisites
* **[Node](https://github.com/creationix/nvm#installation) `22.X`**
* **[Yarn](https://yarnpkg.com/en/) `1.22.22`**
    * `npm install --global yarn@1.22.22`

_[back to top](#ingest-event-reporter-lambda)_

---
## Installing dependencies
- `yarn install`

## Bundling the runtime
- `yarn build`

_[back to top](#ingest-event-reporter-lambda)_

---
## Local development
- **Linting**
    - `yarn run lint`
        - Lints all code in all the Lambda function
- **Running an individual Lambda**
    - The easiest way to execute the Lambda is to run the tests ([see below](#tests))
        - Commenting out certain tests to limit the execution scope & repetition is trivial

_[back to top](#ingest-event-reporter-lambda)_

---
## Tests
This project uses `jest` and `aws-sdk-client-mock` for approachable unit testing. To run the included test:

- `yarn test`

This lambda module requires >90% code coverage and >90% code _branch_ coverage. Be sure that all contributions are
covered with tests accordingly.
