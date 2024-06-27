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
- **[Decommissioning](#decommissioning)**
- **[More Info](#more-info)**

## Prerequisites
[Back to top](#compact-connect---backend-developer-documentation)

To deploy this app, you will need:
1) Access to an AWS account
2) Python>=3.12 installed on your machine, preferably through a virtual environment management tool like [pyenv](https://github.com/pyenv/pyenv),
   for clean management of virtual environments across multiple Python versions.
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

At this point you can now synthesize the CloudFormation template(s) for this code.

```
$ cdk synth
```

For development work there are additional requirements in `requirements-dev.txt` to install with
`pip install -r requirements.txt`.

To add additional dependencies, for example other CDK libraries, just add them to the `requirements.in` file and rerun
`pip-compile requirements.in`, then `pip install -r requirements.txt` command.

## Local Development
[Back to top](#compact-connect---backend-developer-documentation)

Local development can be done by editing the python code and `cdk.json`. For development purposes, this is simply a
Python project that executes locally. Be sure to install the development requirements:

```
pip install -r requirements-dev.txt
```

If you want to deploy this app to see how it runs in the cloud, you can do so by configuring context for your own
sandbox AWS account with context variables in `cdk.context.json` and running the appropriate `cdk deploy` command.

## Tests
[Back to top](#compact-connect---backend-developer-documentation)

Being a cloud project whose infrastructure is written in Python, establishing tests, using the python `unittest`
library early will be critical to maintaining reliability and velocity. Be sure that any updates you add are covered
by tests, so we don't introduce bugs or cost time identifying testable bugs after deployment. CDK tests are defined
under the [tests](./tests) directory. Runtime code tests should be similarly bundled within the lambda folders. Any
python lambda functions defined in cdk code that uses the `common_constructs.python_function.PythonFunction` construct
will automatically run bundled tests on synthesis to facilitate automated testing of the entire app.

To execute the tests, simply run `bin/run_tests.sh` from this directory.

## Deployment
[Back to top](#compact-connect---backend-developer-documentation)

### First deploy to a Sandbox environment
The very first deploy to a new environment (like your personal sandbox account) requires a few steps to fully set up
its environment:
1) Copy [cdk.context.example.json](./cdk.context.example.json) to `cdk.context.json` and adapt it to your details
   (i.e. replace `<your-name>` with your own name, the account id with your own, etc.)
2) Run `cdk bootstrap` to add some base CDK support infrastructure to your AWS account.
3) Run `cdk deploy --all` to get the initial stack resources deployed.

### Subsequent sandbox deploys:
For any future deploys, everything is set up so a simple `cdk deploy --all` should update all your infrastructure to
reflect the changes in your code.

### First deploy to the production environment
The production environment requires a few steps to fully set up before deploys can be automated. Refer to the
[README.md](../multi-account/README.md) for details on setting up a full multi-account architecture environment. Once
that is done, perform the following steps to deploy the CI/CD pipeline into the appropriate AWS account:
- Have someone with suitable permissions in the GitHub organization that hosts this code navigate to the AWS Console
  for the Deploy account, go to the
  [AWS CodeStar Connections](https://us-east-1.console.aws.amazon.com/codesuite/settings/connections) page and create a
  connection that grants AWS permission to receive GitHub events. Note the identifier of the resulting connection for
  the next step.
- Copy the `cdk.context.example.json` file to `cdk.context.json` and update accounts and other identifiers, including
  the Code Star connection you just had created to match the identifiers for your actual accounts and resources.
- With the [aws-cli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), set up your local
  machine to authenticate against the Deploy account as an administrator.
- Run the `bin/put_ssm_context.sh` script to push relevant content from your `cdk.context.json` script into an SSM
  Parameter Store in your Deploy account.
- Set cli-environment variables `CDK_DEFAULT_ACCOUNT` and `CDK_DEFAULT_REGION` to your deploy account id and
  `us-east-1`, respectively.
- Run the command `cdk deploy PipelineStack` to get the pipeline initial stack resources deployed.

### Subsequent production deploys

Once the pipeline is established with the above steps, deploys will automatically execute to the test and production
environments whenever changes are pushed to the `development` or `main` branches of the repository named in your
`cdk.context.json` file.

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

## More Info
[Back to top](#compact-connect---backend-developer-documentation)

- [cdk-workshop](https://cdkworkshop.com/): If you are new to CDK, I highly recommend you go through the CDK Workshop
  for a quick introduction to the technology and its concepts before getting too deep into any particular project.
