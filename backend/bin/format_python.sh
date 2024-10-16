#!/bin/bash

# Find all Python files in the backend directory and format them using Ruff
# if check flag is passed in, run check without actually formatting the files
if [ "$1" == "--check" ]; then
    echo "checking lint errors on Python files..."
    ruff check $(git ls-files '*.py')
    ruff format --check $(git ls-files '*.py')
elif [ "$1" == "--fix" ]; then
    echo "Fixing all autocorrect errors in Python files..."
    ruff check --fix $(git ls-files '*.py')
    ruff format $(git ls-files '*.py')
# else we just run the formatter
else
    echo "Formatting Python files..."
    # this step is required to sort the imports
    ruff check --select I --fix $(git ls-files '*.py')
    ruff format $(git ls-files '*.py')
fi
