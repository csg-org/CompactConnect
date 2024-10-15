#!/bin/bash

# Find all Python files in the backend directory and check them using Ruff
# if the user has passed in the --fix flag, then we will fix the issues that can be automatically fixed
if [ "$1" == "--fix" ]; then
    # print that wer'e fixing the files
    echo "Fixing Python files..."
    ruff check --fix $(git ls-files '*.py')
# else we just run check
else
    echo "Checking Python files..."
    ruff check $(git ls-files '*.py')
fi
