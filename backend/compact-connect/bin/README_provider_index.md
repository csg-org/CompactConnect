# Provider Index Creation Script

This script creates an OpenSearch index for storing provider data with proper field mappings based on the `ProviderGeneralResponseSchema`.

## Prerequisites

1. Python 3.8 or higher
2. AWS credentials configured (via `aws configure` or environment variables)
3. Access to your AWS OpenSearch domain
4. Required Python packages

## Installation

Install the required dependencies:

```bash
pip install -r create_provider_index_requirements.txt
```

Or install individually:

```bash
pip install boto3 opensearch-py requests-aws4auth
```

## Usage

### Interactive Mode

Simply run the script and follow the prompts:

```bash
python create_provider_index.py
```

You'll be prompted for:
- OpenSearch domain endpoint (e.g., `search-my-domain-abc123.us-east-1.es.amazonaws.com`)
- AWS region (default: `us-east-1`)
- Index name (default: `providers`)
- Whether to delete the index if it already exists

### Programmatic Usage

You can also import and use the functions directly in your code:

```python
from create_provider_index import get_opensearch_client, create_provider_index

# Create client
client = get_opensearch_client('your-domain-endpoint.us-east-1.es.amazonaws.com', 'us-east-1')

# Create index
create_provider_index(client, index_name='providers', delete_if_exists=False)
```

## Index Mapping

The script creates an index with the following structure:

### Top-level Provider Fields
- `providerId` (keyword)
- `type` (keyword)
- `dateOfUpdate` (date)
- `compact` (keyword)
- `licenseJurisdiction` (keyword)
- `currentHomeJurisdiction` (keyword)
- `licenseStatus` (keyword)
- `compactEligibility` (keyword)
- `npi` (keyword)
- `givenName`, `middleName`, `familyName` (text with keyword subfield)
- `suffix` (keyword)
- `dateOfExpiration` (date)
- `compactConnectRegisteredEmailAddress` (keyword)
- `jurisdictionUploadedLicenseStatus` (keyword)
- `jurisdictionUploadedCompactEligibility` (keyword)
- `privilegeJurisdictions` (keyword array)
- `providerFamGivMid` (text)
- `providerDateOfUpdate` (date)
- `birthMonthDay` (keyword)

### Nested Arrays
- `licenses` (nested) - Array of license objects
- `privileges` (nested) - Array of privilege objects
- `militaryAffiliations` (nested) - Array of military affiliation objects

## Adding Documents

After creating the index, you can add documents like this:

```python
from opensearchpy import OpenSearch
from create_provider_index import get_opensearch_client

# Create client
client = get_opensearch_client('your-domain-endpoint.us-east-1.es.amazonaws.com')

# Add a document
provider_doc = {
    "providerId": "123e4567-e89b-12d3-a456-426614174000",
    "type": "provider",
    "dateOfUpdate": "2025-11-20T10:00:00Z",
    "compact": "aslp",
    "licenseJurisdiction": "oh",
    "licenseStatus": "active",
    "compactEligibility": "eligible",
    "givenName": "John",
    "familyName": "Doe",
    "dateOfExpiration": "2026-12-31",
    "jurisdictionUploadedLicenseStatus": "active",
    "jurisdictionUploadedCompactEligibility": "eligible",
    "birthMonthDay": "01-15",
    "licenses": [],
    "privileges": [],
    "militaryAffiliations": []
}

response = client.index(
    index='providers',
    body=provider_doc,
    id=provider_doc['providerId'],
    refresh=True
)

print(f"Document indexed: {response}")
```

## Searching Documents

Example searches:

```python
# Search by name
response = client.search(
    index='providers',
    body={
        "query": {
            "match": {
                "familyName": "Doe"
            }
        }
    }
)

# Search by jurisdiction
response = client.search(
    index='providers',
    body={
        "query": {
            "term": {
                "licenseJurisdiction": "oh"
            }
        }
    }
)

# Search nested privileges
response = client.search(
    index='providers',
    body={
        "query": {
            "nested": {
                "path": "privileges",
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"privileges.jurisdiction": "ky"}},
                            {"term": {"privileges.status": "active"}}
                        ]
                    }
                }
            }
        }
    }
)
```

## AWS OpenSearch Domain Configuration

Make sure your OpenSearch domain:
1. Has the appropriate access policy to allow your AWS credentials
2. Is accessible from your network (VPC configuration or public access)
3. Has sufficient resources for your expected data volume

## Troubleshooting

### Authentication Errors
- Verify your AWS credentials are configured: `aws sts get-caller-identity`
- Check the access policy on your OpenSearch domain

### Connection Errors
- Verify the domain endpoint is correct
- Check if the domain is in a VPC (you may need VPN or bastion host)
- Ensure security groups allow access on port 443

### Import Errors
- Make sure all required packages are installed
- Use a virtual environment to avoid conflicts

## Notes

- The index uses 1 shard and 0 replicas by default (suitable for development/testing)
- For production use, adjust the shard and replica settings in the `get_provider_index_mapping()` function
- Name fields use a custom analyzer for better search capabilities
- Nested fields (licenses, privileges, militaryAffiliations) allow for complex queries while maintaining document relationships

