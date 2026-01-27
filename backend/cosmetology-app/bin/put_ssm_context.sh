# Requires that jq and aws-cli be installed
#
# 1) Copy cdk.context.<environment>-example.json to cdk.context.json
# 2) Edit the values for your configuration
# 3) Configure your aws-cli to connect to your deployment AWS account
# 4) Run this script to push your local configuration to SSM for the pipeline to pick up


# check which context file to put in SSM using argument, can be prod, beta, test, or deploy
if [ -z "$1" ]; then
    echo "Usage: $0 <prod|beta|test|deploy>"
    exit 1
fi

# check if the argument is valid
if [ "$1" != "prod" ] && [ "$1" != "beta" ] && [ "$1" != "test" ] && [ "$1" != "deploy" ]; then
    echo "Invalid argument: $1"
    echo "Usage: $0 <prod|beta|test|deploy>"
    exit 1
fi

# put the context file into SSM
echo "Reading configuration from cdk.context.json (ensure you've copied from cdk.context.$1-example.json)"
val="$(jq '.ssm_context' <cdk.context.json)"
aws ssm put-parameter --type String --name "$1-cosmetology-context" --value "$val" --overwrite
