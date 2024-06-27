# Requires that jq and aws-cli be installed
#
# 1) Copy cdk.context.example.json to cdk.context.json
# 2) Edit the values for your configuration
# 3) Configure your aws-cli to connect to your deployment AWS account
# 4) Run this script to push your local configuration to SSM for the pipeline to pick up

val="$(jq '.ssm_context' <cdk.context.json)"
aws ssm put-parameter --type String --name 'compact-connect-context' --value "$val" --overwrite
