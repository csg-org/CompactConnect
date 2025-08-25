#!/bin/bash

# Update API documentation workflow
# Downloads, trims, and updates Postman collections for both StateApi and LicenseApi

set -e  # Exit immediately if any command fails

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if required tools are installed
check_requirements() {
    print_status "Checking requirements..."

    local missing_tools=()

    if ! command_exists python3; then
        missing_tools+=("python3")
    fi

    if ! command_exists openapi2postmanv2; then
        missing_tools+=("openapi2postmanv2")
    fi

    if ! command_exists aws; then
        missing_tools+=("aws")
    fi

    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install missing tools and try again."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials not configured or invalid"
        print_error "Please run 'aws configure' or set up your credentials"
        exit 1
    fi

    print_success "All requirements satisfied"
}

# Function to download API specifications
download_specs() {
    print_status "Downloading API specifications..."

    if ! python3 bin/download_oas30.py; then
        print_error "Failed to download API specifications"
        exit 1
    fi

    print_success "API specifications downloaded successfully"
}

# Function to trim API specifications
trim_specs() {
    print_status "Trimming API specifications..."

    # Trim regular API spec
    print_status "Trimming StateApi specification..."
    if ! python3 bin/trim_oas30.py; then
        print_error "Failed to trim StateApi specification"
        exit 1
    fi
    print_success "StateApi specification trimmed"

    # Trim internal API spec
    print_status "Trimming LicenseApi specification..."
    if ! python3 bin/trim_oas30.py --internal; then
        print_error "Failed to trim LicenseApi specification"
        exit 1
    fi
    print_success "LicenseApi specification trimmed"
}

# Function to update Postman collections
update_postman() {
    print_status "Updating Postman collections..."

    # Update regular Postman collection
    print_status "Updating StateApi Postman collection..."
    if ! python3 bin/update_postman_collection.py; then
        print_error "Failed to update StateApi Postman collection"
        exit 1
    fi
    print_success "StateApi Postman collection updated"

    # Update internal Postman collection
    print_status "Updating LicenseApi Postman collection..."
    if ! python3 bin/update_postman_collection.py --internal; then
        print_error "Failed to update LicenseApi Postman collection"
        exit 1
    fi
    print_success "LicenseApi Postman collection updated"
}

# Function to verify files exist
verify_files() {
    print_status "Verifying generated files..."

    local files=(
        "docs/api-specification/latest-oas30.json"
        "docs/internal/api-specification/latest-oas30.json"
        "docs/postman/postman-collection.json"
        "docs/internal/postman/postman-collection.json"
    )

    for file in "${files[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "Required file not found: $file"
            exit 1
        fi
    done

    print_success "All required files verified"
}

# Main execution
main() {
    echo "=========================================="
    echo "  API Documentation Update Workflow"
    echo "=========================================="
    echo

    print_status "Starting API documentation update workflow..."
    echo

    # Execute workflow steps
    check_requirements
    echo

    download_specs
    echo

    trim_specs
    echo

    update_postman
    echo

    verify_files
    echo

    print_success "API documentation update workflow completed successfully!"
    echo
    print_status "Updated files:"
    echo "  - docs/api-specification/latest-oas30.json"
    echo "  - docs/internal/api-specification/latest-oas30.json"
    echo "  - docs/postman/postman-collection.json"
    echo "  - docs/internal/postman/postman-collection.json"
}

# Handle script interruption
trap 'print_error "Script interrupted by user"; exit 1' INT TERM

# Run main function
main "$@"
