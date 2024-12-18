# Ingest Event Reporter Lambda

This package contains code required to generate emailed reports for compacts/jurisdictions. It leverages
[EmailBuilderJS](https://github.com/usewaypoint/email-builder-js) to dynamically render email
HTML content that should be rendered consistently across email clients.

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
