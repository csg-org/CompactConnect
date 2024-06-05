set -e

pip-compile --no-emit-index-url --upgrade requirements.in
pip-compile --no-emit-index-url --upgrade requirements-dev.in
pip-compile --no-emit-index-url --upgrade lambdas/requirements.in
pip-compile --no-emit-index-url --upgrade lambdas/requirements-dev.in
pip-compile --no-emit-index-url --upgrade delete-objects-lambda/requirements.in
pip-compile --no-emit-index-url --upgrade delete-objects-lambda/requirements-dev.in
bin/sync_deps.sh
