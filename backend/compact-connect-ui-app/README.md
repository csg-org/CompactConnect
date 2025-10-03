# Compact Connect UI - Backend developer documentation

## Looking for technical user documentation?
[Find it here](../compact-connect/docs/README.md)

## Looking for architectural design documentation?
[Find it here](../compact-connect/docs/design/README.md)

## Introduction

This is an [AWS-CDK](https://aws.amazon.com/cdk/) based project for the frontend deploy and hosting infrastructure for
the licensure compact system.

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
[Back to top](#compact-connect-ui---backend-developer-documentation)

To deploy this app, you will need:
1) Access to an AWS account
2) Python>=3.12 installed on your machine, preferably through a virtual environment management tool like
   [pyenv](https://github.com/pyenv/pyenv),
   for clean management of virtual environments across multiple Python versions.
3) Otherwise, follow the [Prerequisites section](https://cdkworkshop.com/15-prerequisites.html) of the CDK workshop to
   prepare your system to work with AWS-CDK, including a NodeJS install.
4) Follow the steps in the [Installing Dependencies](#installing-dependencies) section.

## Environment Config
[Back to top](#compact-connect-ui---backend-developer-documentation)

The `cdk.json` file tells the CDK Toolkit how to execute your app, including configuration specific to any given target
deployment. You can add local configuration that will be merged into the `cdk.json['context']` values with a
`cdk.context.json` file that you will not check in.

This project is set up like a standard Python project. To use it, create and activate a python virtual environment
using the tools of your choice (`pyenv` and `venv` are common).

Once the virtualenv is activated, you can install the required dependencies.

## Installing Dependencies
[Back to top](#compact-connect-ui---backend-developer-documentation)

Python requirements are pinned in [`requirements.txt`](requirements.txt). Install them using `pip`:

```
$ pip install -r requirements.txt
```

Node.js requirements (for some selected Lambda runtimes) are defined in [`package.json`](./lambdas/nodejs). Install
them using `yarn`.

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

## Local Development
[Back to top](#compact-connect-ui---backend-developer-documentation)

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
[Back to top](#compact-connect-ui---backend-developer-documentation)

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
[Back to top](#compact-connect-ui---backend-developer-documentation)

Keeping documentation current is an important part of feature development in this project. If the feature involves a
non-trivial amount of architecture or other technical design, be sure that the design and considerations are captured
in the [design documentation](./docs/design).

## Deployment
[Back to top](#compact-connect-ui---backend-developer-documentation)

### First deploy to a Sandbox environment
The very first deploy to a new environment (like your personal sandbox account) requires a few steps to fully set up
its environment:
1) Deploy the backend app. See the [backend app](../compact-connect/README.md) for details. You will need to configure
   the 'optional' domain name, if you want to host your frontend in your sandbox.
2) Copy your sandbox context file from the backend app to this folder.
3) Once the backend stacks have successfully deployed with a domain name, you can deploy the frontend UI by setting the
   running `cdk deploy 'SandboxUI/*'`. The application will then be accessible at the 'app' subdomain of the configured
   domain name (e.g., `https://app.[configured_domain.com]`).

### Subsequent sandbox deploys:
For any future deploys, everything is set up so a simple `cdk deploy 'SandboxUI/*'` should update all your frontend
infrastructure to reflect the changes in your code. Full deployment steps are:
1) Make sure your python environment is active.
2) Run `bin/sync_deps.sh` from `backend/` to ensure you have the latest requirements installed.
3) Configure your aws cli to authenticate against your own account.
4) Run `cdk deploy 'SandboxUI/*'` to deploy the app to your AWS account.

### First deploy to the production environment
The production environment requires a few steps to fully set up before deploys can be automated. Refer to the
[README.md](../multi-account/README.md) for details on setting up a full multi-account architecture environment. Once
that is done, perform the following steps to deploy the CI/CD pipelines into the appropriate AWS account:
1. **Deploy the Backend Pipeline Stacks and applications first:** See [the backend app](../compact-connect/README.md)
   for details.

2. **Then deploy the Frontend Pipeline Stacks (approve the permission change requests for each stack deployment):**
  `cdk deploy --context action=bootstrapDeploy TestFrontendPipelineStack BetaFrontendPipelineStack ProdFrontendPipelineStack`

### Subsequent production deploys

Once the pipelines are established with the above steps, deployments will be automatically handled:

- Pushes to the `development` branch will trigger the test backend pipeline, which will then trigger the test frontend
  pipeline
- Pushes to the `main` branch will trigger both the beta and production backend pipelines, which will then trigger
  their respective frontend pipelines.

### Useful commands

* `cdk ls`          list all stacks in the app
* `cdk synth`       emits the synthesized CloudFormation template
* `cdk deploy`      deploy this stack to your default AWS account/region
* `cdk diff`        compare deployed stack with current state
* `cdk docs`        open CDK documentation

## Decommissioning
[Back to top](#compact-connect-ui---backend-developer-documentation)

You can tear down resources associated with any of the CloudFormation stacks for this application with
`cdk destroy <stack-name>`. Most resources in frontend infrastructure can be deleted with the stack, however some data
storage resources, such as the access logs bucket, may not be configured to delete with the stack, depending on your
removal policy. You can identify any resources that weren't destroyed by watching the stack deletion from the AWS
CloudFormation Console, then looking at the resources after its delete is complete, to look for any with a
`Delete Skipped` status.

## More Info
[Back to top](#compact-connect-ui---backend-developer-documentation)

- [cdk-workshop](https://cdkworkshop.com/): If you are new to CDK, I highly recommend you go through the CDK Workshop
  for a quick introduction to the technology and its concepts before getting too deep into any particular project.
