# Smoke Tests

This directory contains smoke tests for the Compact Connect API. Smoke tests are end-to-end integration tests that run against a test environment to verify that critical functionality works as expected.

## Overview

Smoke tests validate that key features of the Compact Connect API are working correctly in a test environment. They make real API calls and interact with actual AWS services (DynamoDB, Cognito, etc.) to ensure the system behaves correctly end-to-end.

## Prerequisites

Before running smoke tests, you must complete the following setup:

### 1. Sandbox/Test Environment

You must have access to a deployed sandbox environment of the Compact Connect API. The sandbox should be deployed with the following configuration:

- **Security Profile**: Your `cdk.context.json` file must have `"security_profile": "VULNERABLE"` set. This allows the smoke tests to create users programmatically using the boto3 Cognito client.

### 2. Registered Provider User

You must have a registered provider user in your sandbox environment. This user will be used by the smoke tests to authenticate and perform various operations.

**To create a registered provider user:**
1. Register a provider user through the normal registration flow in your sandbox environment
2. Ensure the user has at least one active license record
3. Note the user's email address and password - you'll need these for the environment variables

### 3. AWS Credentials

Ensure your AWS credentials are configured with appropriate permissions to:
- Access DynamoDB tables in the sandbox environment
- Access Cognito user pools in the sandbox environment
- Access other AWS services used by the smoke tests

You can configure credentials using:
- AWS CLI: `aws configure`
- Environment variables: `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- IAM role (if running on EC2/ECS)

### 4. Python Dependencies

Install the required Python packages. The smoke tests use the same dependencies as the main codebase. Ensure you have:
- Python 3.x
- All dependencies from the project's requirements files

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
   - `CC_TEST_COGNITO_PROVIDER_USER_POOL_ID`: Cognito user pool ID for provider users
   - `CC_TEST_COGNITO_PROVIDER_USER_POOL_CLIENT_ID`: Cognito client ID for provider users
   - `CC_TEST_PROVIDER_USER_USERNAME`: Email address of your registered provider user
   - `CC_TEST_PROVIDER_USER_PASSWORD`: Password for your registered provider user
   - `ENVIRONMENT_NAME`: Name of your sandbox environment
   - `AWS_DEFAULT_REGION`: AWS region where your sandbox is deployed (e.g., `us-east-1`)

   **Optional Variables (for specific tests):**
   - `SANDBOX_AUTHORIZE_NET_API_LOGIN_ID`: Authorize.net API login ID for payment processing tests
   - `SANDBOX_AUTHORIZE_NET_TRANSACTION_KEY`: Authorize.net transaction key for payment processing tests
   - `CC_TEST_ROLLBACK_STEP_FUNCTION_ARN`: Step function ARN for rollback tests
   - `CC_TEST_RATE_LIMITING_DYNAMO_TABLE_NAME`: DynamoDB table name for rate limiting
   - `CC_TEST_SSN_DYNAMO_TABLE_NAME`: DynamoDB table name for SSN data
   - `CC_TEST_GET_PROVIDER_SSN_LAMBDA_NAME`: Lambda function name for SSN retrieval

3. **Important:** Never commit `smoke_tests_env.json` to version control. It contains sensitive credentials and should be in `.gitignore`.

## Running Smoke Tests

### Running Individual Test Files

Each test file can be run independently from the compact-connect folder:

```bash
# Navigate to the smoke tests directory
cd backend/compact-connect

# Run a specific test file
python3 tests/smoke/purchasing_privileges_smoke_tests.py
python3 tests/smoke/military_affiliation_smoke_tests.py
python3 tests/smoke/query_provider_smoke_tests.py
```

## Special Test Requirements

### Tests Requiring Manual Input

Some tests require manual interaction:

- **`practitioner_email_update_smoke_tests.py`**: Requires you to manually enter email verification codes sent to your email address.

### Tests Creating Test Data

Many tests create temporary test data (staff users, configurations, etc.) and clean it up automatically. However, if a test fails partway through, you may need to manually clean up test data.

## Troubleshooting

### Common Issues

1. **"ResourceNotFoundException" when accessing DynamoDB tables**
   - Verify that your `smoke_tests_env.json` has the correct table names for your sandbox environment
   - Ensure your AWS credentials have permissions to access the tables
   - Check that the tables exist in the specified region

2. **"Failed to authenticate" or Cognito errors**
   - Verify that `CC_TEST_PROVIDER_USER_USERNAME` and `CC_TEST_PROVIDER_USER_PASSWORD` are correct
   - Ensure the provider user exists and is registered in your sandbox environment
   - Check that `security_profile: "VULNERABLE"` is set in your `cdk.context.json`


### Verifying Test Data

If a test fails, you can verify the state of your test data:

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

