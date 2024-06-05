# To disable the report, provide basically anything as a first argument
REPORT="$1"

# Run CDK tests, tracking code coverage in a new data file
pytest --cov=. --cov-config=.coveragerc tests || exit "$?"
for dir in lambdas delete-objects-lambda; do
  (
    cd "$dir"
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
