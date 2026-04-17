#!/usr/bin/env bash
#
# Fetches a Cognito client_credentials access token for the State Auth M2M pool.
# Prints only the access_token to stdout on success.
#
# Requires:
#   COGNITO_STATE_AUTH_DOMAIN — e.g. compact-connect-state-auth-test.auth.us-east-1.amazoncognito.com
#   STATE_AUTH_CLIENT_ID
#   STATE_AUTH_CLIENT_SECRET
#   STATE_AUTH_SCOPES — space-separated list, e.g. "aslp/readGeneral ky/aslp.write"

set -euo pipefail

: "${COGNITO_STATE_AUTH_DOMAIN:?COGNITO_STATE_AUTH_DOMAIN is required}"
: "${STATE_AUTH_CLIENT_ID:?STATE_AUTH_CLIENT_ID is required}"
: "${STATE_AUTH_CLIENT_SECRET:?STATE_AUTH_CLIENT_SECRET is required}"
: "${STATE_AUTH_SCOPES:?STATE_AUTH_SCOPES is required}"

response=$(curl -sS --fail-with-body \
    -X POST "https://${COGNITO_STATE_AUTH_DOMAIN}/oauth2/token" \
    -u "${STATE_AUTH_CLIENT_ID}:${STATE_AUTH_CLIENT_SECRET}" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "scope=${STATE_AUTH_SCOPES}")

token=$(jq -r '.access_token // empty' <<<"$response")
if [[ -z "$token" ]]; then
    echo "Failed to obtain M2M token. Response: $response" >&2
    exit 1
fi
printf '%s' "$token"
