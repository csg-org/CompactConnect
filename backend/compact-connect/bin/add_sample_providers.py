#!/usr/bin/env python3
"""
Script to add sample provider documents to the OpenSearch index.

This script demonstrates how to add provider data to the OpenSearch index
created by create_provider_index.py.
"""

from datetime import datetime, timedelta
from create_provider_index import get_opensearch_client


# ============================================================================
# EXAMPLE QUERIES - Test queries for common search scenarios
# ============================================================================

# Query 1: Which providers are registered in a particular home state?
QUERY_PROVIDERS_BY_HOME_STATE = {
    "query": {
        "term": {
            "currentHomeJurisdiction": "ky"  # Change to desired state code
        }
    }
}

# Query 2: Which providers have uploaded military documentation that needs review?
QUERY_MILITARY_DOCS_PENDING_REVIEW = {
    "query": {
        "nested": {
            "path": "militaryAffiliations",
            "query": {
                "bool": {
                    "should": [
                        {"term": {"militaryAffiliations.status": "pending"}},
                        {"term": {"militaryAffiliations.status": "under-review"}}
                    ],
                    "minimum_should_match": 1
                }
            }
        }
    }
}

# Query 3: Which providers currently have open investigations against them?
# This searches for investigations in both licenses and privileges
QUERY_PROVIDERS_WITH_OPEN_INVESTIGATIONS = {
    "query": {
        "bool": {
            "should": [
                # Check for investigation status at provider level (if present)
                {"exists": {"field": "investigationStatus"}},
                # Check for investigations in nested licenses
                {
                    "nested": {
                        "path": "licenses",
                        "query": {
                            "bool": {
                                "must": [
                                    {"exists": {"field": "licenses.investigationStatus"}},
                                    {"term": {"licenses.investigationStatus": "underInvestigation"}}
                                ]
                            }
                        }
                    }
                },
                # Check for investigations in nested privileges
                {
                    "nested": {
                        "path": "privileges",
                        "query": {
                            "bool": {
                                "must": [
                                    {"exists": {"field": "privileges.investigationStatus"}},
                                    {"term": {"privileges.investigationStatus": "underInvestigation"}}
                                ]
                            }
                        }
                    }
                }
            ],
            "minimum_should_match": 1
        }
    }
}

# Query 4: Which providers have an encumbrance against them?
# Searches for encumbrance status in licenses or privileges
QUERY_PROVIDERS_WITH_ENCUMBRANCE = {
    "query": {
        "bool": {
            "should": [
                # Check for encumbrance in nested licenses
                {
                    "nested": {
                        "path": "licenses",
                        "query": {
                            "term": {"licenses.encumberedStatus": "encumbered"}
                        }
                    }
                },
                # Check for encumbrance in nested privileges
                {
                    "nested": {
                        "path": "privileges",
                        "query": {
                            "term": {"privileges.encumberedStatus": "encumbered"}
                        }
                    }
                }
            ],
            "minimum_should_match": 1
        }
    }
}

# Query 5: Which provider has a specified NPI?
QUERY_PROVIDER_BY_NPI = {
    "query": {
        "term": {
            "npi": "1234567890"  # Change to desired NPI
        }
    }
}

# Query 6: Which providers have a specified first and/or last name? (fuzzy search, sorted by best match)
QUERY_PROVIDER_BY_NAME_FUZZY = {
    "query": {
        "bool": {
            "should": [
                {
                    "match": {
                        "givenName": {
                            "query": "Sara",  # Note: intentional misspelling to test fuzzy
                            "fuzziness": "AUTO",
                            "boost": 2.0  # Give more weight to first name matches
                        }
                    }
                },
                {
                    "match": {
                        "familyName": {
                            "query": "Jonson",  # Note: intentional misspelling to test fuzzy
                            "fuzziness": "AUTO",
                            "boost": 3.0  # Give even more weight to last name matches
                        }
                    }
                },
                {
                    "match": {
                        "providerFamGivMid": {
                            "query": "Sara Jonson",
                            "fuzziness": "AUTO"
                        }
                    }
                }
            ],
            "minimum_should_match": 1
        }
    },
    "sort": [
        {"_score": {"order": "desc"}}  # Sort by relevance score
    ]
}

# Query 7: How many privileges were purchased within a specific time period? What states were the privileges in?
# This uses aggregations to count privileges and group by jurisdiction
QUERY_PRIVILEGES_BY_TIME_PERIOD_WITH_AGGREGATIONS = {
    "size": 0,  # We only want aggregations, not individual documents
    "query": {
        "nested": {
            "path": "privileges",
            "query": {
                "range": {
                    "privileges.dateOfIssuance": {
                        "gte": "2024-01-01T00:00:00Z",  # Change to desired start date
                        "lte": "2025-12-31T23:59:59Z"   # Change to desired end date
                    }
                }
            }
        }
    },
    "aggs": {
        "privileges_in_period": {
            "nested": {
                "path": "privileges"
            },
            "aggs": {
                "filtered_privileges": {
                    "filter": {
                        "range": {
                            "privileges.dateOfIssuance": {
                                "gte": "2024-01-01T00:00:00Z",
                                "lte": "2025-12-31T23:59:59Z"
                            }
                        }
                    },
                    "aggs": {
                        "total_count": {
                            "value_count": {
                                "field": "privileges.privilegeId"
                            }
                        },
                        "by_jurisdiction": {
                            "terms": {
                                "field": "privileges.jurisdiction",
                                "size": 100
                            }
                        }
                    }
                }
            }
        }
    }
}


def get_sample_providers():
    """
    Generate sample provider documents for testing.
    
    Returns:
        list: List of sample provider documents
    """
    now = datetime.now()
    future_date = (now + timedelta(days=365)).date().isoformat()
    
    providers = [
        {
            "providerId": "123e4567-e89b-12d3-a456-426614174000",
            "type": "provider",
            "dateOfUpdate": now.isoformat(),
            "compact": "aslp",
            "licenseJurisdiction": "oh",
            "licenseStatus": "active",
            "compactEligibility": "eligible",
            "givenName": "Sarah",
            "middleName": "Marie",
            "familyName": "Johnson",
            "suffix": "PhD",
            "dateOfExpiration": future_date,
            "compactConnectRegisteredEmailAddress": "sarah.johnson@example.com",
            "jurisdictionUploadedLicenseStatus": "active",
            "jurisdictionUploadedCompactEligibility": "eligible",
            "privilegeJurisdictions": ["ky", "ne", "co"],
            "providerFamGivMid": "Johnson Sarah Marie",
            "providerDateOfUpdate": now.isoformat(),
            "birthMonthDay": "03-15",
            "npi": "1234567890",
            "licenses": [
                {
                    "providerId": "123e4567-e89b-12d3-a456-426614174000",
                    "type": "license",
                    "dateOfUpdate": now.isoformat(),
                    "compact": "aslp",
                    "jurisdiction": "oh",
                    "licenseType": "audiologist",
                    "licenseStatus": "active",
                    "jurisdictionUploadedLicenseStatus": "active",
                    "compactEligibility": "eligible",
                    "jurisdictionUploadedCompactEligibility": "eligible",
                    "npi": "1234567890",
                    "licenseNumber": "OH-12345",
                    "givenName": "Sarah",
                    "middleName": "Marie",
                    "familyName": "Johnson",
                    "suffix": "PhD",
                    "dateOfIssuance": (now - timedelta(days=730)).date().isoformat(),
                    "dateOfRenewal": (now - timedelta(days=30)).date().isoformat(),
                    "dateOfExpiration": future_date,
                    "homeAddressStreet1": "123 Main St",
                    "homeAddressCity": "Columbus",
                    "homeAddressState": "OH",
                    "homeAddressPostalCode": "43215",
                    "emailAddress": "sarah.johnson@example.com",
                    "phoneNumber": "+15551234567",
                    "adverseActions": [],
                    "investigations": []
                }
            ],
            "privileges": [
                {
                    "type": "privilege",
                    "providerId": "123e4567-e89b-12d3-a456-426614174000",
                    "compact": "aslp",
                    "jurisdiction": "ky",
                    "licenseJurisdiction": "oh",
                    "licenseType": "audiologist",
                    "dateOfIssuance": (now - timedelta(days=180)).isoformat(),
                    "dateOfRenewal": (now - timedelta(days=180)).isoformat(),
                    "dateOfExpiration": future_date,
                    "dateOfUpdate": now.isoformat(),
                    "adverseActions": [],
                    "investigations": [],
                    "administratorSetStatus": "active",
                    "compactTransactionId": "TX123456",
                    "attestations": [
                        {
                            "attestationId": "attest-001",
                            "version": "1.0"
                        }
                    ],
                    "privilegeId": "PRIV-KY-001",
                    "status": "active",
                    "activeSince": (now - timedelta(days=180)).isoformat()
                },
                {
                    "type": "privilege",
                    "providerId": "123e4567-e89b-12d3-a456-426614174000",
                    "compact": "aslp",
                    "jurisdiction": "ne",
                    "licenseJurisdiction": "oh",
                    "licenseType": "audiologist",
                    "dateOfIssuance": (now - timedelta(days=90)).isoformat(),
                    "dateOfRenewal": (now - timedelta(days=90)).isoformat(),
                    "dateOfExpiration": future_date,
                    "dateOfUpdate": now.isoformat(),
                    "adverseActions": [],
                    "investigations": [],
                    "administratorSetStatus": "active",
                    "compactTransactionId": "TX123457",
                    "attestations": [
                        {
                            "attestationId": "attest-001",
                            "version": "1.0"
                        }
                    ],
                    "privilegeId": "PRIV-NE-001",
                    "status": "active",
                    "activeSince": (now - timedelta(days=90)).isoformat()
                }
            ],
            "militaryAffiliations": []
        },
        {
            "providerId": "234e5678-e89b-12d3-a456-426614174001",
            "type": "provider",
            "dateOfUpdate": now.isoformat(),
            "compact": "aslp",
            "licenseJurisdiction": "ky",
            "currentHomeJurisdiction": "ky",
            "licenseStatus": "active",
            "compactEligibility": "eligible",
            "givenName": "Michael",
            "familyName": "Chen",
            "dateOfExpiration": future_date,
            "compactConnectRegisteredEmailAddress": "michael.chen@example.com",
            "jurisdictionUploadedLicenseStatus": "active",
            "jurisdictionUploadedCompactEligibility": "eligible",
            "privilegeJurisdictions": ["oh", "co"],
            "providerFamGivMid": "Chen Michael",
            "providerDateOfUpdate": now.isoformat(),
            "birthMonthDay": "07-22",
            "npi": "2345678901",
            "licenses": [
                {
                    "providerId": "234e5678-e89b-12d3-a456-426614174001",
                    "type": "license",
                    "dateOfUpdate": now.isoformat(),
                    "compact": "aslp",
                    "jurisdiction": "ky",
                    "licenseType": "speech-language-pathologist",
                    "licenseStatus": "active",
                    "jurisdictionUploadedLicenseStatus": "active",
                    "compactEligibility": "eligible",
                    "jurisdictionUploadedCompactEligibility": "eligible",
                    "npi": "2345678901",
                    "licenseNumber": "KY-67890",
                    "givenName": "Michael",
                    "familyName": "Chen",
                    "dateOfIssuance": (now - timedelta(days=1095)).date().isoformat(),
                    "dateOfRenewal": (now - timedelta(days=60)).date().isoformat(),
                    "dateOfExpiration": future_date,
                    "homeAddressStreet1": "456 Oak Avenue",
                    "homeAddressStreet2": "Apt 2B",
                    "homeAddressCity": "Louisville",
                    "homeAddressState": "KY",
                    "homeAddressPostalCode": "40202",
                    "emailAddress": "michael.chen@example.com",
                    "phoneNumber": "+15559876543",
                    "adverseActions": [],
                    "investigations": []
                }
            ],
            "privileges": [
                {
                    "type": "privilege",
                    "providerId": "234e5678-e89b-12d3-a456-426614174001",
                    "compact": "aslp",
                    "jurisdiction": "oh",
                    "licenseJurisdiction": "ky",
                    "licenseType": "speech-language-pathologist",
                    "dateOfIssuance": (now - timedelta(days=120)).isoformat(),
                    "dateOfRenewal": (now - timedelta(days=120)).isoformat(),
                    "dateOfExpiration": future_date,
                    "dateOfUpdate": now.isoformat(),
                    "adverseActions": [],
                    "investigations": [],
                    "administratorSetStatus": "active",
                    "compactTransactionId": "TX234567",
                    "attestations": [
                        {
                            "attestationId": "attest-002",
                            "version": "1.0"
                        }
                    ],
                    "privilegeId": "PRIV-OH-002",
                    "status": "active",
                    "activeSince": (now - timedelta(days=120)).isoformat()
                }
            ],
            "militaryAffiliations": [
                {
                    "type": "militaryAffiliation",
                    "dateOfUpdate": now.isoformat(),
                    "providerId": "234e5678-e89b-12d3-a456-426614174001",
                    "compact": "aslp",
                    "fileNames": ["military_docs.pdf"],
                    "affiliationType": "active-duty",
                    "dateOfUpload": (now - timedelta(days=200)).isoformat(),
                    "status": "pending"  # Changed to pending for testing
                }
            ]
        },
        {
            "providerId": "345e6789-e89b-12d3-a456-426614174002",
            "type": "provider",
            "dateOfUpdate": now.isoformat(),
            "compact": "aslp",
            "licenseJurisdiction": "co",
            "licenseStatus": "active",
            "compactEligibility": "eligible",
            "givenName": "Emily",
            "middleName": "Rose",
            "familyName": "Martinez",
            "suffix": "MS",
            "dateOfExpiration": future_date,
            "jurisdictionUploadedLicenseStatus": "active",
            "jurisdictionUploadedCompactEligibility": "eligible",
            "privilegeJurisdictions": [],
            "providerFamGivMid": "Martinez Emily Rose",
            "providerDateOfUpdate": now.isoformat(),
            "birthMonthDay": "11-05",
            "licenses": [
                {
                    "providerId": "345e6789-e89b-12d3-a456-426614174002",
                    "type": "license",
                    "dateOfUpdate": now.isoformat(),
                    "compact": "aslp",
                    "jurisdiction": "co",
                    "licenseType": "audiologist",
                    "licenseStatus": "active",
                    "jurisdictionUploadedLicenseStatus": "active",
                    "compactEligibility": "eligible",
                    "jurisdictionUploadedCompactEligibility": "eligible",
                    "licenseNumber": "CO-11223",
                    "givenName": "Emily",
                    "middleName": "Rose",
                    "familyName": "Martinez",
                    "suffix": "MS",
                    "dateOfIssuance": (now - timedelta(days=365)).date().isoformat(),
                    "dateOfRenewal": (now - timedelta(days=10)).date().isoformat(),
                    "dateOfExpiration": future_date,
                    "homeAddressStreet1": "789 Mountain Road",
                    "homeAddressCity": "Denver",
                    "homeAddressState": "CO",
                    "homeAddressPostalCode": "80201",
                    "emailAddress": "emily.martinez@example.com",
                    "phoneNumber": "+15551112222",
                    "adverseActions": [],
                    "investigations": [],
                    "investigationStatus": "underInvestigation"  # Add investigation status for testing
                }
            ],
            "privileges": [],
            "militaryAffiliations": []
        },
        {
            "providerId": "456e7890-e89b-12d3-a456-426614174003",
            "type": "provider",
            "dateOfUpdate": now.isoformat(),
            "compact": "aslp",
            "licenseJurisdiction": "ne",
            "licenseStatus": "active",
            "compactEligibility": "eligible",
            "givenName": "Robert",
            "middleName": "James",
            "familyName": "Williams",
            "dateOfExpiration": future_date,
            "compactConnectRegisteredEmailAddress": "robert.williams@example.com",
            "jurisdictionUploadedLicenseStatus": "active",
            "jurisdictionUploadedCompactEligibility": "eligible",
            "privilegeJurisdictions": ["ky"],
            "providerFamGivMid": "Williams Robert James",
            "providerDateOfUpdate": now.isoformat(),
            "birthMonthDay": "09-12",
            "npi": "3456789012",
            "licenses": [
                {
                    "providerId": "456e7890-e89b-12d3-a456-426614174003",
                    "type": "license",
                    "dateOfUpdate": now.isoformat(),
                    "compact": "aslp",
                    "jurisdiction": "ne",
                    "licenseType": "speech-language-pathologist",
                    "licenseStatus": "active",
                    "jurisdictionUploadedLicenseStatus": "active",
                    "compactEligibility": "eligible",
                    "jurisdictionUploadedCompactEligibility": "eligible",
                    "npi": "3456789012",
                    "licenseNumber": "NE-99887",
                    "givenName": "Robert",
                    "middleName": "James",
                    "familyName": "Williams",
                    "dateOfIssuance": (now - timedelta(days=540)).date().isoformat(),
                    "dateOfRenewal": (now - timedelta(days=20)).date().isoformat(),
                    "dateOfExpiration": future_date,
                    "homeAddressStreet1": "321 Prairie Lane",
                    "homeAddressCity": "Omaha",
                    "homeAddressState": "NE",
                    "homeAddressPostalCode": "68101",
                    "emailAddress": "robert.williams@example.com",
                    "phoneNumber": "+15553334444",
                    "adverseActions": [],
                    "investigations": []
                }
            ],
            "privileges": [
                {
                    "type": "privilege",
                    "providerId": "456e7890-e89b-12d3-a456-426614174003",
                    "compact": "aslp",
                    "jurisdiction": "ky",
                    "licenseJurisdiction": "ne",
                    "licenseType": "speech-language-pathologist",
                    "dateOfIssuance": (now - timedelta(days=45)).isoformat(),
                    "dateOfRenewal": (now - timedelta(days=45)).isoformat(),
                    "dateOfExpiration": future_date,
                    "dateOfUpdate": now.isoformat(),
                    "adverseActions": [],
                    "investigations": [],
                    "administratorSetStatus": "active",
                    "compactTransactionId": "TX345678",
                    "attestations": [
                        {
                            "attestationId": "attest-003",
                            "version": "1.0"
                        }
                    ],
                    "privilegeId": "PRIV-KY-003",
                    "status": "active",
                    "activeSince": (now - timedelta(days=45)).isoformat(),
                    "encumberedStatus": "encumbered"  # Add encumbrance for testing
                }
            ],
            "militaryAffiliations": [
                {
                    "type": "militaryAffiliation",
                    "dateOfUpdate": now.isoformat(),
                    "providerId": "456e7890-e89b-12d3-a456-426614174003",
                    "compact": "aslp",
                    "fileNames": ["dd214.pdf", "orders.pdf"],
                    "affiliationType": "veteran",
                    "dateOfUpload": (now - timedelta(days=5)).isoformat(),
                    "status": "under-review"  # Add under-review status for testing
                }
            ]
        }
    ]
    
    return providers


def add_documents_to_index(client, index_name: str = 'providers'):
    """
    Add sample provider documents to the OpenSearch index.
    
    Args:
        client: OpenSearch client instance
        index_name: Name of the index to add documents to
    """
    # Check if index exists
    if not client.indices.exists(index=index_name):
        print(f"Error: Index '{index_name}' does not exist.")
        print("Please run create_provider_index.py first to create the index.")
        return
    
    # Get sample providers
    providers = get_sample_providers()
    
    print(f"Adding {len(providers)} sample provider documents to index '{index_name}'...")
    print()
    
    # Add each provider
    for i, provider in enumerate(providers, 1):
        provider_id = provider['providerId']
        print(f"Adding provider {i}/{len(providers)}: {provider['givenName']} {provider['familyName']} (ID: {provider_id})")
        
        response = client.index(
            index=index_name,
            body=provider,
            id=provider_id,
            refresh=True  # Make document immediately searchable
        )
        
        print(f"  Result: {response['result']}")
        print(f"  Licenses: {len(provider.get('licenses', []))}")
        print(f"  Privileges: {len(provider.get('privileges', []))}")
        print(f"  Military Affiliations: {len(provider.get('militaryAffiliations', []))}")
        print()
    
    # Verify documents were added
    print(f"Verifying documents in index '{index_name}'...")
    count_response = client.count(index=index_name)
    print(f"Total documents in index: {count_response['count']}")
    print()
    
    print("✅ Sample providers added successfully!")


def search_index(client, index_name: str = 'providers', query_body: dict = None):
    """
    Execute a search query against the provider index.
    
    Args:
        client: OpenSearch client instance
        index_name: Name of the index to search
        query_body: The query body to execute (defaults to QUERY_PROVIDER_BY_NPI)
    """
    import json
    
    if query_body is None:
        query_body = QUERY_PROVIDER_BY_NPI
    
    print("=" * 80)
    print("Executing search query:")
    print("=" * 80)
    print(json.dumps(query_body, indent=2))
    print("=" * 80)
    print()
    
    search_response = client.search(
        index=index_name,
        body=query_body
    )
    
    # Handle aggregation responses differently
    if 'aggregations' in search_response:
        print("Aggregation Results:")
        print("-" * 80)
        aggs = search_response['aggregations']
        
        # Handle the privileges aggregation specifically
        if 'privileges_in_period' in aggs:
            filtered = aggs['privileges_in_period']['filtered_privileges']
            total_count = filtered['total_count']['value']
            jurisdictions = filtered['by_jurisdiction']['buckets']
            
            print(f"Total privileges purchased in time period: {total_count}")
            print()
            print("Breakdown by jurisdiction:")
            for bucket in jurisdictions:
                print(f"  {bucket['key']}: {bucket['doc_count']} privileges")
        else:
            print(json.dumps(aggs, indent=2))
        print()
    
    # Show matching documents
    total_hits = search_response['hits']['total']['value']
    print(f"Found {total_hits} matching providers:")
    print("-" * 80)
    
    for hit in search_response['hits']['hits']:
        provider = hit['_source']
        score = hit.get('_score', 'N/A')
        print(f"Score: {score} | {provider['givenName']} {provider.get('middleName', '')} {provider['familyName']} ({provider['providerId']})")
        print(f"  Jurisdiction: {provider['licenseJurisdiction']}, Compact: {provider['compact']}")
        
        # Show relevant details based on query
        if provider.get('npi'):
            print(f"  NPI: {provider['npi']}")
        if provider.get('militaryAffiliations'):
            print(f"  Military Affiliations: {len(provider['militaryAffiliations'])}")
            for affil in provider['militaryAffiliations']:
                print(f"    - Status: {affil['status']}, Type: {affil['affiliationType']}")
        if provider.get('privileges'):
            print(f"  Privileges: {len(provider['privileges'])} in jurisdictions: {provider.get('privilegeJurisdictions', [])}")
        print()
    
    print("=" * 80)
    print()


def main():
    """
    Main function to add sample providers to the index.
    """
    # Available queries for testing
    available_queries = {
        '1': ('Providers by home state', QUERY_PROVIDERS_BY_HOME_STATE),
        '2': ('Military docs pending review', QUERY_MILITARY_DOCS_PENDING_REVIEW),
        '3': ('Providers with open investigations', QUERY_PROVIDERS_WITH_OPEN_INVESTIGATIONS),
        '4': ('Providers with encumbrance', QUERY_PROVIDERS_WITH_ENCUMBRANCE),
        '5': ('Provider by NPI', QUERY_PROVIDER_BY_NPI),
        '6': ('Provider by name (fuzzy)', QUERY_PROVIDER_BY_NAME_FUZZY),
        '7': ('Privileges by time period (with aggregations)', QUERY_PRIVILEGES_BY_TIME_PERIOD_WITH_AGGREGATIONS),
    }
    
    # Configuration
    domain_endpoint = input("Enter your OpenSearch domain endpoint (without https://): ").strip() or 'search-provider-search-poc-zgbptybh7se7mboibqkshe7bg4.aos.us-east-1.on.aws'
    region = input("Enter your AWS region (default: us-east-1): ").strip() or 'us-east-1'
    index_name = input("Enter index name (default: providers): ").strip() or 'providers'
    
    print(f"\nConnecting to OpenSearch domain: {domain_endpoint}")
    print(f"Region: {region}")
    print(f"Index name: {index_name}")
    print()
    
    try:
        # Create OpenSearch client
        client = get_opensearch_client(domain_endpoint, region)
        
        # Test connection
        info = client.info()
        print(f"Connected to OpenSearch cluster: {info['version']['number']}")
        print()
        
        # Ask what to do
        print("What would you like to do?")
        print("  A - Add sample documents to index")
        print("  S - Search the index")
        action = input("Enter choice (A/S): ").strip().upper() or 'S'
        print()
        
        if action == 'A':
            add_documents_to_index(client, index_name)
        else:
            while True:
                # Show available queries
                print("Available test queries:")
                print("-" * 80)
                for key, (description, _) in available_queries.items():
                    print(f"  {key} - {description}")
                print()

                query_choice = input("Select query to test (1-7): ").strip()

                if query_choice in available_queries:
                    description, query_body = available_queries[query_choice]
                    print(f"\nTesting: {description}")
                    print()
                    search_index(client, index_name, query_body)
                else:
                    print(f"Invalid choice: {query_choice}")
        
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == '__main__':
    main()

