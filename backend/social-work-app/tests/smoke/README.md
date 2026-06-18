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

Expect long runtimes (up to ~15 minutes) due to SQS batching windows during license ingest. Do not run this test concurrently with other smoke tests that use the same shared practitioner identity against the same sandbox.

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

