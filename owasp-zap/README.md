# OWASP Zed Attack Proxy

[ZAP](https://www.zaproxy.org/) is a security pen testing tool, which this project uses for active scanning for vulnerabilities. To manually run a scan similar to the ones integrated into [our GitHub Actions](../.github/workflows), run `./manual-scan.sh` from a command line. For full details on running the scan locally, see [Manual run](#manual-run). Below is a brief explanation of the pieces of this integration and what they are for.

# Authenticator

The [authenticator](./authenticator) directory contains helpers for obtaining bearer tokens against the three Cognito pools CompactConnect uses:

- `main.js` — a NodeJS script leveraging [aws-amplify](https://www.npmjs.com/package/aws-amplify) for user sign-in against the **Staff Users** and **Provider Users** pools. It accepts `--mode=staff` or `--mode=provider` to select which set of `.env` variables to use. Both pools must have the [Secure Remote Password (SRP)](https://en.wikipedia.org/wiki/Secure_Remote_Password_protocol) flow enabled, which happens automatically under the `VULNERABLE` security profile (see [Set up](#set-up)).
- `get-m2m-token.sh` — a shell script that performs the OAuth2 `client_credentials` grant against the **State Auth** pool for machine-to-machine access to `state-api.test.compactconnect.org`.

# Data

The [data](./data) folder contains configuration and automation data files that are used to control ZAP's scan. This includes an HttpSender script and an automation YML file. The HttpSender script (`bearer-token.js`) routes requests to the correct bearer token based on hostname + path: requests to the state API host get the M2M token, requests under `/v1/provider-users/*`, `/v1/purchases/*`, and `GET /v1/compacts/{compact}/attestations/{attestationId}` get the provider token, everything else gets the staff token. The YML file defines the ZAP automation plan.

# Set up

In order for the scan to run successfully, the target environment needs some set-up:

1. The target environment backend needs to be deployed with the `"security_profile": "VULNERABLE"` environment context set in order to prevent ZAP from being locked out. The `VULNERABLE` profile weakens a number of security elements to allow for the scan, including:
   - Removing the rate limit from the WAF policies
   - Enabling the SRP authentication flow (for both staff and provider pools)
   - Disabling Cognito Advanced Security
   - Removing MFA requirements

   Because of this loosened security for scanning, the `VULNERABLE` security profile cannot be used in the production environment.

2. **Staff Users pool** — create a dedicated test user with broad scope coverage (e.g. `aslp/admin` plus full `oh` and `ky` jurisdiction permissions). Define these GitHub secrets:

   ```
   TEST_COGNITO_USER_POOL_ID_STAFF
   TEST_WEBROOT_COGNITO_CLIENT_ID_STAFF
   TEST_ZAP_USERNAME_STAFF
   TEST_ZAP_PASSWORD_STAFF
   ```

3. **Provider Users pool** — create a dedicated test provider user. The user needs a backing provider record in DynamoDB with a license in a covered jurisdiction (e.g. `ky` or `oh` within ASLP) so the `/v1/provider-users/me/*` endpoints resolve. ZAP only needs handlers to execute — response codes don't matter for vulnerability scanning, so POST endpoints (`/v1/purchases/privileges`, `/v1/provider-users/me/military-affiliation`) returning 4xx on repeat runs because records already exist is fine; no cleanup is required between scans. Define these GitHub secrets:

   ```
   TEST_COGNITO_USER_POOL_ID_PROVIDER
   TEST_COGNITO_CLIENT_ID_PROVIDER
   TEST_ZAP_USERNAME_PROVIDER
   TEST_ZAP_PASSWORD_PROVIDER
   ```

4. **State Auth M2M pool** — provision an app client dedicated to ZAP scanning. Follow the process in [`../backend/compact-connect/app_clients/README.md`](../backend/compact-connect/app_clients/README.md), granting the minimum scopes needed to exercise the four state API endpoints:

   - `{compact}/readGeneral`
   - `{state}/{compact}.write` for each covered jurisdiction

   After creation, bump the access token validity from the default 15 minutes to 60 minutes so a single token covers a scan run under the 45-minute active scan cap:

   ```
   aws cognito-idp update-user-pool-client \
     --user-pool-id <state-auth-pool-id> \
     --client-id <zap-client-id> \
     --access-token-validity 60 \
     --token-validity-units AccessToken=minutes
   ```

   Then define these GitHub secrets:

   ```
   TEST_COGNITO_STATE_AUTH_DOMAIN         (e.g. compact-connect-state-auth-test.auth.us-east-1.amazoncognito.com)
   TEST_STATE_AUTH_CLIENT_ID
   TEST_STATE_AUTH_CLIENT_SECRET
   TEST_STATE_AUTH_SCOPES                 (space-separated, e.g. "aslp/readGeneral aslp/write ky/aslp.write oh/aslp.write")
   ```

# Manual run

To run the ZAP scan locally:

1. Install [docker](https://www.docker.com/).
2. From inside the [authenticator](./authenticator) folder, copy `.env.example` to `.env` and fill in whichever credential sets you have. Missing sets (e.g. you only have staff creds) are skipped with a warning — the scan still runs, but endpoints needing the missing tokens will return 401.
3. From the repository root, run `./owasp-zap/manual-scan.sh`. The scan runs inside a Docker container and the report is written to a `report/` folder at the repository root.
