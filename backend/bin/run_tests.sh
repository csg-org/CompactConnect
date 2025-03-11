#!/bin/bash
set -e

# Default values
LANGUAGE="all"
REPORT=true
OPEN_REPORT=true
VERBOSE=""
FAIL_UNDER=90

# Print usage information
usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -l, --language LANG   Specify language to test (nodejs, python, all) [default: all]"
  echo "  -n, --no-report       Don't generate coverage report"
  echo "  -o, --no-open         Don't open coverage report in browser"
  echo "  -v, --verbose         Increase python verbosity (can be used multiple times: -vv)"
  echo "  -f, --fail-under PCT  Set minimum python coverage percentage [default: 90]"
  echo "  -h, --help            Display this help message"
  exit 1
}

# Parse command line arguments
while getopts "l:nov:f:h-:" opt; do
  case $opt in
    -)
      case "${OPTARG}" in
        language)
          LANGUAGE="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ))
          ;;
        no-report)
          REPORT=false
          ;;
        no-open)
          OPEN_REPORT=false
          ;;
        verbose)
          VERBOSE="v${VERBOSE}"
          ;;
        fail-under)
          FAIL_UNDER="${!OPTIND}"; OPTIND=$(( $OPTIND + 1 ))
          ;;
        help)
          usage
          ;;
        *)
          echo "Invalid option: --${OPTARG}" >&2
          usage
          ;;
      esac
      ;;
    l)
      LANGUAGE="$OPTARG"
      ;;
    n)
      REPORT=false
      ;;
    o)
      OPEN_REPORT=false
      ;;
    v)
      VERBOSE="v${VERBOSE}"
      ;;
    f)
      FAIL_UNDER="$OPTARG"
      ;;
    h)
      usage
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      usage
      ;;
  esac
done

# Validate language argument
if [[ "$LANGUAGE" != "nodejs" && "$LANGUAGE" != "python" && "$LANGUAGE" != "all" ]]; then
  echo "Error: Language must be 'nodejs', 'python', or 'all'" >&2
  usage
fi

# Set this to 1 ahead of running tests, so this script will fail if neither node or python tests ran
EXIT=1

# Run NodeJS tests if requested
if [[ "$LANGUAGE" == 'nodejs' || "$LANGUAGE" == 'all' ]]; then
  echo "Running NodeJS tests..."
  (
    cd compact-connect/lambdas/nodejs
    yarn test || exit "$?"
    if [[ "$REPORT" == true && "$OPEN_REPORT" == true ]]; then
      open 'coverage/lcov-report/index.html'
    fi
  ) || exit "$?"
  # If this didn't exit already, we'll set our exit status to success for now
  EXIT=0
fi

# Run Python tests if requested
if [[ "$LANGUAGE" == 'python' || "$LANGUAGE" == 'all' ]]; then
  echo "Running Python tests..."

  # Build Python test arguments
  PYTHON_ARGS=()

  # Add report flags
  if [[ "$REPORT" == true ]]; then
    PYTHON_ARGS+=("--report")
    if [[ "$OPEN_REPORT" == true ]]; then
      PYTHON_ARGS+=("--open-report")
    fi
  fi

  # Add verbosity flag
  if [[ -n "$VERBOSE" ]]; then
    PYTHON_ARGS+=("-${VERBOSE}")
  fi

  # Add fail-under threshold
  PYTHON_ARGS+=("--fail-under" "$FAIL_UNDER")

  # Run the Python tests
  python3 bin/run_python_tests.py "${PYTHON_ARGS[@]}" || exit "$?"
  EXIT=0
fi

exit "$EXIT"
