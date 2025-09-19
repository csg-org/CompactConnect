# Cloudfront Viewer Response Edge Lambda

## Table of Contents
- **[Prerequisites](#prerequisites)**
- **[Installing dependencies](#installing-dependencies)**
- **[Local development](#local-development)**
- **[Tests](#tests)**

---
## Prerequisites
* **[Node](https://github.com/creationix/nvm#installation) `22.X`**
* **[Yarn](https://yarnpkg.com/en/) `1.22.22`**
    * `npm install --global yarn@1.22.22`
* **[Mocha](https://mochajs.org/) `10.x.x`+**
    * Check if already installed: `mocha --version`
    * `npm install --g mocha@10`

_[back to top](#cloudfront-csp-header-edge-lambda)_

---
## Installing dependencies
- `yarn install`

_Currently there are no production dependencies that require build bundling. There are only development dependencies needed for local development tooling._

_[back to top](#cloudfront-csp-header-edge-lambda)_

---
## Local development
- **Linting**
    - `yarn run grunt`
        - This lints all code in all the Lambda function + watches locally for changes
- **Running an individual Lambda**
    - The easiest way to execute the Lambda is to run the tests ([see below](#tests))
        - Commenting out certain tests to limit the execution scope & repetition is trivial

_[back to top](#cloudfront-csp-header-edge-lambda)_

---
## Tests
- `yarn test`

#### Test output verbosity
- `index.test.js`
    - In individual test blocks (e.g. `it()`) you can update the output verbosity in the options passed to `lambdaConfig()`
    - Examples:
        - `config.verboseLevel = 3`
        - ```
          const config = lambdaConfig({
              ...
              verboseLevel: 3,
          });
          ```
        - _(options are [0-3](https://github.com/ashiina/lambda-local#lambdalocalexecuteoptions))_
