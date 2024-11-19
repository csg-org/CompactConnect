# To disable the report, provide basically anything as a first argument
set -e
REPORT="$1"

# Run NodeJS tests first
(
  cd compact-connect/lambdas/nodejs/ingest-event-reporter
  yarn test || exit "$?"
  if [ -z "$REPORT" ]; then
    open 'coverage/lcov-report/index.html'
  fi
)

# Run CDK tests, tracking code coverage in a new, combined, data file
(
  cd compact-connect
  pytest --cov=. --cov-config=.coveragerc tests
) || exit "$?"
for dir in \
  compact-connect/lambdas/python/common \
  compact-connect/lambdas/python/custom-resources \
  compact-connect/lambdas/python/data-events \
  compact-connect/lambdas/python/provider-data-v1 \
  compact-connect/lambdas/python/purchases \
  compact-connect/lambdas/python/staff-user-pre-token \
  compact-connect/lambdas/python/staff-users \
  multi-account
  do
  (
    cd "$dir"
    echo "Running tests in $dir"
    # update the PYTHONPATH to include the shared code if not common-python
    [ "$dir" = "compact-connect/lambdas/python/common" ] || export PYTHONPATH=../common
    # Run lambda tests, appending data to the same data file
    pytest --cov=. --cov-config=.coveragerc --cov-append tests
  ) || exit "$?"
done

# Run a coverage report with the combined data
coverage html --fail-under=90
EXIT=$?
if [ -z "$REPORT" ]; then
  open 'coverage/index.html'
fi

exit "$EXIT"
