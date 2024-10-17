#/usr/bin/env bash
set -e

# Copy our official API doc to ZAP data
cp backend/compact-connect/docs/api-specification/latest-oas30.json owasp-zap/data/latest-oas30.json

# Log in as a user to get a token
TOKEN="$(cd owasp-zap/authenticator; node main.js | jq -r '.accessToken')"

[[ -z "$TOKEN" ]] && echo "Failed to get token" && exit 1

docker run \
  -v "$(pwd):/zap/wrk:rw" \
  -e ZAP_AUTH_HEADER_VALUE="$TOKEN" \
  -t zaproxy/zap-stable \
  zap.sh -cmd \
  -autorun /zap/wrk/owasp-zap/data/test-automation.yml

RESULT="$?"
if [[ "$RESULT" -eq 0 ]]; then
  echo "ZAP scan passed"
else
  echo "ZAP scan FAILED"
  exit "$RESULT"
fi
