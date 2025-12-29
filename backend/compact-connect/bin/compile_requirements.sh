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
# The purchases lambda requires Python<=3.12, which is older than everything else in this project, so we have
# to install that separately, if we want to be developing with Python>=3.13 for the rest of the project, to
# avoid installation failures
# pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/purchases/requirements-dev.in
# pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/purchases/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/search/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/search/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/staff-user-pre-token/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/staff-user-pre-token/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/staff-users/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras lambdas/python/staff-users/requirements.in
bin/sync_deps.sh
