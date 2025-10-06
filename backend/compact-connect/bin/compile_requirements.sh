set -e

pip-compile --no-emit-index-url --upgrade --no-strip-extras requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/cognito-backup/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/cognito-backup/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/compact-configuration/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/compact-configuration/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/common/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/common/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/custom-resources/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/custom-resources/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/data-events/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/data-events/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/disaster-recovery/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/disaster-recovery/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/provider-data-v1/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/provider-data-v1/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/purchases/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/purchases/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/staff-user-pre-token/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/staff-user-pre-token/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/staff-users/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/staff-users/requirements.in
bin/sync_deps.sh
