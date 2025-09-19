set -e

pip-compile --no-emit-index-url --upgrade --no-strip-extras backups/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras backups/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras control-tower/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras control-tower/requirements.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras log-aggregation/requirements-dev.in
pip-compile --no-emit-index-url --upgrade --no-strip-extras log-aggregation/requirements.in
bin/sync_deps.sh
