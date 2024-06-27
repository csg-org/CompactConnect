set -e

pip-compile --no-emit-index-url --upgrade multi-account/requirements.in
pip-compile --no-emit-index-url --upgrade multi-account/requirements-dev.in
pip-compile --no-emit-index-url --upgrade compact-connect/requirements.in
pip-compile --no-emit-index-url --upgrade compact-connect/requirements-dev.in
pip-compile --no-emit-index-url --upgrade compact-connect/lambdas/license-data/requirements.in
pip-compile --no-emit-index-url --upgrade compact-connect/lambdas/license-data/requirements-dev.in
pip-compile --no-emit-index-url --upgrade compact-connect/lambdas/board-user-pre-token/requirements.in
pip-compile --no-emit-index-url --upgrade compact-connect/lambdas/board-user-pre-token/requirements-dev.in
pip-compile --no-emit-index-url --upgrade compact-connect/lambdas/delete-objects/requirements.in
pip-compile --no-emit-index-url --upgrade compact-connect/lambdas/delete-objects/requirements-dev.in
bin/sync_deps.sh
