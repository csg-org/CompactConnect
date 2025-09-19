(
  cd compact-connect/lambdas/nodejs
  yarn install
)

pip-sync \
  requirements-dev.txt \
  requirements.txt \
  lambdas/python/cognito-backup/requirements-dev.txt \
  lambdas/python/cognito-backup/requirements.txt \
  lambdas/python/compact-configuration/requirements-dev.txt \
  lambdas/python/compact-configuration/requirements.txt \
  lambdas/python/common/requirements-dev.txt \
  lambdas/python/common/requirements.txt \
  lambdas/python/custom-resources/requirements-dev.txt \
  lambdas/python/custom-resources/requirements.txt \
  lambdas/python/data-events/requirements-dev.txt \
  lambdas/python/data-events/requirements.txt \
  lambdas/python/disaster-recovery/requirements-dev.txt \
  lambdas/python/disaster-recovery/requirements.txt \
  lambdas/python/provider-data-v1/requirements-dev.txt \
  lambdas/python/provider-data-v1/requirements.txt \
  lambdas/python/purchases/requirements-dev.txt \
  lambdas/python/purchases/requirements.txt \
  lambdas/python/staff-user-pre-token/requirements-dev.txt \
  lambdas/python/staff-user-pre-token/requirements.txt \
  lambdas/python/staff-users/requirements-dev.txt \
  lambdas/python/staff-users/requirements.txt
