# Multi-Account Architecture

This [CDK](https://aws.amazon.com/cdk/) project automates initial set up of the multi-account architecture that
CompactConnect is designed to operate within. This set-up should be a one time process, with both some CDK and manual
steps, combined. Below are step-by-step instructions for setting up the AWS environment. Note that these instructions
cover a lot of ground and are expected to be carried out by a technical person with relevant experience, so the
instructions do not cover every detail.


## Environment Setup
1) [Provision an AWS account to serve as the root of an AWS Organization](#provision-root-account)
2) [Deploy the multi-account app](#deploy-the-multi-account-app) to provision the core ControlTower
   LandingZone/Organization and controls.
3) [Set up IAM Identity Center](#set-up-iam-identity-center)
4) [Provision new workflow AWS accounts and OUs](#provision-workflow-accounts)
5) [Disable Root in all OUs](#disallow-root)
6) Create an access-logs s3 bucket in the logs account to serve as a log replication target from across the
   organization. _FURTHER DETAILS TBD_.
7) [Bootstrap the workflow accounts](#bootstrap-the-workflow-accounts)

### Provision root account
Work with your IT department (as applicable) to provision a single AWS account that will serve as the root of your
new AWS organization that we will set up here. Have them:
- Set up the appropriate support level (Business or better is recommended before any production workloads are live)
- Set the root account MFA device
- Provision you one IAM User with Admin access (we will delete this later after moving to a more secure option)
- [Enable IAM Billing access](https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_billing.html#tutorial-billing-activate) - only Step 1 is required.

### Deploy the multi-account app
- For this section, work within the `backend/multi-account` directory
- Copy `cdk.context.example.json` to `cdk.context.json`
- Update the `account_id` field to your new root account id.
- Update the `account_name_prefix` to a common name prefix you would like to use for the core AWS account names
- Update the `email_domain` to an email domain you control
- You will need email distribution lists to correspond to new AWS accounts you will create as part of this set-up.
  Create (or have your IT department create) email distribution lists that allow external senders by the following
  names:
  - `<account_name_prefix>-logs@<email_domain>`
  - `<account_name_prefix>-audit@<email_domain>`
  - `<account_name_prefix>-deploy@<email_domain>`
  - `<account_name_prefix>-prod@<email_domain>`
  - `<account_name_prefix>-test@<email_domain>`
- Configure your local CLI to use your new IAM User admin credentials.
- Install the requirements in `requirements.txt` into your local python environment.
- Run `cdk bootstrap` to provision some CDK support infrastructure into your account.
- Run `cdk deploy --all` to deploy this app

### Set Up IAM Identity Center
- Log into the AWS Console for the management account, using your IAM User.
- Go to the IAM Identity Center service, Settings, Configure multi-factor authentication, then check the following
  settings:
  - Prompt users for MFA: Every time they sign in
  - Users Can authenticate with these MFA types: Check both options
  - If a user does not yet have a registered MFA device: Require them to register an MFA device at sign in
- Go to the IAM Identity Center service, Users view, and add a user for yourself
- Add yourself to the AWSControlTowerAdmins group
- You should receive an invite email from AWS. Log out as the IAM user and use the new link to set up your IAM Identity
  Center user.
- Configure your cli to
  [use refreshable tokens via SSO](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- Once you have confirmed that you have access to the console and cli via your new IAM Identity Center user, delete the
  IAM User created for you.

### Provision workflow accounts
- Log into the AWS Management account console via your IAM Identity Center user
- Go to the ControlTower service, Organization view
- Create a new OU structure as follows:
```text
└── Workflows
    ├── Deployment
    ├── PreProd
    └── Prod
```
- Go to the ControlTower service, Account factory view
- Create three new AWS accounts for the OUs in the following structure, with the following details. Use the
  corresponding email distribution list as the account address, the names in the following structure for Display name,
  and your own IAM Identity Center user for Access configuration:
```text
└── Workflows
    ├── Deployment
    │   └── Deploy
    ├── PreProd
    │   └── Test
    └── Prod
        └── Production
```
- Go to the IAM Identity Center service, Groups view
- Create a new group called CSGAdmins and add yourself
- Create a new group called CSGReadOnly and add yourself
- Go to the IAM Identity Center service, AWS Accounts view, check all AWS Accounts under the Workflow OU and select
  Assign users or groups
- Select the CSGAdmin group, and the `AWSAdministratorAccess` permission set
- Select all the accounts under the Workflow OU and select Assign users or groups
- Select the CSGReadOnly group, and the `AWSReadOnlyAccess` permission set
- In the future, add any new IAM Identity Center users to these groups as appropriate (or create even more groups, with
  more granular permissions, as needed).

### Disallow Root
- Log into the AWS Management account console via your IAM Identity Center user
- Go to the ControlTower service, All Controls view
- Search for 'root' and check the `[AWS-GR_RESTRICT_ROOT_USER] Disallow actions as a root user` control
- At the top right of the page, select Control Actions, Enable
- Select every Organizational Unit available, then select Enable Controls

### Bootstrap the workflow accounts
- Configure your cli and CDK to use the new Deploy account via your IAM Identity Center user
- Make note of your Deploy AWS account ID
- Run `cdk bootstrap <deploy account id>/us-east-1`
- For your Test and Production accounts:
  - Configure your CLI to use the account
  - Run `cdk bootstrap <target account>/us-east-1 --trust <deploy account> --trust-for-lookup <deploy account> --cloudformation-execution-policies 'arn:aws:iam::aws:policy/AdministratorAccess'`
