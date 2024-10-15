# OWASP Zed Attack Proxy

[ZAP](https://www.zaproxy.org/) is a security pen testing tool, which this project uses for active scanning for
vulnerabilities. To manually run a scan similar to the ones integrated into [our GitHub Actions](../.github/workflows),
run `./manual-scan.sh` from a command line. For full details on running the scan locally, see [Manual run ](#manual-run). Below is a brief explanation of the pieces of this integration and what they are for.

# Authenticator

The [authenticator](./authenticator) directory is a simple NodeJS script that leverages
[aws-amplify](https://www.npmjs.com/package/aws-amplify) to quickly log a test user in and acquire an token for
authentication. This script requires that the Cognit UserPool Client be configured to enable the SRP authentication
flow, which can only be activated in pre-production environments.

# Data

The [data](./data) folder contains configuration and automation data files that are used to control ZAP's scan. This
includes an HttpSender script and an automation YML file. The HTTPSender script will tell ZAP to add the token we acquired from the [authenticator](#authenticator) script into the `Authorization` header for every 'in scope' request, headed
to the UI or API. The YML file defines what jobs are to be run as part of an automated scan.

# Set up

In order for the scan to be able to run successfully, the scanned environment requires some set-up:
1) The target environment backend needs to be deployed with the `"security_profile": "VULNERABLE"` environment context set in order to prevent ZAP from being locked out. The `VULNERABLE` security profile cannot be used in the production environment.
2) Create a dedicated test user in the StaffUsers Cognito UserPool
3) Define the following secrets in the GitHub repository with the corresponding information from the staff user pool, client, and test user:

```
    TEST_COGNITO_USER_POOL_ID_STAFF
    TEST_WEBROOT_COGNITO_CLIENT_ID_STAFF
    TEST_ZAP_USERNAME_STAFF
    TEST_ZAP_PASSWORD_STAFF
```

# Manual run

If you wish to run the ZAP scan locally, you can do so buy following these steps:
1) Install `docker` [docker](https://www.docker.com/) on your computer.
2) From inside the [authenticator](./authenticator) folder, copy `env.example` to `.env` and update the example values with the real values from the StaffUser user pool and the test user created in [Set up](#set-up).
3) From the repository root, run `./owasp-zap/manual-run.sh`. The scan will run inside a docker container and the report will be added to a `reports` folder at the repository root.
