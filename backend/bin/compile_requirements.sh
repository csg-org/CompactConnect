set -e

pip-compile --no-emit-index-url --upgrade --no-strip-extras multi-account/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras multi-account/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/attestations/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/attestations/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/common/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/common/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/custom-resources/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/custom-resources/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/data-events/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/data-events/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/provider-data-v1/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/provider-data-v1/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/purchases/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/purchases/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/staff-user-pre-token/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/staff-user-pre-token/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/staff-users/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras compact-connect/lambdas/python/staff-users/requirements.in
bin/sync_deps.sh
