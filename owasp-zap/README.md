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

4. **State Auth M2M pool** — provision an app client dedicated to ZAP scanning. This client needs two things that differ from a standard state onboarding client:

   - A 60-minute access token validity (vs. the 15-minute default) so one token covers a scan run under the 45-minute active scan cap.
   - Scopes to exercise all four state API endpoints: `{compact}/readGeneral` plus `{state}/{compact}.write` for each covered jurisdiction.

   Rather than creating with defaults and patching after (`update-user-pool-client` is a full-replacement API — any attribute omitted is reset to its default, which is easy to get wrong), temporarily bump the validity in the creation script:

   1. In `backend/compact-connect/app_clients/bin/create_app_client.py`, change `BASE_CLIENT_CONFIG['AccessTokenValidity']` from `15` to `60`. **Do not commit this change** — it's a one-shot override for this ZAP client.
   2. Run the script against the test StateAuthUsers pool:

      ```
      python3 backend/compact-connect/app_clients/bin/create_app_client.py -u <state-auth-pool-id>
      ```

      At the prompts: client name `owasp-zap-v1` (increment the version on rotation), compact `aslp`, state `ky`, additional scopes `aslp/readGeneral,oh/aslp.write`. Capture the `clientId` / `clientSecret` from the output.
   3. Revert the `AccessTokenValidity` change in `create_app_client.py`.
   4. Verify the client with `aws cognito-idp describe-user-pool-client` — you should see `AccessTokenValidity: 60` and `AllowedOAuthScopes` containing `aslp/readGeneral`, `ky/aslp.write`, `oh/aslp.write`.

   Then define these GitHub secrets:

   ```
   TEST_COGNITO_STATE_AUTH_DOMAIN         (e.g. compact-connect-state-auth-test.auth.us-east-1.amazoncognito.com)
   TEST_ZAP_STATE_AUTH_CLIENT_ID
   TEST_ZAP_STATE_AUTH_CLIENT_SECRET
   TEST_ZAP_STATE_AUTH_SCOPES             (space-separated, e.g. "aslp/readGeneral ky/aslp.write oh/aslp.write")
   ```

# Manual run

To run the ZAP scan locally:

1. Install [docker](https://www.docker.com/).
2. From inside the [authenticator](./authenticator) folder, copy `.env.example` to `.env` and fill in whichever credential sets you have. Missing sets (e.g. you only have staff creds) are skipped with a warning — the scan still runs, but endpoints needing the missing tokens will return 401.
3. From the repository root, run `./owasp-zap/manual-scan.sh`. The scan runs inside a Docker container and the report is written to a `report/` folder at the repository root.
