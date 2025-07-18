(
  cd compact-connect/lambdas/nodejs
  yarn install
)

pip-sync \
  multi-account/control-tower/requirements-dev.txt \
  multi-account/control-tower/requirements.txt \
  multi-account/log-aggregation/requirements-dev.txt \
  multi-account/log-aggregation/requirements.txt \
  compact-connect/requirements-dev.txt \
  compact-connect/requirements.txt \
  compact-connect/lambdas/python/cognito-backup/requirements-dev.txt \
  compact-connect/lambdas/python/cognito-backup/requirements.txt \
  compact-connect/lambdas/python/compact-configuration/requirements-dev.txt \
  compact-connect/lambdas/python/compact-configuration/requirements.txt \
  compact-connect/lambdas/python/common/requirements-dev.txt \
  compact-connect/lambdas/python/common/requirements.txt \
  compact-connect/lambdas/python/custom-resources/requirements-dev.txt \
  compact-connect/lambdas/python/custom-resources/requirements.txt \
  compact-connect/lambdas/python/data-events/requirements-dev.txt \
  compact-connect/lambdas/python/data-events/requirements.txt \
  compact-connect/lambdas/python/provider-data-v1/requirements-dev.txt \
  compact-connect/lambdas/python/provider-data-v1/requirements.txt \
  compact-connect/lambdas/python/purchases/requirements-dev.txt \
  compact-connect/lambdas/python/purchases/requirements.txt \
  compact-connect/lambdas/python/staff-user-pre-token/requirements-dev.txt \
  compact-connect/lambdas/python/staff-user-pre-token/requirements.txt \
  compact-connect/lambdas/python/staff-users/requirements-dev.txt \
  compact-connect/lambdas/python/staff-users/requirements.txt
