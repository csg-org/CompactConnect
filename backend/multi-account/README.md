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
7) [Bootstrap the deploy account](#bootstrap-the-deploy-account)
8) [Deploy the pipeline stacks](#deploy-the-pipeline-stacks)
9) [Bootstrap the application accounts](#bootstrap-the-application-accounts)

### Provision root account
Work with your IT department (as applicable) to provision a single AWS account that will serve as the root of your
new AWS organization that we will set up here. Have them:
- Set up the appropriate support level (Business or better is recommended before any production workloads are live)
- Set the root account MFA device
- Provision you one IAM User with Admin access (we will delete this later after moving to a more secure option)
- [Enable IAM Billing access](https://docs.aws.amazon.com/IAM/latest/UserGuide/tutorial_billing.html#tutorial-billing-activate) - only Step 1 is required.

### Deploy the multi-account app
- For this section, work within the `backend/multi-account/control-tower` directory
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
  - `<account_name_prefix>-prod-secondary@<email_domain>` (for backups and disaster recovery)
  - `<account_name_prefix>-beta@<email_domain>`
  - `<account_name_prefix>-test@<email_domain>`
  - `<account_name_prefix>-test-secondary@<email_domain>` (for backups and disaster recovery)
- Configure your local CLI to use your new IAM User admin credentials.
- Install the requirements in `requirements.txt` into your local python environment.
- If this is your first time deploying, run `cdk bootstrap` to provision some CDK support infrastructure into your account.
- If this is not your first time deploying, run `cdk diff` and verify the changes that will be applied.
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
- Create a new OU structure as follows. Each compact gets its own OU under `Workflows`, with its own
  `PreProd` and `Prod` sub-OUs inside it. Name the compact-level OU after the compact (e.g. `CompactConnect`
  for the initial JCC compact):
```text
└── Workflows
    ├── Deployment
    └── CompactConnect
        ├── PreProd
        └── Prod
```
- Go to the ControlTower service, Account factory view
- Create six new AWS accounts for the OUs in the following structure, with the following details. Use the
  corresponding email distribution list as the account address, the names in the following structure for Display name,
  and your own IAM Identity Center user for Access configuration:
```text
└── Workflows
    ├── Deployment
    │   └── Deploy
    └── CompactConnect
        ├── PreProd
        │   ├── Test
        │   ├── Test Secondary (Backups and Disaster Recovery)
        │   └── Beta
        └── Prod
            ├── Production
            └── Production Secondary (Backups and Disaster Recovery)
```
- Go to the IAM Identity Center service, Groups view
- Create a new group called CSGAdmins and add yourself
- Create a new group called CSGReadOnly and add yourself
- Go to the IAM Identity Center service, AWS Accounts view, check all AWS Accounts under the compact's OU
  (e.g. `Workflows/CompactConnect`) and the Deploy account and select Assign users or groups
- Select the CSGAdmin group, and the `AWSAdministratorAccess` permission set
- Select all those same accounts and select Assign users or groups again
- Select the CSGReadOnly group, and the `AWSReadOnlyAccess` permission set
- In the future, add any new IAM Identity Center users to these groups as appropriate (or create even more groups, with
  more granular permissions, as needed).

### Configure Permission Set Inline Policies
To enhance security, configure inline policies on IAM Identity Center permission sets to restrict certain actions:

#### Lambda Function Code Update Protection and Resource Deletion Prevention
We do not want users updating runtime code or deleting critical resources outside of our CI/CD review and deployment process. Apply the following inline policy to the `AWSPowerUserAccess` permission set.

1. Log into the AWS Management account console via your IAM Identity Center user
2. Go to the IAM Identity Center service, Permission sets view
3. Select the `AWSPowerUserAccess` permission set
4. Go to the Permissions tab, then select "Create inline policy"
5. Choose JSON and paste the following policy:

```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "DenyComputeAndBackupUpdates",
			"Effect": "Deny",
			"Action": [
                "ec2:RunInstances",
				"lambda:Delete*",
				"lambda:Create*",
				"lambda:Update*",
				"lambda:Put*",
				"lambda:Publish*",
				"lambda:Add*",
				"lambda:Remove*",
				"backup:Create*",
				"backup:Copy*",
				"backup:Delete*",
				"backup:Start*",
				"backup:Put*",
				"backup:Stop*",
				"backup:Disassociate*",
				"backup:Cancel*",
				"backup:Revoke*",
				"backup:Associate*",
				"backup:Update*",
				"states:Create*",
				"states:Update*",
				"states:Publish*",
				"states:Delete*"
			],
			"Resource": [
				"*"
			]
		},
		{
			"Sid": "DenyResourceModification",
			"Effect": "Deny",
			"Action": [
                "dynamodb:BatchWriteItem",
				"dynamodb:Delete*",
				"s3:Delete*",
				"s3:Create*",
				"s3:Put*",
				"s3:Replicate*",
				"s3:Update*",
				"events:Delete*",
				"sqs:DeleteQueue",
				"sns:Delete*",
				"ses:Delete*",
				"ses:Update*",
				"cognito-idp:DeleteUserPool",
				"cognito-idp:DeleteUserPoolDomain",
				"cognito-idp:DeleteGroup",
				"cognito-idp:DeleteIdentityProvider",
				"cognito-idp:DeleteResourceServer",
				"cognito-idp:DeleteManagedLoginBranding",
				"ec2:DeleteVpc",
				"ec2:DeleteSubnet",
				"ec2:DeleteSecurityGroup",
				"ec2:DeleteInternetGateway",
				"ec2:DeleteNatGateway",
				"ec2:DeleteRouteTable",
				"ec2:DeleteRoute",
				"ec2:DeleteNetworkAcl",
				"ec2:DeleteNetworkAclEntry",
				"ec2:DeleteVpnConnection",
				"ec2:DeleteVpnGateway",
				"ec2:DeleteVpcEndpointServiceConfigurations",
				"ec2:DeleteVpcPeeringConnection",
				"ec2:DeleteFlowLogs",
				"ec2:DeleteEgressOnlyInternetGateway",
				"kms:ScheduleKeyDeletion",
				"kms:Disable*",
				"kms:Delete*",
				"secretsmanager:Delete*",
				"apigateway:DELETE",
				"apigateway:PATCH",
				"apigateway:PUT",
				"apigateway:POST",
				"apigateway:RemoveCertificateFromDomain",
				"apigateway:SetWebACL",
				"apigateway:Update*",
				"es:Delete*"
			],
			"Resource": [
				"*"
			]
		}
	]
}
```

6. Name the policy `DenyComputeBackupAndResourceModifications`
7. Select "Create policy"
8. The policy will automatically apply to all users assigned to the `AWSPowerUserAccess` permission set

This policy prevents power users from:
- Modifying Lambda functions, Step Functions, and backup resources
- Deleting critical infrastructure resources
- Modifying S3 bucket configurations and API Gateway resources

### Disallow Root
- Log into the AWS Management account console via your IAM Identity Center user
- Go to the ControlTower service, All Controls view
- Search for 'root' and check the `[AWS-GR_RESTRICT_ROOT_USER] Disallow actions as a root user` control
- At the top right of the page, select Control Actions, Enable
- Select every Organizational Unit available, then select Enable Controls

### Bootstrap the deploy account
- Configure your cli and CDK to use the new Deploy account via your IAM Identity Center user
- Make note of your Deploy AWS account ID and region (typically `us-east-1`)
- Run `cdk bootstrap <deploy account id>/us-east-1`

### Deploy the pipeline stacks
Before bootstrapping the application accounts, you must deploy the pipeline stacks to create the cross-account roles that the bootstrap templates reference:

- Navigate to the `backend/compact-connect` directory
- Configure your CLI to use the Deploy account
- Follow the pipeline deployment instructions in the [CompactConnect README](../compact-connect/README.md#first-deploy-to-the-production-environment) to deploy:
  - TestBackendPipelineStack and TestFrontendPipelineStack
  - BetaBackendPipelineStack and BetaFrontendPipelineStack
  - ProdBackendPipelineStack and ProdFrontendPipelineStack

**Important**: The pipeline stacks create the cross-account roles (e.g., `CompactConnect-test-Backend-CrossAccountRole`) that the application account bootstrap templates trust. These roles must exist before the bootstrap can succeed.

### Bootstrap the application accounts
For enhanced security, use the secure bootstrap templates that trust only specific pipeline roles instead of the entire deploy account root. Each environment has its own template with hardcoded role names to avoid conflicts.

**Prerequisites**: The pipeline stacks must be deployed first (see step 8 above) because the bootstrap templates reference specific cross-account roles that must exist.

- For your Test, Beta, and Production accounts:
  - Configure your CLI to use the target account
  - Run the secure bootstrap command with environment-specific templates:

  ```bash
  # Run these commands from the backend/compact-connect directory

  # For Test account
  cdk bootstrap <test account>/us-east-1 --force \
    --template resources/bootstrap-stack-test.yaml \
    --trust <deploy account id> \
    --cloudformation-execution-policies 'arn:aws:iam::aws:policy/AdministratorAccess'

  # For Beta account
  cdk bootstrap <beta account>/us-east-1 --force \
    --template resources/bootstrap-stack-beta.yaml \
    --trust <deploy account id> \
    --cloudformation-execution-policies 'arn:aws:iam::aws:policy/AdministratorAccess'

  # For Production account
  cdk bootstrap <prod account>/us-east-1 --force \
    --template resources/bootstrap-stack-prod.yaml \
    --trust <deploy account id> \
    --cloudformation-execution-policies 'arn:aws:iam::aws:policy/AdministratorAccess'
  ```

## Log Aggregation Setup

After setting up the multi-account architecture, you can deploy the log aggregation infrastructure to enable CloudTrail logging for DynamoDB data events:

1. Navigate to the `backend/multi-account/log-aggregation` directory
2. Follow the instructions in the README.md to:
   - Configure the `cdk.context.json` file with your account IDs
   - Deploy the logs account resources to the Logs account
   - Deploy the management account resources to the Management account

This will set up a CloudTrail organization trail that logs read operations on DynamoDB tables with the `-DataEventsLog` suffix across all accounts in the organization.

The logs will be stored in an S3 bucket in the Logs account, and the trail itself will be managed from the Management account.

## Adding a new compact

Each compact runs in its own set of application accounts under the existing AWS Organization, in its own dedicated OU under `Workflows`. The Deploy account is **shared** across all compacts, so you do not provision a new Deploy account when onboarding a new compact. You need to create a new compact-level OU (with `PreProd` and `Prod` sub-OUs inside it), provision the compact's application accounts within those OUs, and stand up the compact's pipeline stacks inside the existing Deploy account.

The following documentation mirrors the process described above for setting up the original JCC compact, but with details specific for new compacts.

### Create email distribution lists for the new compact
Following the same pattern established for the initial compact (see
[Deploy the multi-account app](#deploy-the-multi-account-app)), create (or have your IT department create) email
distribution lists that allow external senders for the new compact's application accounts. Include the compact
identifier in the list name so it is easy to distinguish from the other compacts' accounts. For example, for a
hypothetical `<compact>` compact:
- `cc-<compact>-prod@<email_domain>`
- `cc-<compact>-prod-secondary@<email_domain>` (for backups and disaster recovery)
- `cc-<compact>-beta@<email_domain>`
- `cc-<compact>-test@<email_domain>`
- `cc-<compact>-test-secondary@<email_domain>` (for backups and disaster recovery)

Note you do **not** need a new `-deploy@` distribution list. The Deploy account provisioned during the initial setup is
shared across all compacts.

### Provision the new compact's application accounts
- Log into the AWS Management account console via your IAM Identity Center user
- Go to the ControlTower service, Organization view
- Create a new compact-level OU under `Workflows` named after the compact (e.g. `Cosmetology`), and within it
  create `PreProd` and `Prod` sub-OUs, following the same pattern as the original compact's OU structure
- Go to the ControlTower service, Account factory view
- Create five new AWS accounts within the new compact's OUs.
  Use the corresponding email distribution list from the previous step as the account address, give each account a
  Display name that clearly identifies both the compact and the environment, and assign your own IAM Identity Center
  user for Access configuration. The resulting OU structure should look like the following (the original compact's
  OU is shown for reference, and the new compact's OU sits alongside it):
```text
└── Workflows
    ├── Deployment
    │   └── Deploy                                    (shared, already exists)
    ├── CompactConnect                                (original compact, already exists)
    │   ├── PreProd
    │   │   ├── Test
    │   │   ├── Test Secondary
    │   │   └── Beta
    │   └── Prod
    │       ├── Production
    │       └── Production Secondary
    └── <Compact>                                     (new compact OU)
        ├── PreProd
        │   ├── <Compact> Test                        (new)
        │   ├── <Compact> Test Secondary              (new)
        │   └── <Compact> Beta                        (new)
        └── Prod
            ├── <Compact> Production                  (new)
            └── <Compact> Production Secondary        (new)
```

### Grant IAM Identity Center access to the new accounts
- Go to the IAM Identity Center service, AWS Accounts view
- Select the five newly created application accounts under the new compact's OU (e.g.
  `Workflows/<Compact>/PreProd` and `Workflows/<Compact>/Prod`) and select Assign users or groups
- Assign the existing `CSGAdmins` group with the `AWSAdministratorAccess` permission set
- Select those same accounts again and select Assign users or groups
- Assign the existing `CSGReadOnly` group with the `AWSReadOnlyAccess` permission set
- The `DenyComputeBackupAndResourceModifications` inline policy described in
  [Configure Permission Set Inline Policies](#configure-permission-set-inline-policies) is attached at the permission
  set level, so it automatically applies to the new accounts with no further action.
- The `Disallow actions as a root user` control configured in [Disallow Root](#disallow-root) is enabled at the OU
  level, so it automatically applies to the new compact's OU as well.

### Deploy the new compact's pipeline stacks
The new compact's pipeline stacks are deployed into the **existing** Deploy account alongside the original compact's
pipeline stacks. Each compact's CDK app defines its own set of pipeline stacks (for example, the Cosmetology compact
defines `TestBackendCosmetology`, `BetaBackendCosmetology`, and `ProdBackendCosmetology`), so the pipelines for
different compacts do not collide.

- Navigate to the new compact's CDK project directory (for example, `backend/cosmetology-app` or
  `backend/social-work-app`)
- Follow that project's deployment instructions for the pipelined environments. The Cosmetology compact's instructions
  are a good reference for any new compact and live at
  [Cosmetology README - First deploy to the pipelined environments](../cosmetology-app/README.md#first-deploy-to-the-pipelined-environments).
  In particular, you generally will need to perform the following:
  - Complete the StatSig Feature Flag Setup for each environment (test, beta, prod)
  - Create Route53 hosted zones for the new compact's domain names in each of its Test, Beta, and Production accounts
  - Populate the compact-specific `cdk.context.json` files with the new account IDs and push them to SSM via
    `bin/put_ssm_context.sh <environment>`
  - Configure your CLI to use the Deploy account and run the appropriate `cdk deploy` command to create the new
    compact's pipeline stacks (e.g.
    `cdk deploy --context action=bootstrapDeploy TestBackendCosmetology BetaBackendCosmetology ProdBackendCosmetology`
    for the Cosmetology compact; substitute the equivalent stack names for any other compact)

**Important**: As with the initial compact setup, the new compact's pipeline stacks create cross-account roles in the
Deploy account (e.g. `CompactConnect-test-Cosmetology-CrossAccountRole`) that the new compact's application account
bootstrap templates trust. These pipeline stacks must be deployed before bootstrapping the new compact's application
accounts in the next step.

### Bootstrap the new compact's application accounts
Each compact ships its own custom bootstrap templates that trust only the pipeline roles for that specific compact,
under `<compact-app>/resources/bootstrap-stack-{test,beta,prod}.yaml`. Update the role names in those templates (not the original compact's templates) to reference the new cross-account roles and then use the templates when bootstrapping the new compact's application accounts so the resulting bootstrap roles trust the correct cross-account roles.

- For each of the new compact's Test, Beta, and Production accounts:
  - Configure your CLI to use the target account
  - Run the secure bootstrap command with the new compact's environment-specific template. For example, for the
    Cosmetology compact:

  ```bash
  # Run these commands from the backend/cosmetology-app directory

  # For the new compact's Test account
  cdk bootstrap <new compact test account>/us-east-1 --force \
    --template resources/bootstrap-stack-test.yaml \
    --trust <deploy account id> \
    --cloudformation-execution-policies 'arn:aws:iam::aws:policy/AdministratorAccess'

  # For the new compact's Beta account
  cdk bootstrap <new compact beta account>/us-east-1 --force \
    --template resources/bootstrap-stack-beta.yaml \
    --trust <deploy account id> \
    --cloudformation-execution-policies 'arn:aws:iam::aws:policy/AdministratorAccess'

  # For the new compact's Production account
  cdk bootstrap <new compact prod account>/us-east-1 --force \
    --template resources/bootstrap-stack-prod.yaml \
    --trust <deploy account id> \
    --cloudformation-execution-policies 'arn:aws:iam::aws:policy/AdministratorAccess'
  ```

  For a different compact, run the commands from that compact's CDK project directory and use its
  `resources/bootstrap-stack-*.yaml` templates.

After the secure bootstrap completes, perform the first manual application deploy into each of the new compact's
application accounts and trigger the first pipeline run as described in the compact's README (for the Cosmetology
compact, see
[Cosmetology README - First deploy to the pipelined environments](../cosmetology-app/README.md#first-deploy-to-the-pipelined-environments)).

### Bootstrap the new compact's secondary accounts
The Test Secondary and Production Secondary accounts host the new compact's backups and disaster recovery resources.
See [`backend/multi-account/backups/README.md`](./backups/README.md) for instructions on bootstrapping these secondary
accounts and deploying the backup resources for the new compact.
