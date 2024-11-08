
# CompactConnect Frontend

## Table of Contents
- **[Key](#key)**
- **[Prerequisites](#prerequisites)**
- **[Environment Configuration](#environment-configuration)**
- **[Local Development](#local-development)**
- **[Tests](#tests)**
- **[Build](#build)**

---
## Key
- :arrow_heading_up: Server-hosted only
- :arrow_heading_down: Local development only

---
## Prerequisites
- **[Node](https://nodejs.org/) `22.1.0`**
    * Use **[NVM](https://github.com/creationix/nvm#installation)** to manage Node versions
    * The `curl`-based install script is typically all that's required
    * A brief overview of the [NVM Usage commands](https://github.com/nvm-sh/nvm#usage) is typically helpful
- **[Yarn](https://yarnpkg.com/en/) `1.22.x`**
    - `npm install --global yarn`

---
## Environment Configuration
### Environment variables
1. If you don't already have an `.env` file: :arrow_heading_down:
    - Copy the `.env.example` as `.env`
1. Adjust the values in `.env` as needed:
    - **`NODE_ENV`**
        - `production`: for all server environments :arrow_heading_up:
        - `development`: for local development :arrow_heading_down:
    - **`BASE_URL`**
        - `/` to serve under domain root
        - Otherwise, a relative path under the domain root; don't include trailing slash
    - **`VUE_APP_ROBOTS_META`**
        - _Server_ :arrow_heading_up:
            - Dev: `noindex,nofollow`
            - Test: `noindex,nofollow`
            - Prod: `nofollow`
        - _Local_ :arrow_heading_down:
            - `noindex,nofollow`
    - **`VUE_APP_DOMAIN`**
        - _Server_ :arrow_heading_up:
            - Dev: `https://app.test.jcc.iaapi.io`
            - Test: `https://app.test.compactconnect.org`
            - Prod: `https://app.compactconnect.org`
        - _Local_ :arrow_heading_down:
            - `http://localhost:3018`
    - **`VUE_APP_API_STATE_ROOT`**
        - _Server_ :arrow_heading_up:
            - Dev: `https://api.test.jcc.iaapi.io`
            - Test: `https://api.test.compactconnect.org`
            - Prod: `https://api.compactconnect.org`
        - _Local_ :arrow_heading_down:
            - `https://api.test.jcc.iaapi.io`
    - **`VUE_APP_API_LICENSE_ROOT`**
        - _Server_ :arrow_heading_up:
            - Dev: `https://api.test.jcc.iaapi.io`
            - Test: `https://api.test.compactconnect.org`
            - Prod: `https://api.compactconnect.org`
        - _Local_ :arrow_heading_down:
            - `https://api.test.jcc.iaapi.io`
    - **`VUE_APP_COGNITO_REGION`**
        - _Server_ :arrow_heading_up:
            - Dev: `us-east-1`
            - Test: `us-east-1`
            - Prod: `us-east-1`
        - _Local_ :arrow_heading_down:
            - `us-east-1`
    - **`VUE_APP_COGNITO_AUTH_DOMAIN_LICENSEE`**
        - _Server_ :arrow_heading_up:
            - Dev: `https://ia-cc-provider-test.auth.us-east-1.amazoncognito.com`
            - Test: `https://compact-connect-provider-test.auth.us-east-1.amazoncognito.com`
            - Prod: `https://compact-connect-provider.auth.us-east-1.amazoncognito.com`
        - _Local_ :arrow_heading_down:
            - `https://ia-cc-provider-test.auth.us-east-1.amazoncognito.com`
    - **`VUE_APP_COGNITO_CLIENT_ID_LICENSEE`**
        - _Server_ :arrow_heading_up:
            - Dev: `topd4vhftng5cfm3ccgkb6ejd`
            - Test: `6erj63mpa5tjqdtdi6vfi9q9hi`
            - Prod: `N/A`
        - _Local_ :arrow_heading_down:
            - `topd4vhftng5cfm3ccgkb6ejd`
    - **`VUE_APP_COGNITO_AUTH_DOMAIN_STAFF`**
        - _Server_ :arrow_heading_up:
            - Dev: `https://ia-cc-staff-test.auth.us-east-1.amazoncognito.com`
            - Test: `https://compact-connect-staff-test.auth.us-east-1.amazoncognito.com`
            - Prod: `https://compact-connect-staff.auth.us-east-1.amazoncognito.com`
        - _Local_ :arrow_heading_down:
            - `https://ia-cc-staff-test.auth.us-east-1.amazoncognito.com`
    - **`VUE_APP_COGNITO_CLIENT_ID_STAFF`**
        - _Server_ :arrow_heading_up:
            - Dev: `15mh24ea4af3of8jcnv8h2ic10`
            - Test: `75uq274pv8ufhc1g1h4n86gp1l`
            - Prod: `1qlqoaivpmosrdjbsi0u0nfkg4`
        - _Local_ :arrow_heading_down:
            - `15mh24ea4af3of8jcnv8h2ic10`
    - **`VUE_APP_MOCK_API`** :arrow_heading_down:
        - Only used for local development
        - `true` if mock API should be used
    - **`LOCAL_DEV_PORT`** :arrow_heading_down:
        - `3018`

### Server environment web server :arrow_heading_up:
- **Create a 404 rule that serves the `index.html` page**
    - This is common to modern "single-page-app" (SPA) frontends. It allows the frontend to serve up sub-page routes without the web server throwing a 404 first.
    - The frontend will handle 404 pages as needed
    - Apache example:
        - ```
          <Directory "<...path-to-frontend-dist...>/">
              ...
              FallbackResource /index.html
          </Directory>

          ### Also, omit any other 404 handlers, such as:
          ### ErrorDocument 404 /404/
          ```
- **Depending on the hosting environment, other `4xx` codes may need similar treatment**
    - For instance, AWS S3 will also require a similar rule for 403 responses

---
## Local Development :arrow_heading_down:
1. In a terminal, navigate to  `webroot/`
1. Ensure `.env` is created & up-to-date
1. `yarn install --ignore-engines`
1. `yarn build`
1. `yarn serve`
    - Visit `http://localhost:3018` in your browser
    - Files are watched for changes and the app is re-compiled automatically

### Onboarding
1. **Study `/webroot/src/styles.common/*`**
    - _To get a sense of what styles are available globally_
1. **Study `webroot/src/store/*`**
    - _To get a sense of the available store state / actions / getters_
1. **Study `webroot/src/models/*`**
    - _To get a sense of the available model types and their helper methods_
1. **Study `webroot/src/network/*.api.ts`**
    - _To get a sense of the available endpoint calls_
    - _There is also a Postman collection & environment in `/docs/postman`_
1. **Understand what's injected into Components**
    - Review `main.ts` and the `/plugins` directory

### Blueprints
We've created a CLI tool to help speed up the creation of certain modules, such as Components, Pages & Models.

- In a terminal, navigate to  `webroot/`
- **Create:** `node blueprint create <type> <name> <sub-path>`
- **Destroy:** `node blueprint destroy <type> <name> <sub-path>`
- **Help:** `node blueprint`

### CORS Testing
- This is a standalone single-page frontend (SPA); any server APIs will need to have CORS enabled. You can read more about CORS [here](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS).

We've created a CORS testing tool to make quick work of verifying whether CORS has been enabled for a server API:

1. In a terminal, navigate to  `webroot/`
1. `node cors-test.js`
    - Select the Origin domain
    - Enter / paste a server API endpoint
    - Choose the HTTP method you'll be using for the endpoint
1. The output will be the response status & headers
1. CORS requires that the `Access-Control-Allow-Origin` header must be included and contain a value matching the Origin domain
    - _Rather than simply parsing the headers for the expected value, we return all the headers as they can provide additional clues about any CORS config issues the server may have._


### Static assets
- **/src/assets vs. /public**
    - Prefer the `/src/assets` directory for static assets, such as images, vendor CSS, etc.
    - `/src/assets` files are examined / inlined by the webpack build process as appropriate. Missing images produce a build error before the user notices a 404. CSS under a certain size is auto-inlined to reduce network requests, etc.
    - The `/public` folder in just an escape hatch for one-offs
    - https://cli.vuejs.org/guide/html-and-static-assets.html#static-assets-handling

### Server API Docs
- TODO

---
## Tests
### Unit
Unit tests run non-interactively and can be included in automations.

#### Run all tests
1. In a terminal, navigate to  `webroot/`
1. `yarn test:unit:all`

#### Run specific tests
- In a terminal, navigate to  `webroot/`
- `yarn test:unit <path-under-webroot>`
    - _Specific test file:_ `yarn test:unit /src/components/Nav/Nav.spec.ts`
    - _Specific group of files:_ `yarn test:unit /src/components/Nav`
        - _Can also be used a shorthand for specific test file if only 1 exists in directory_
    - [Mocha options](https://mochajs.org/#command-line-usage) can also be passed in _(e.g. `watch`, `bail`, etc)_

### Coverage
1. In a terminal, navigate to  `webroot/`
1. `yarn test:unit:coverage`

### E2E
Currently, E2E tests run interactively and should not be included in automations.

#### Testing environment variables
1. In `/webroot/`, copy `cypress.env.example.json` to `cypress.env.json`
1. Adjust the values in `cypress.env.json` as needed`

#### Run E2E tests
1. In a terminal, navigate to  `webroot/`
1. `yarn test:e2e`

---
## Build
- In a terminal, navigate to  `webroot/`
- `yarn build`
    - A production-like app structure is created in `webroot/dist`

Note that testing the **built** app locally will require a running web server; file protocol will not work
- Example:
    - ```
      cd webroot/dist
      python3 -m http.server 8001

      ### Visit localhost:8001 in Private / Incognito browser
      ```
- Testing the **built** app should always be done with a Private / Incognito browser window
    - _Otherwise the PWA will get cached and testing a clean state or volatile in-progress work will require lots of manual cache storage clearing._

---
