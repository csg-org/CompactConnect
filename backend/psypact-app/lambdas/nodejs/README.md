# NodeJS Lambdas

This folder contains all lambda runtimes that are written with NodeJS/TypeScript. Because these lambdas are each bundled through CDK with ESBuild, we can pull common code and tests together, leaving only the entrypoints in a lambda-specific folder, leaving ESBuild to pull in only needed lib code.


## Prerequisites
* **[Node](https://github.com/creationix/nvm#installation) `24.X`**
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
## Testing
This project uses `jest` and `aws-sdk-client-mock` for approachable unit testing. The code in this folder can be tested by running:
- `yarn install`
- `yarn test`

or by using the utility scripts located at `backend/bin`.
