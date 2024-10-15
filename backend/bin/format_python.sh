#!/bin/bash

# Find all Python files in the backend directory and format them using Ruff
# if check flag is passed in, run check without actually formatting the files
if [ "$1" == "--check" ]; then
    # print that wer'e fixing the files
    echo "checking format on Python files..."
    ruff format --check $(git ls-files '*.py')
# else we just run check
else
    echo "Formatting Python files..."
    ruff format $(git ls-files '*.py')
fi
