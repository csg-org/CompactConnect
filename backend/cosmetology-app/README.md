# Compact Connect - Backend developer documentation

## Looking for technical user documentation?
[Find it here](./docs/README.md)

## Introduction

This is an [AWS-CDK](https://aws.amazon.com/cdk/) based project for the backend components of the licensure compact system.

## Table of Contents
- **[Prerequisites](#prerequisites)**
- **[Environment Config](#environment-config)**
- **[Installing Dependencies](#installing-dependencies)**
- **[Local Development](#local-development)**
- **[Tests](#tests)**
- **[Deployment](#deployment)**
- **[Google reCAPTCHA Setup](#google-recaptcha-setup)**
- **[Decommissioning](#decommissioning)**
- **[More Info](#more-info)**

## Prerequisites
[Back to top](#compact-connect---backend-developer-documentation)

To deploy this app, you will need:
1) Access to an AWS account
2) Python>=3.14 installed on your machine, preferably through a virtual environment management tool like
   [pyenv](https://github.com/pyenv/pyenv), for clean management of virtual environments across multiple Python
   versions.
   > Note: The [purchases lambda](./lambdas/python/purchases) depends on the
   > [Authorize.Net python sdk](https://github.com/AuthorizeNet/sdk-python/issues/164), which is barely maintained at
   > present, and is not yet compatible with Python 3.13. Due to that restriction, we have to hold back the python
   > version of just this lambda package, so that the entire project is not impacted. For local development, this means
   > that, at least for lambdas that use this package, developers will have to have a dedicated python environment, held
   > back at Python 3.12. That environment and its dependencies will have to be maintained separately from those of the
   > rest of the project, which can all share a common virtual environment and common dependencies, without excessive risk of
   > version conflicts.
3) Otherwise, follow the [Prerequisites section](https://cdkworkshop.com/15-prerequisites.html) of the CDK workshop to
   prepare your system to work with AWS-CDK, including a NodeJS install.
4) Follow the steps in the [Installing Dependencies](#installing-dependencies) section.

## Environment Config
[Back to top](#compact-connect---backend-developer-documentation)

The `cdk.json` file tells the CDK Toolkit how to execute your app, including configuration specific to any given target
deployment. You can add local configuration that will be merged into the `cdk.json['context']` values with a
`cdk.context.json` file that you will not check in.

This project is set up like a standard Python project. To use it, create and activate a python virtual environment
using the tools of your choice (`pyenv` and `venv` are common).

Once the virtualenv is activated, you can install the required dependencies.

## Installing Dependencies
[Back to top](#compact-connect---backend-developer-documentation)

Python requirements are pinned in [`requirements.txt`](requirements.txt). Install them using `pip`:

```
$ pip install -r requirements.txt
```

Node.js requirements (for some selected Lambda runtimes) are defined in [`package.json`](./lambdas/nodejs). Install them using `yarn`.

```shell
$ cd lambdas/nodejs
$ yarn install
```

At this point you can now synthesize the CloudFormation template(s) for this code.

```
$ cdk synth
```

For development work there are additional requirements in `requirements-dev.txt` to install with
`pip install -r requirements-dev.txt`.

To add additional dependencies, for example other CDK libraries, just add them to the `requirements.in` file and rerun
`pip-compile requirements.in`, then `pip install -r requirements.txt` command.

### Convenience scripts

To simplify dependency installation in this project, which includes many runtimes with similar dependencies, maintain
the dependency files with two convenience scripts, which manage the file contents for _most_ runtimes (See Note below),
[compile_requirements.sh](./bin/compile_requirements.sh), and installs the defined dependencies,
[sync_deps.sh](./bin/sync_deps.sh).

> Note: Due to its dependency on the Authorize.Net python sdk, the [purchases lambda](./lambdas/python/purchases)
> dependencies have to be maintained separately from the rest of the project. You can update the requirements files for
> that lambda directly with the `pip-compile` command, and install dependencies into your python enviornment dedicated
> to that lambda with the `pip-sync` command.

## Local Development
[Back to top](#compact-connect---backend-developer-documentation)

Local development can be done by editing the python code and `cdk.json`. For development purposes, this is simply a
Python project that can be exercised with local tests. Be sure to install the development requirements:

```
pip install -r requirements-dev.txt
```

Note that this project is a cloud-native app that has many small modular runtimes and integrations. Simulating that
distributed environment locally is not feasible, so the project relies heavily on test-driven development and solid
unit/functional tests to be incorporated in the development workflow. If you want to deploy this app to see how it runs
in the cloud, you can do so by configuring context for your own sandbox AWS account with context variables in
`cdk.context.json` and running the appropriate `cdk deploy` command.

Once the deployment completes, you may want to run a local frontend. To do so, you must [populate a `.env`
file](../../webroot/README.md#environment-variables) with data on certain AWS resources (for example, AWS Cognito auth
domains and client IDs). A quick way to do that is to run `bin/sandbox_fetch_aws_resources.py --as-env` from the
`backend/compact-connect` directory and copy/paste the output into `webroot/.env`. To see more data on your deployment
in human-readable format (for example, DynamoDB table names), run `bin/fetch_aws_resources.py` without any additional
flags.

## Tests
[Back to top](#compact-connect---backend-developer-documentation)

Being a cloud project whose infrastructure is written in Python, establishing tests, using the python `unittest`
library is critical to maintaining reliability and velocity. Be sure that any updates you add are covered
by tests, so we don't introduce bugs or cost time identifying testable bugs after deployment. Note that all
unit/functional tests bundled with this app should be designed to execute with zero requirements for environmental
setup (including environment variables) beyond simply installing the dependencies in `requirements*.txt` files. CDK
tests are defined under the [tests](./tests) directory. Runtime code tests should be similarly bundled within the
lambda folders. Code that is common across all lambdas should be abstracted to a common code asset and tested there, to
reduce duplication and ensure consistency across the app.

To execute the tests, simply run `bin/sync_deps.sh` then `bin/run_tests.sh` from the `backend` directory.

## Documentation
[Back to top](#compact-connect---backend-developer-documentation)

Keeping documentation current is an important part of feature development in this project. If the feature involves a
non-trivial amount of architecture or other technical design, be sure that the design and considerations are captured
in the [design documentation](./docs/design). If any updates are made to the API, be sure to follow these steps to keep
the documentation current:
1) Export a fresh api specification (OAS 3.0) is exported from API Gateway and used to update
   [the Open API Specification JSON file](./docs/api-specification/latest-oas30.json).
2) Run `bin/trim_oas30.py` to organize and trim the API to include only supported API endpoints (and update the script
   itself, if needed).
3) If you exported the api specification from somewhere other than the CSG Test environment, be sure to set the
   `servers[0].url` entry back to the correct base URL for the CSG Test environment.
4) Use `bin/update_postman_collection.py` to update the [Postman Collection and Environment](./docs/postman), based on
   your new api spec, as appropriate.

## Deployment
[Back to top](#compact-connect---backend-developer-documentation)

### AWS Service Quota Increases
Before deploying to any environment (sandbox, test, beta, or production), you'll need to request service quota
increases for the following AWS services:

#### 1. Resource Servers Per User Pool (Amazon Cognito)
The Staff Users pool in CompactConnect uses resource servers for every jurisdiction (50+ states/territories). It also
has resource servers for each compact to implement granular permission scopes. As detailed in
[User Architecture documentation](./docs/design/README.md#user-architecture), resource server scopes are defined at
both the jurisdiction level (ie for state administrators) and the compact level (ie for compact administrators),
allowing for fine-grained access control tailored to each entity's specific needs.

**Required Steps:**
1. Visit the [AWS Service Quotas console](https://console.aws.amazon.com/servicequotas/home) in each AWS account you'll be deploying to
2. Search for "Amazon Cognito User Pools"
3. Find "Resource servers per user pool" (default value is 25)
4. Request an increase to at least 100 resource servers per user pool
5. Wait for AWS to approve the increase before attempting deployment

This increase gives sufficient capacity for all jurisdictions (50+ states/territories) plus all compacts, with room for
future expansion.

#### 2. Concurrent Executions (AWS Lambda)
CompactConnect uses numerous Lambda functions to power its backend services. By default, new AWS accounts have a very
low concurrent execution limit.

**Required Steps:**
1. Visit the [AWS Service Quotas console](https://console.aws.amazon.com/servicequotas/home) in each AWS account you'll be deploying to
2. Search for "AWS Lambda"
3. Find "Concurrent executions" (default value is 10 for new accounts)
4. Request an increase to at least 1,000 concurrent executions
5. Wait for AWS to approve the increase before attempting deployment

This increase ensures that your Lambda functions can scale appropriately during periods of high traffic without throttling.

### First deploy to a Sandbox environment
The very first deploy to a new environment (like your personal sandbox account) requires a few steps to fully set up
its environment:
1) *Optional:* Create a new Route53 HostedZone in your AWS sandbox account for the DNS domain name you want to use for
   your app. See [About Route53 Hosted Zones](#about-route53-hosted-zones) for more. Note: Without this step, you will
   not be able to log in to the UI hosted in CloudFront. The Oauth2 authentication process requires a predictable
   callback url to be pre-configured, which the domain name provides. You can still run a local UI against this app,
   so long as you leave the `allow_local_ui` context value set to `true` and remove the `domain_name` param in your
   environment's context.
2) *Optional if testing SES email notifications with custom domain:* By default, AWS does not allow sending emails to
   unverified email
   addresses. If you need to test SES email notifications and do not want to request AWS to remove your account from
   the SES sandbox, you will need to set up a verified SES email identity for each address you want to send emails to.
   See [Creating an email address identity](https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html#verify-email-addresses-procedure). Alternatively, you can request AWS to remove your account
   from the SES sandbox, which will allow you to send emails to addresses that are not verified. See
   [SES Sandbox](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html).
   If you do not specify the `domain_name` field in your environment context, cognito will use its default email
   configuration.
   See [Default User Pool Email Settings](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-email.html#user-pool-email-default)
3) Copy [cdk.context.sandbox-example.json](./cdk.context.sandbox-example.json) to `cdk.context.json`.
4) At the top level of the JSON structure update the `"environment_name"` field to your own name.
5) Update the environment entry under `ssm_context.environments` to your own name and your own AWS sandbox account id
   (which you can find by following
   [these instructions](https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-identifiers.html#FindAccountId)),
   and domain name, if you set one up. **If you opted not to create a HostedZone, remove the `domain_name` field.**
   The key under `environments` must match the value you put under `environment_name`.
6) Configure your aws cli to authenticate against your own account. There are several ways to do this based on the
   type of authentication you use to login to your account. See the [AWS CLI Configuration Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-quickstart.html).
7) Complete the [StatSig Feature Flag Setup](#statsig-feature-flag-setup) steps for your sandbox environment.
8) Complete the [Google reCAPTCHA Setup](#google-recaptcha-setup) steps for your sandbox environment.
9) Run `cdk bootstrap` to add some base CDK support infrastructure to your AWS account. See
   [Custom bootstrap stack](#custom-bootstrap-stack) below for optional custom stack deployment.
10) Run `cdk deploy 'Sandbox/*'` to get the initial backend stack resources deployed.
11)*Optional:* If you have a domain name configured for your sandbox environment, once the backend stacks have
    successfully deployed, you can deploy the frontend UI app as well. See the
    [UI app for details](../compact-connect-ui-app/README.md).

### Subsequent sandbox deploys:
For any future deploys, everything is set up so a simple `cdk deploy 'Sandbox/*'` should update all your infrastructure
to reflect the changes in your code. Full deployment steps are:
1) Make sure your python environment is active.
2) Run `bin/sync_deps.sh` from `backend/` to ensure you have the latest requirements installed.
3) Configure your aws cli to authenticate against your own account.
4) Run `cdk deploy 'Sandbox/*'` to deploy the app to your AWS account.

### Custom bootstrap stack

The pipelined environments leverage a custom bootstrap stack, which includes cross-account trusts to the deploy account
as well as a permissions boundary around the CloudFormation execution role. If new AWS services are added to the app
architecture, that permissions boundary will need to be updated to allow access to the new service. See the
[multi-account documentation](../multi-account/README.md#bootstrap-the-application-accounts) for details on how to
deploy the custom bootstrap stack. If you want to test the bootstrap stack customizations in your sandbox, for example,
to make sure the new resources you are creating in your sandbox won't be blocked by the CloudFormation execution role's
permission boundary, you can deploy the custom stack to a sandbox account for testing, using the same steps.

### Verifying SES configuration for Cognito User Notifications
If your account is in the SES sandbox, the simplest way to verify that SES is integrated with your cognito user pool is
to first go the AWS SES console and create an SES verified email identity for the email address you want to send a test
message to, See [Creating an email address identity](https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html#verify-email-addresses-procedure).

Once you have verified your email address, go to the AWS Cognito console and find your user pool. From there, you have
the option to create a new user using your verified email address, and select the option to send an email invite. Once
you create the user, you should receive an email notification from Cognito, and you can verify that
the FROM address is using your custom domain. The DMARC authentication will reject any emails from your domain that are
not properly configured using SPF and DKIM, so if you get the email notification from Cognito, you've verified that the
authentication is working as expected.

### First deploy to the production environment
The production environment requires a few steps to fully set up before deploys can be automated. Refer to the
[README.md](../multi-account/README.md) for details on setting up a full multi-account architecture environment. Once
that is done, perform the following steps to deploy the CI/CD pipelines into the appropriate AWS account:
- Complete the [StatSig Feature Flag Setup](#statsig-feature-flag-setup) steps for each environment you will be deploying to (test, beta, prod).
- Complete the [Google reCAPTCHA Setup](#google-recaptcha-setup) steps for each environment you will be deploying to (test, beta, prod).
  Use the appropriate domain name for the environment (ie `app.test.compactconnect.org` for test environment,
  `app.beta.compactconnect.org` for beta environment, `app.compactconnect.org` for production). For the production
  environment, make sure to complete the billing setup steps as well.
- Have someone with suitable permissions in the GitHub organization that hosts this code navigate to the AWS Console
  for the Deploy account, go to the
  [AWS CodeStar Connections](https://us-east-1.console.aws.amazon.com/codesuite/settings/connections) page and create a
  connection that grants AWS permission to receive GitHub events. Note the ARN of the resulting connection for
  the next step.
- Create a new Route53 hosted zone for the domain name you plan to use for the app in each of the production, beta, and
  test AWS accounts. See [About Route53 hosted zones](#about-route53-hosted-zones) below for more detail.
- Request AWS to remove your account from the SES sandbox and wait for them to complete this request.
  See [SES Sandbox](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html).
- With the [aws-cli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), set up your local machine to authenticate against the Deploy account as an administrator.
- For every environment, copy the appropriate example context file (`cdk.context.deploy-example.json` for the `Deploy`
  account, `cdk.context.test-example.json` for the `Test` account, `cdk.context.beta-example.json` for the `Beta`
  account, or `cdk.context.prod-example.json` for the `Prod` account) to `cdk.context.json` and update the values to
  match your respective accounts and other identifiers, including the code star connection you just created to match
  the identifiers for your actual accounts and resources. You will then need to run the
  `bin/put_ssm_context.sh <environment>` script to push relevant content from your `cdk.context.json` script into an
  SSM Parameter in your Deploy account. Replace `<environment>` with the target environment. For example, to set up for
  the test environment: `bin/put_ssm_context.sh test`.
  For example, to set up for the test environment: `bin/put_ssm_context.sh test`.
- Optional: If a Slack integration is desired for operational support, have someone with permission to install Slack
  apps in your workspace and Admin access to each of the Test, Beta, Prod, and Deploy accounts log into each AWS account
  and go to the Chatbot service. Select 'Slack' under the **Configure a chat client** box and click **Configure
  client**, then follow the Slack authorization prompts. This will authorize AWS to integrate with the channels you
  identify in your `cdk.context.json` file. For each Slack channel you want to integrate, be sure to invite your new
  AWS app to those channels. Update the `notifications.slack` sections of the `cdk.context.json` file with the details
  for your Slack workspace and channels.
  If you opt not to integrate with Slack, remove the `slack` fields from the file.
- Set cli-environment variables `CDK_DEFAULT_ACCOUNT` and `CDK_DEFAULT_REGION` to your deployment account id and
  `us-east-1`, respectively.
- For each environment (test, beta, prod), you need to deploy both the backend and frontend pipeline stacks:

1. **Deploy the Backend Pipeline Stacks first (note: you will need to approve the permission change requests for each
   stack deployment in the terminal)**:
  `cdk deploy --context action=bootstrapDeploy TestBackendPipelineStack BetaBackendPipelineStack ProdBackendPipelineStack`

2. **Then deploy the Frontend App**:
   See the [UI app for details](../compact-connect-ui-app/README.md).

**Important**: When a pipeline stack is deployed, it will automatically trigger a deployment to its environment from
the configured branch in your GitHub repo. The first time you deploy the backend pipeline, it should pass all the steps
except the final trigger of the frontend pipeline, since the frontend pipeline will not exist until you deploy it. From
there on, the pipelines should integrate as designed.

### Subsequent production deploys

Once the pipelines are established with the above steps, deployments will be automatically handled:

- Tags pushed with the pattern, `cc-test-*` will trigger the backend `test` pipeline to deploy
- Tags pushed with the pattern, `cc-prod-*` will trigger the backend `beta` and `prod` pipelines to deploy

> *Note:* The frontend app has dependencies on the backend, in the form of parameters like
> S3 bucket urls, cognito domains, etc. If those change, you will need to explicitly plan
> the deploys so that the backend completes before the frontend starts to resolve the dependency.
>
> Currently, we include a [GitHub Action](../../.github/workflows/auto-tag-test-deployments.yml) that automatically
> tags all pushed commits to `main` with a `cc-test-*` and `ui-test-*` tag. Because there is no coordination between
> pipelines for these, now independent, services, they go out in parallel to the `test` environment. If these
> cross-app dependencies change, you will need to manually create an additional `ui-test-*` tag after the backend
> deploy completes, to resolve the cross-app dependencies.

## StatSig Feature Flag Setup
[Back to top](#compact-connect---backend-developer-documentation)

The feature flag system uses StatSig to manage feature flags across different environments. Follow these steps to set up StatSig for your environment:

1. **Create a StatSig Account**
   - Visit [StatSig](https://www.statsig.com/) and create an account
   - Set up your project and organization

2. **Generate API Keys**
   - Navigate to the [API Keys section](https://docs.statsig.com/guides/first-feature/#step-4---create-a-new-client-api-key) of the StatSig console
   - You'll need to create three types of API keys:
     - **Server Secret Key**: Used for server-side feature flag evaluation
     - **Client API Key**: Used for client-side feature flag evaluation (optional for this backend setup)
     - **Console API Key**: Used for programmatic management of feature flags via the Console API

3. **Store Credentials in AWS Secrets Manager**
   - For each environment (test, beta, prod), create a secret in AWS Secrets Manager with the following naming pattern:
     ```
     compact-connect/env/{environment_name}/statsig/credentials
     ```
   - The secret value should be a JSON object with the following structure:
     ```json
     {
       "serverKey": "<your_server_secret_key>",
       "consoleKey": "<your_console_api_key>"
     }
     ```
   - You can create the secret for each environment account by logging into the respective environment account and using the AWS CLI:
     ```bash
     aws secretsmanager create-secret \
       --name "compact-connect/env/{test | beta | prod}/statsig/credentials" \
       --secret-string '{"serverKey": "<your_server_secret_key>", "consoleKey": "<your_console_api_key>"}'
     ```

## Google reCAPTCHA Setup
[Back to top](#compact-connect---backend-developer-documentation)

The practitioner registration endpoint uses Google reCAPTCHA to prevent abuse. Follow these steps to set up reCAPTCHA
for your environment:

1. Visit https://www.google.com/recaptcha/
2. Go to "v3 Admin Console"
   - If needed, enter your Google account credentials
3. Create a site
   - Recaptcha type is v3 (score based)
   - Domain will be the frontend browser domain for the environment ('localhost' for local development)
   - Google Cloud Platform may require a project name
   - Submit
4. Open the Settings for the new site
   - The Site Key (Public) will need to be set in the cdk.context.json for the appropriate environment under the field
     named `recaptcha_public_key` for deployments, or in your local `.env` file of the webroot folder (if running the
     app locally)
   - The Secret Key (Private) will need to be manually stored in the AWS account in secrets manager, using the
     following secret name:
     `compact-connect/env/{value of 'environment_name' in cdk.context.json}/recaptcha/token`
   The value of the secret key should be in the following format:
   ```
   {
     "token": "<value of private Secret Key from Google reCAPTCHA>"
   }
   ```
   You can run the following aws cli command to create the secret (make sure you are logged in to the same AWS account
   you want to store the secret in, under the us-east-1 region):
   ```
   aws secretsmanager create-secret --name compact-connect/env/{value of 'environment_name' in cdk.context.json}/recaptcha/token --secret-string '{"token": "<value of private Secret Key from Google reCAPTCHA>"}'
   ```

For Production environments, additional billing setup is required:
1. In the Settings for a reCAPTCHA site, click "View in Cloud Console"
2. From the main nav, go to Billing
3. If you have an existing billing account, you may link it. Otherwise, you can create a New Billing account, where you
   will add payment information
4. More info on Google Recaptcha billing: https://cloud.google.com/recaptcha/docs/billing-information

### Useful commands

* `cdk ls`          list all stacks in the app
* `cdk synth`       emits the synthesized CloudFormation template
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk docs`        open CDK documentation

## Decommissioning
[Back to top](#compact-connect---backend-developer-documentation)

You can tear down resources associated with any of the CloudFormation stacks for this application with
`cdk destroy <stack-name>`. Most persistent resources with data remain in the Persistent stack, so you can freely
destroy the others without losing users or data. If you wish to destroy the Persistent stack as well, be aware that
some resources may be left behind as CloudFormation is designed to err on the side of orphaning resources over data
loss. You can identify any resources that weren't destroyed by watching the stack deletion from the AWS CloudFormation
Console, then looking at the resources after its delete is complete, to look for any with a `Delete Skipped` status.

## About Route53 hosted zones

A Hosted Zone in Route53 represents a collection of DNS records for a particular domain and its subdomains, managed
together. See the [Route53 FAQs for more](https://aws.amazon.com/route53/faqs/). When creating a hosted zone, you have
to also configure the domain name registrar (be it AWS or some other vendor) to point to the name servers associated
with your hosted zone, before the records in the zone will have any effect. When deploying this app, creating a hosted
zone in the AWS account for the UI and API domains is part of the environment setup. If you use the common approach
of having your test environments be a subdomain of your production environments (i.e. `compactconnect.org` for prod
and `test.compactconnect.org` for test), you need to delegate nameserver authority from your production hosted zone
(`compactconnect.org` in this example) to your test account's hosted zone (`test.compactconnect.org`). To do this, you
need to create your production hosted zone (`compactconnect.org`) in your production account first, then create your
test hosted zone (`test.compactconnect.org`) in your test account second, then delegate name server authority to your
test subdomain. To do this, find the NS record associated with your test hosted zone and copy its value, which should
look something like:
```text
ns-1.awsdns-19.co.uk.
ns-2.awsdns-18.com.
ns-5.awsdns-15.net.
ns-6.awsdns-16.org.
```

Copy those name server values and, back in your production hosted zone, create a new NS record that matches the test
one, with the same value (i.e. Record Name: `test.compactconnect.org`, Type: `NS`, Value: `<same as above>`). Once that
is done, your test hosted zone is ready for use by the app. You will need to perform this action for your beta
environment as well, should you choose to deploy one.

> [!WARNING]
> Additionally, If you are setting up a Route53 HostedZone, you need to add an A record at your environment's HostedZone's
> base domain (i.e. `compactconnect.org` for prod and `test.compactconnect.org` for test) if there is not one already
> there. The target of the A record is actually not important, we simply need an A record at the base domain to
> prove that we own it. This is necessary to create auth subdomains for the user pools. We have been pointing the A record
> at the ip of compactconnect.org, which can be obtained by running the command `dig compactconnect.org +short`

## More Info
[Back to top](#compact-connect---backend-developer-documentation)

- [cdk-workshop](https://cdkworkshop.com/): If you are new to CDK, I highly recommend you go through the CDK Workshop for a quick
  introduction to the technology and its concepts before getting too deep into any particular project.
