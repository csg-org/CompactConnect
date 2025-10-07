set -e

pip-compile --no-emit-index-url --upgrade --no-strip-extras requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras requirements.in
bin/sync_deps.sh
