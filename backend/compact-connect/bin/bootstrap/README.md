# Sandbox Bootstrap Script

This script bootstraps a sandbox environment with staff users and configuration for testing purposes.

## Overview

The script creates:

- Board editor users for each configured jurisdiction
- A compact editor user
- Authorize.net payment processor credentials
- Compact configuration with fees and settings
- Jurisdiction configurations with privilege fees

## Configuration

All configuration is stored in `sandbox_bootstrap_config.json`. Copy this file and modify it for your environment:

```json
{
  "base_email": "your-email@example.org",
  "authorize_net": {
    "api_login_id": "your_sandbox_api_login_id",
    "transaction_key": "your_sandbox_transaction_key"
  },
  "compact": {
    "abbreviation": "aslp",
    "additional_states": ["ky", "ne", "al", "mn", "oh"],
    "commission_fee": {
      "amount": 15.0,
      "type": "FLAT_RATE"
    },
    "transaction_fee": {
      "amount": 10.0,
      "type": "FLAT_FEE_PER_PRIVILEGE",
      "active": true
    },
    "privilege_fees": {
      "default_amount": 75.0,
      "military_rate": 50.0
    }
  },
  "test_data": {
    "provider": {
      "given_name": "Joe",
      "family_name": "Dokes",
      "ssn": "999-99-9999"
    },
    "license": {
      "npi": "1111111111",
      "license_number": "A0608337260",
      "home_address_postal_code": "68001",
      "home_address_street1": "123 Fake Street",
      "date_of_birth": "1991-12-10",
      "date_of_issuance": "2024-12-10",
      "license_type": "speech-language pathologist",
      "date_of_expiration": "2050-12-10",
      "home_address_state": "OH",
      "date_of_renewal": "2051-12-10",
      "home_address_city": "New Timothy",
      "compact_eligibility": "eligible",
      "license_status": "inactive"
    }
  },
  "jurisdiction": {
    "jurisprudence_requirements": {
      "required": true,
      "link_to_documentation": "https://example.com/jurisprudence-docs"
    }
  }
}
```

### Configuration Options

#### Base Email

- `base_email`: The email address used as the base for creating test users
  - Board editors: `{username}+board-ed-{compact}-{jurisdiction}@{domain}`
  - Compact editor: `{username}+compact-ed-{compact}@{domain}`

#### Authorize.net Credentials

- `authorize_net.api_login_id`: Your authorize.net sandbox API login ID
- `authorize_net.transaction_key`: Your authorize.net sandbox transaction key

#### Compact Configuration

- `compact.abbreviation`: The compact abbreviation (e.g., "aslp", "octp")
- `compact.additional_states`: List of jurisdiction abbreviations to configure
- `compact.commission_fee`: Commission fee configuration
- `compact.transaction_fee`: Transaction fee configuration
- `compact.privilege_fees`: Default privilege fee amounts

#### Test Data

- `test_data.provider`: Test provider information
- `test_data.license`: Test license information for uploads

#### Jurisdiction Configuration

- `jurisdiction.jurisprudence_requirements`: Jurisprudence requirements for all jurisdictions

## Usage

1. **Set up your configuration file:**

   ```bash
   cp sandbox_bootstrap_config.json my_sandbox_config.json
   # Edit my_sandbox_config.json with your settings
   ```

2. **Run the bootstrap script:**

   ```bash
   # Using default config file
   python sandbox_bootstrap_staff_users.py

   # Using custom config file
   python sandbox_bootstrap_staff_users.py --config-file my_sandbox_config.json
   ```

## Prerequisites

- AWS CLI configured with appropriate credentials
- Access to Cognito and DynamoDB resources
- Valid authorize.net sandbox credentials
- The script must be run from the `backend/compact-connect` directory

## Output

The script will:

1. Create staff users for each jurisdiction and the compact
2. Upload authorize.net credentials
3. Configure the compact with fees and settings
4. Configure each jurisdiction with privilege fees
5. Display a summary of created users and configurations

## Files

- `sandbox_bootstrap_staff_users.py`: Main script
- `sandbox_bootstrap_config.py`: Configuration helper module
- `sandbox_bootstrap_api.py`: API helper module
- `sandbox_bootstrap_config.json`: Configuration file (template)
- `sandbox_fetch_aws_resources.py`: AWS resource fetching (existing)

## Security Notes

- The configuration file contains sensitive credentials - keep it secure
- Use sandbox/development authorize.net credentials only
- The script uses a hardcoded password for test users (appropriate for sandbox environments)
