#!/usr/bin/env bash

user_pool_id='us-east-1_gxBtau7Di'

echo 'Creating client'
client=$(aws cognito-idp create-user-pool-client \
  --user-pool-id "$user_pool_id" \
  --cli-input-json file://user-pool-client.json)

client_id=$(echo "$client" | jq -r '.UserPoolClient.ClientId')
client_secret=$(echo "$client" | jq -r '.UserPoolClient.ClientSecret')

echo "Client '$client_id' created"
echo "Client secret: '$client_secret'"

read -p 'Press Enter to delete...'

echo "Deleting client"
aws cognito-idp delete-user-pool-client --user-pool-id "$user_pool_id" --client-id "$client_id"
