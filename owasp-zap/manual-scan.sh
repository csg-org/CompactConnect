#!/usr/bin/env bash
#
# Runs the ZAP automation scan in Docker against the test environment.
# Pulls bearer tokens for each credential set defined in owasp-zap/authenticator/.env
# (STAFF_*, PROVIDER_*, STATE_*). Missing credential sets are skipped with a warning —
# the scan will still run, but endpoints needing the missing token will return 401.
set -e

cd "$(dirname "$0")/.."

authenticator_dir="owasp-zap/authenticator"
env_file="$authenticator_dir/.env"

if [[ ! -f "$env_file" ]]; then
    echo "Missing $env_file. Copy .env.example and fill in credentials." >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
. "$env_file"
set +a

fetch_user_token() {
    local mode="$1"
    local prefix="$2"
    local pool_id_var="${prefix}_COGNITO_USER_POOL_ID"
    if [[ -z "${!pool_id_var:-}" ]]; then
        echo "Skipping $mode token: ${prefix}_COGNITO_* vars not set in $env_file" >&2
        return 1
    fi
    # Provider API handlers require the ID token (claims like email/username);
    # staff API accepts the access token.
    local token_field='.accessToken'
    if [[ "$mode" == 'provider' ]]; then
        token_field='.idToken'
    fi
    (cd "$authenticator_dir" && node main.js --mode="$mode") | jq -r "$token_field"
}

fetch_m2m_token() {
    if [[ -z "${COGNITO_STATE_AUTH_DOMAIN:-}" ]]; then
        echo "Skipping state M2M token: COGNITO_STATE_AUTH_DOMAIN not set in $env_file" >&2
        return 1
    fi
    (cd "$authenticator_dir" && ./get-m2m-token.sh)
}

STAFF_TOKEN=$(fetch_user_token staff STAFF || true)
PROVIDER_TOKEN=$(fetch_user_token provider PROVIDER || true)
STATE_TOKEN=$(fetch_m2m_token || true)

if [[ -z "$STAFF_TOKEN$PROVIDER_TOKEN$STATE_TOKEN" ]]; then
    echo "No tokens obtained; aborting." >&2
    exit 1
fi

docker run \
  -v "$(pwd):/zap/wrk:rw" \
  -e ZAP_AUTH_STAFF_TOKEN="$STAFF_TOKEN" \
  -e ZAP_AUTH_PROVIDER_TOKEN="$PROVIDER_TOKEN" \
  -e ZAP_AUTH_STATE_TOKEN="$STATE_TOKEN" \
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
