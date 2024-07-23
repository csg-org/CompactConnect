# Cloudfront CSP Header Edge Lambda

## Table of Contents
- **[Prerequisites](#prerequisites)**
- **[Installing dependencies](#installing-dependencies)**
- **[Local development](#local-development)**
- **[Tests](#tests)**

---
## Prerequisites
* **[Node](https://github.com/creationix/nvm#installation) `20.15.1`**
* **[Yarn](https://yarnpkg.com/en/) `1.22.22`**
    * `npm install --global yarn@1.22.22`
* **[Grunt](http://gruntjs.com/)**
    * Check if already installed: `grunt --version`
    * To install Grunt run: `npm install -g grunt-cli`
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
    - `grunt`
        - This lints all code in all the Lambda function + watches locally for changes
- **Running an individual Lambda**
    - The easiest way to execute the Lambda is to run the tests ([see below](#tests))
        - Commenting out certain tests to limit the execution scope & repetition is trivial

_[back to top](#cloudfront-csp-header-edge-lambda)_

---
## Tests
- `npm test`

#### Test output verbosity
- `index.test.js`
    - Test block `it()`
        - `config.verboseLevel = 3` _(options are [0-3](https://github.com/ashiina/lambda-local#lambdalocalexecuteoptions))_
