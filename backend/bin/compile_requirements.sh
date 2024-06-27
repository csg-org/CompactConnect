set -e

pip-compile --no-emit-index-url --upgrade requirements.in
pip-compile --no-emit-index-url --upgrade requirements-dev.in
pip-compile --no-emit-index-url --upgrade lambdas/license-data/requirements.in
pip-compile --no-emit-index-url --upgrade lambdas/license-data/requirements-dev.in
pip-compile --no-emit-index-url --upgrade lambdas/board-user-pre-token/requirements.in
pip-compile --no-emit-index-url --upgrade lambdas/board-user-pre-token/requirements-dev.in
pip-compile --no-emit-index-url --upgrade lambdas/delete-objects/requirements.in
pip-compile --no-emit-index-url --upgrade lambdas/delete-objects/requirements-dev.in
bin/sync_deps.sh
