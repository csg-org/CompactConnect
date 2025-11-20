#!/usr/bin/env python3
"""
Script to create a provider index in AWS OpenSearch with proper field mappings.

This script creates an index based on the ProviderGeneralResponseSchema structure.
"""

import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth


def get_opensearch_client(domain_endpoint: str, region: str = 'us-east-1'):
    """
    Create an OpenSearch client with AWS authentication.
    
    Args:
        domain_endpoint: The OpenSearch domain endpoint (without https://)
        region: AWS region where the domain is located
    
    Returns:
        OpenSearch client instance
    """
    # Get AWS credentials
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        'es',
        session_token=credentials.token
    )
    
    # Create OpenSearch client
    client = OpenSearch(
        hosts=[{'host': domain_endpoint, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )
    
    return client


def get_provider_index_mapping():
    """
    Define the index mapping for provider documents based on ProviderGeneralResponseSchema.

    Returns:
        dict: The index mapping configuration
    """
    # Nested schema for AttestationVersion
    attestation_version_properties = {
        "attestationId": {"type": "keyword"},
        "version": {"type": "keyword"}
    }

    # Nested schema for AdverseAction (simplified - can be expanded)
    adverse_action_properties = {
        "type": {"type": "keyword"},
        "adverseActionId": {"type": "keyword"},
        "compact": {"type": "keyword"},
        "jurisdiction": {"type": "keyword"},
        "licenseType": {"type": "keyword"},
        "status": {"type": "keyword"},
        "dateOfAction": {"type": "date"},
        "dateOfUpdate": {"type": "date"}
    }

    # Nested schema for Investigation (simplified - can be expanded)
    investigation_properties = {
        "type": {"type": "keyword"},
        "investigationId": {"type": "keyword"},
        "compact": {"type": "keyword"},
        "jurisdiction": {"type": "keyword"},
        "licenseType": {"type": "keyword"},
        "status": {"type": "keyword"},
        "dateOfUpdate": {"type": "date"}
    }
    
    # Nested schema for LicenseGeneralResponseSchema
    license_properties = {
        "providerId": {"type": "keyword"},
        "type": {"type": "keyword"},
        "dateOfUpdate": {"type": "date"},
        "compact": {"type": "keyword"},
        "jurisdiction": {"type": "keyword"},
        "licenseType": {"type": "keyword"},
        "licenseStatusName": {"type": "keyword"},
        "licenseStatus": {"type": "keyword"},
        "jurisdictionUploadedLicenseStatus": {"type": "keyword"},
        "compactEligibility": {"type": "keyword"},
        "jurisdictionUploadedCompactEligibility": {"type": "keyword"},
        "npi": {"type": "keyword"},
        "licenseNumber": {"type": "keyword"},
        "givenName": {
            "type": "text",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "middleName": {
            "type": "text",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "familyName": {
            "type": "text",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "suffix": {"type": "keyword"},
        "dateOfIssuance": {"type": "date"},
        "dateOfRenewal": {"type": "date"},
        "dateOfExpiration": {"type": "date"},
        "homeAddressStreet1": {"type": "text"},
        "homeAddressStreet2": {"type": "text"},
        "homeAddressCity": {
            "type": "text",
            "fields": {
                "keyword": {"type": "keyword", "ignore_above": 256}
            }
        },
        "homeAddressState": {"type": "keyword"},
        "homeAddressPostalCode": {"type": "keyword"},
        "emailAddress": {"type": "keyword"},
        "phoneNumber": {"type": "keyword"},
        "adverseActions": {
            "type": "nested",
            "properties": adverse_action_properties
        },
        "investigations": {
            "type": "nested",
            "properties": investigation_properties
        },
        "investigationStatus": {"type": "keyword"}
    }
    
    # Nested schema for PrivilegeGeneralResponseSchema
    privilege_properties = {
        "type": {"type": "keyword"},
        "providerId": {"type": "keyword"},
        "compact": {"type": "keyword"},
        "jurisdiction": {"type": "keyword"},
        "licenseJurisdiction": {"type": "keyword"},
        "licenseType": {"type": "keyword"},
        "dateOfIssuance": {"type": "date"},
        "dateOfRenewal": {"type": "date"},
        "dateOfExpiration": {"type": "date"},
        "dateOfUpdate": {"type": "date"},
        "adverseActions": {
            "type": "nested",
            "properties": adverse_action_properties
        },
        "investigations": {
            "type": "nested",
            "properties": investigation_properties
        },
        "administratorSetStatus": {"type": "keyword"},
        "compactTransactionId": {"type": "keyword"},
        "attestations": {
            "type": "nested",
            "properties": attestation_version_properties
        },
        "privilegeId": {"type": "keyword"},
        "status": {"type": "keyword"},
        "activeSince": {"type": "date"},
        "investigationStatus": {"type": "keyword"}
    }
    
    # Nested schema for MilitaryAffiliationGeneralResponseSchema
    military_affiliation_properties = {
        "type": {"type": "keyword"},
        "dateOfUpdate": {"type": "date"},
        "providerId": {"type": "keyword"},
        "compact": {"type": "keyword"},
        "fileNames": {"type": "keyword"},
        "affiliationType": {"type": "keyword"},
        "dateOfUpload": {"type": "date"},
        "status": {"type": "keyword"}
    }
    
    # Main provider index mapping
    mapping = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "1s"
            },
            "analysis": {
                "analyzer": {
                    "name_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                # Top-level provider fields
                "providerId": {"type": "keyword"},
                "type": {"type": "keyword"},
                "dateOfUpdate": {"type": "date"},
                "compact": {"type": "keyword"},
                "licenseJurisdiction": {"type": "keyword"},
                "currentHomeJurisdiction": {"type": "keyword"},
                "licenseStatus": {"type": "keyword"},
                "compactEligibility": {"type": "keyword"},
                "npi": {"type": "keyword"},
                "givenName": {
                    "type": "text",
                    "analyzer": "name_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword", "ignore_above": 256}
                    }
                },
                "middleName": {
                    "type": "text",
                    "analyzer": "name_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword", "ignore_above": 256}
                    }
                },
                "familyName": {
                    "type": "text",
                    "analyzer": "name_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword", "ignore_above": 256}
                    }
                },
                "suffix": {"type": "keyword"},
                "dateOfExpiration": {"type": "date"},
                "compactConnectRegisteredEmailAddress": {"type": "keyword"},
                "jurisdictionUploadedLicenseStatus": {"type": "keyword"},
                "jurisdictionUploadedCompactEligibility": {"type": "keyword"},
                "privilegeJurisdictions": {"type": "keyword"},  # Array of keywords
                "providerFamGivMid": {
                    "type": "text",
                    "analyzer": "name_analyzer"
                },
                "providerDateOfUpdate": {"type": "date"},
                "birthMonthDay": {"type": "keyword"},
                
                # Nested arrays
                "licenses": {
                    "type": "nested",
                    "properties": license_properties
                },
                "privileges": {
                    "type": "nested",
                    "properties": privilege_properties
                },
                "militaryAffiliations": {
                    "type": "nested",
                    "properties": military_affiliation_properties
                }
            }
        }
    }
    
    return mapping


def create_provider_index(
    client: OpenSearch,
    index_name: str = 'providers',
    delete_if_exists: bool = False
):
    """
    Create the provider index in OpenSearch.
    
    Args:
        client: OpenSearch client instance
        index_name: Name of the index to create
        delete_if_exists: Whether to delete the index if it already exists
    """
    # Check if index exists
    if client.indices.exists(index=index_name):
        if delete_if_exists:
            print(f"Index '{index_name}' already exists. Deleting...")
            client.indices.delete(index=index_name)
            print(f"Index '{index_name}' deleted successfully.")
        else:
            print(f"Index '{index_name}' already exists. Use delete_if_exists=True to recreate it.")
            return
    
    # Get the mapping
    mapping = get_provider_index_mapping()
    
    # Create the index
    print(f"Creating index '{index_name}'...")
    response = client.indices.create(
        index=index_name,
        body=mapping
    )
    
    print(f"Index '{index_name}' created successfully!")
    print(json.dumps(response, indent=2))
    
    # Verify the mapping
    print(f"\nVerifying mapping for index '{index_name}'...")
    mapping_response = client.indices.get_mapping(index=index_name)
    print(json.dumps(mapping_response, indent=2))


def main():
    """
    Main function to create the provider index.
    
    Update the domain_endpoint and region variables with your OpenSearch domain details.
    """
    # TODO: Update these values for your OpenSearch domain
    # Example: domain_endpoint = 'search-my-domain-abc123.us-east-1.es.amazonaws.com'
    domain_endpoint = input("Enter your OpenSearch domain endpoint (without https://): ").strip() or 'search-provider-search-poc-zgbptybh7se7mboibqkshe7bg4.aos.us-east-1.on.aws'
    region = input("Enter your AWS region (default: us-east-1): ").strip() or 'us-east-1'
    index_name = input("Enter index name (default: providers): ").strip() or 'providers'
    delete_if_exists = input("Delete index if it exists? (y/N): ").strip().lower() == 'y'
    
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
        
        # Create the index
        create_provider_index(client, index_name, delete_if_exists)
        
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == '__main__':
    main()
