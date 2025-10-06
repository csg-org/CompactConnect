(
  cd lambdas/nodejs
  yarn install
)

pip-sync \
  requirements-dev.txt \
  requirements.txt
