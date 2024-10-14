#/usr/bin/env bash
set -x

# Copy our official API doc to ZAP data
cp backend/compact-connect/docs/api-specification/latest-oas30.json /zap-data/latest-oas30.json

# Log in as a user to get a token
TOKEN="$(cd authenticator; node main.js | jq -r '.accessToken')"

echo "Using token: '$TOKEN'"

docker run \
  -v "$(pwd)/session:/zap/wrk/:rw" \
  -v "$(pwd)/data:/data:ro" \
  -e TOKEN="$TOKEN" \
  -t zaproxy/zap-stable \
  zap.sh -cmd \
  -autorun /data/justin-automation.yml
