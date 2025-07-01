#!/usr/bin/env python3
# ruff: noqa: I001
"""
This script runs all Python tests in a unified pytest session, which allows coverage data collection to properly merge
across multiple test suites.

Note: This should be run from the 'backend' directory.
"""

import os
import sys
import webbrowser
from argparse import ArgumentParser
from pathlib import Path

import pytest

from coverage import Coverage

# Get the absolute path to the backend directory
BACKEND_DIR = Path(__file__).parent.parent.absolute()

# Define the test directories to include
TEST_DIRS = (
    'compact-connect/lambdas/python/common',
    'compact-connect/lambdas/python/cognito-backup',
    'compact-connect/lambdas/python/compact-configuration',
    'compact-connect/lambdas/python/custom-resources',
    'compact-connect/lambdas/python/data-events',
    'compact-connect/lambdas/python/migration',
    'compact-connect/lambdas/python/provider-data-v1',
    'compact-connect/lambdas/python/purchases',
    'compact-connect/lambdas/python/staff-user-pre-token',
    'compact-connect/lambdas/python/staff-users',
    'compact-connect',  # CDK tests
    'multi-account/control-tower',
    'multi-account/log-aggregation',
    'multi-account/backups',  # Data retention backup infrastructure
)


def get_coverage():
    # Initialize coverage.py with the existing .coveragerc
    return Coverage(
        config_file=BACKEND_DIR / '.coveragerc',
        # Coverage data in memory
        data_file=None,
    )


def clean_modules():
    """
    Clean up modules between test runs to prevent cross-contamination.
    This is especially important for modules like config that maintain state.
    """
    # List of module prefixes to clean up
    modules_to_clean = ['cc_common', 'common_test', 'handlers', 'tests']

    for module_name in list(sys.modules.keys()):
        for prefix in modules_to_clean:
            if module_name == prefix or module_name.startswith(f'{prefix}.'):
                del sys.modules[module_name]

    # Delete local modules after each run so we don't use cached modules and hit name clashes between tests
    for local_dir in [*os.listdir()]:
        # Remove the .py extension from the local file name
        local_dir = local_dir.split('.py', 1)[0]
        if local_dir.isidentifier():
            for m in sorted(sys.modules.keys()):
                if m.startswith(local_dir):
                    del sys.modules[m]


def run_tests(cov: Coverage, args):
    cov.start()

    # Track overall test result
    exit_code = 0
    try:
        # Prepare pytest arguments
        pytest_args = ['tests', '--tb=short', '-W', 'ignore']
        if args.verbose > 0:
            pytest_args.append(f'-{"v" * args.verbose}')

        # Run tests for each directory with the correct working directory
        for test_dir in TEST_DIRS:
            dir_path = BACKEND_DIR / test_dir
            if not dir_path.exists():
                sys.stdout.write(f'Warning: Directory {dir_path} does not exist, skipping\n')
                continue

            tests_dir = dir_path / 'tests'
            if not tests_dir.exists():
                sys.stdout.write(f'Warning: Tests directory {tests_dir} does not exist, skipping\n')
                continue

            sys.stdout.write('\n' + '=' * 80 + '\n')
            sys.stdout.write(f'Running tests in {test_dir}\n')
            sys.stdout.write('=' * 80 + '\n')

            # Save the original working directory and sys.path
            original_dir = os.getcwd()
            original_path = sys.path.copy()
            original_env = os.environ.copy()

            try:
                # Change to the test directory
                os.chdir(dir_path)

                # Set up PYTHONPATH for common code if needed
                if test_dir != 'compact-connect/lambdas/python/common' and 'python' in test_dir:
                    common_path = BACKEND_DIR / 'compact-connect/lambdas/python/common'
                    if str(common_path) not in sys.path:
                        sys.path.insert(0, str(common_path))

                # Clean up modules before running tests
                clean_modules()

                # Run pytest for this directory
                test_result = pytest.main(pytest_args)

                # Update exit code if any tests fail
                if test_result != 0 and exit_code == 0:
                    return test_result

                # Restore the original environment
                os.environ = original_env  # noqa: B003

                # Thorough module cleanup after each test suite
                clean_modules()

            finally:
                # Restore the original working directory
                os.chdir(original_dir)

                # Restore the original sys.path
                sys.path = original_path
    finally:
        # Stop coverage measurement
        cov.stop()
        cov.save()

    return exit_code


def main():
    parser = ArgumentParser(description='Run all Python tests in a unified pytest session')
    parser.add_argument('--report', action='store_true', help='Generate HTML coverage report')
    parser.add_argument('--open-report', action='store_true', help='Open HTML coverage report after generation')
    parser.add_argument('--fail-under', type=float, default=90, help='Fail if coverage is under this percentage')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Increase verbosity')
    args = parser.parse_args()

    cov = get_coverage()
    exit_code = run_tests(cov, args)

    # Generate coverage report if requested
    if args.report:
        sys.stdout.write('\nGenerating coverage report...\n')
        cov.html_report()

        if args.open_report:
            # Open the coverage report
            report_path = BACKEND_DIR / 'coverage' / 'index.html'
            webbrowser.open(f'file://{report_path}')

        # Check coverage against threshold
        sys.stdout.write('\nCalculating coverage...\n')
        coverage_percent = cov.report()
        if coverage_percent < args.fail_under:
            sys.stdout.write(
                f'Coverage {coverage_percent:.2f}% is below the required threshold of {args.fail_under:.2f}%\n'
            )
            exit_code = 1

    if exit_code > 0:
        sys.stdout.write('\n================= TESTS FAILED =================\n')
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
