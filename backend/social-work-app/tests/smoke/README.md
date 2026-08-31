# Smoke Tests

This directory contains smoke tests for the Compact ConnectSocial WorkAPI. Smoke tests are end-to-end integration tests that run against a test environment to verify that critical functionality works as expected.

## Overview

Smoke tests validate that key features of the Compact Connect API are working correctly in a test environment. They make real API calls and interact with actual AWS services (DynamoDB, Cognito, etc.) to ensure the system behaves correctly end-to-end.

## Prerequisites

Before running smoke tests, you must complete the following setup:

### 1. Sandbox/Test Environment

You must have access to a deployed sandbox environment of the Compact ConnectSocial WorkAPI. The sandbox should be deployed with the following configuration:

- **Security Profile**: Your `cdk.context.json` file must have `"security_profile": "VULNERABLE"` set. This allows the smoke tests to create users programmatically using the boto3 Cognito client.
- 
### 2. AWS Credentials

Ensure your AWS credentials are configured with appropriate permissions to:
- Access DynamoDB tables in the sandbox environment
- Access Cognito user pools in the sandbox environment
- Access other AWS services used by the smoke tests

1. Configure your AWS profile to use SSO:
   ```bash
   aws configure sso
   ```
   Follow the prompts to set up your SSO profile using the values from your IAM identity center login
   (see [AWS CLI SSO Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html#sso-configure-profile-token-auto-sso))

2. Log in to AWS SSO:
   ```bash
   aws sso login --profile <your-profile-name>
   ```

3. Set your AWS profile environment variable (if not using the default profile):
   ```bash
   export AWS_PROFILE=<your-profile-name>
   ```

### 3. Python Dependencies

Install the required Python packages. The smoke tests use the same dependencies as the main codebase. Ensure you have:
- Python 3.x
- All dependencies from the project's requirements files

### 4. Upload Test License Record

Some smoke tests create their own practitioner data via the state API (for example `license_upload_smoke_tests.py`). Other tests may still require a pre-existing provider; if so, upload a license record in your sandbox, look up the provider id in the Provider DynamoDB table, and set `CC_TEST_PROVIDER_ID` in `smoke_tests_env.json` (see Environment Variables Setup below).


## Environment Variables Setup

1. **Copy the example environment file:**
   ```bash
   cp smoke_tests_env_example.json smoke_tests_env.json
   ```

2. **Edit `smoke_tests_env.json`** with your sandbox environment values:

   **Required Variables:**
   - `CC_TEST_API_BASE_URL`: Base URL for the Compact Connect API (e.g., `https://api.sandbox.compactconnect.org`)
   - `CC_TEST_STATE_API_BASE_URL`: Base URL for the state API
   - `CC_TEST_STATE_AUTH_URL`: OAuth2 token endpoint for state authentication
   - `CC_TEST_COGNITO_STATE_AUTH_USER_POOL_ID`: Cognito user pool ID for state auth
   - `CC_TEST_PROVIDER_DYNAMO_TABLE_NAME`: DynamoDB table name for provider data
   - `CC_TEST_COMPACT_CONFIGURATION_DYNAMO_TABLE_NAME`: DynamoDB table name for compact configuration
   - `CC_TEST_DATA_EVENT_DYNAMO_TABLE_NAME`: DynamoDB table name for data events
   - `CC_TEST_STAFF_USER_DYNAMO_TABLE_NAME`: DynamoDB table name for staff users
   - `CC_TEST_COGNITO_STAFF_USER_POOL_ID`: Cognito user pool ID for staff users
   - `CC_TEST_COGNITO_STAFF_USER_POOL_CLIENT_ID`: Cognito client ID for staff users
   - `CC_TEST_PROVIDER_ID`: Provider id of your test provider user
   - `ENVIRONMENT_NAME`: Name of your sandbox environment
   - `AWS_DEFAULT_REGION`: AWS region where your sandbox is deployed (e.g., `us-east-1`)

   **Optional Variables (for specific tests):**
   - `CC_TEST_ROLLBACK_STEP_FUNCTION_ARN`: Step function ARN for rollback tests
   - `CC_TEST_RATE_LIMITING_DYNAMO_TABLE_NAME`: DynamoDB table name for rate limiting
   - `CC_TEST_SSN_DYNAMO_TABLE_NAME`: DynamoDB table name for SSN data
   - `CC_TEST_STAFF_USER_INACTIVITY_LAMBDA_NAME`: Function name of the staff user inactivity handler, used by
     `staff_user_inactivity_smoke_tests.py` (found in the `StaffUserInactivityStack`)

3. **Important:** Never commit `smoke_tests_env.json` to version control. It contains sensitive credentials and should be in `.gitignore`.

## Running Smoke Tests

### Running Individual Test Files

Each test file can be run independently from the social-work-app folder:

```bash
# Navigate to the compact-connect directory
cd backend/social-work-app

# Run a specific test file
python3 tests/smoke/encumbrance_smoke_tests.py
```

### License Upload Smoke Tests (`license_upload_smoke_tests.py`)

This test validates license upload, home state change notification, jurisdiction validation, and privilege generation:

1. Configures **AZ**, **OH**, and **CO** as live compact jurisdictions
2. Rejects a **LBSW** upload to **CO** (CO does not recognize that license type)
3. Runs the shared 3-upload home state change flow with **LBSW** (Jane TestSmith / SSN `999-88-8888`)
4. Asserts GET provider privileges include **AZ** only (CO is live but excluded; OH is home and excluded)

Expect a long runtime - roughly 15-20 minutes - since each of the six ingest waits sits behind the
one-minute batching windows on the preprocess and ingest queues, and the test performs them in sequence. Do not run this test concurrently with other smoke tests that use the same shared practitioner identity against the same sandbox.

### SSN Migration Smoke Tests (`ssn_migration_smoke_tests.py`)

This test validates the SSN-correction migration (the optional `previousSSN` license upload field), and in
particular what happens to a practitioner's Compact Unique Identifier (CUID) across a correction. The
practitioner holds a license pair in **two** states, and only the first state's licenses are corrected -
which is what keeps the original provider record alive to be checked after the identifier leaves it:

1. Builds an **OH** LBSW pair for one practitioner under one incorrect SSN (SsnMigration CuidSmokeTest /
   SSN `999-66-6666`), then encumbers and opens an investigation against their **AZ** privilege while OH is
   still their only pair - so both records record OH as the home jurisdiction they were created under.
   Then builds an **AZ** LBSW pair. OH goes first, so its pair is the one that earns the CUID
2. Corrects the OH **single-state** license, and asserts the CUID stays on the original record, is not minted
   on the corrected one, and that only the corrected provider has an `ssnCorrection` record so far
3. Corrects the OH **multi-state** license, and asserts the original CUID moved across unchanged rather than
   a new one being minted, and is no longer on the original record
4. Asserts **both** providers now carry an `ssnCorrection` record - the corrected one for each migration, and
   the original one recording the CUID it lost, with the old value in `previous` and
   `publicCompactIdentifier` in `removedValues`
5. Asserts the AZ pair was never touched (still on the original provider, still the original `ssnLastFour`)
   and the OH records arrived intact
6. Asserts the privilege encumbrance and investigation stayed behind through the single-state correction -
   a single-state license generates no privileges - and travelled with the multi-state license that did
   generate them

Expect a **long** runtime. A practitioner's single-state license must be fully ingested before their
multi-state license is uploaded (see [Upload order](../../docs/README.md)), so building the two pairs takes
four sequential upload/ingest cycles before the two corrections begin - six waits in total, each of which can
take a couple of minutes each because of the SQS batching windows. Both provider partitions are cleaned up
automatically, including on failure; the SSN table records are left in place by design, and the fixed mock
SSNs mean reruns reuse the same mappings.

Requires **OH** and **AZ** to be live jurisdictions in the target environment, with LBSW recognized in each.

## Special Test Requirements

### Tests Creating Test Data

Many tests create temporary test data (staff users, configurations, etc.) and clean it up automatically. However, if a test fails partway through, you may need to manually clean up test data.

These smoke tests should not be run against a production environment. They are only intended for sandbox and test environments

## Troubleshooting

### Common Issues

1. **"ResourceNotFoundException" when accessing DynamoDB tables**
   - Verify that your `smoke_tests_env.json` has the correct table names for your sandbox environment
   - Ensure your AWS credentials have permissions to access the tables
   - Check that the tables exist in the specified region

2. **"Failed to authenticate" or Cognito errors**
   - Check that `security_profile: "VULNERABLE"` is set in your `cdk.context.json`


### Triage Test Failures

If a test fails, you can consider the following steps to triage the cause of the failures:

1. Review CloudWatch logs for Lambda functions that were invoked
2. Check DynamoDB tables directly using the AWS Console or CLI
3. Check Cognito user pools to see if test users were created

## Contributing

When adding new smoke tests:

1. Follow the existing pattern in other test files
2. Use `SmokeTestFailureException` for test failures
3. Include cleanup logic for any test data created
4. Add appropriate docstrings explaining what the test does
5. Update this README with information about your new test if there are any special requirements

## Additional Resources

- See individual test files for specific requirements and usage examples
- Check `smoke_common.py` for shared utilities and helper functions
- Review `config.py` to understand how environment variables are loaded

