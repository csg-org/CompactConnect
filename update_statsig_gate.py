#!/usr/bin/env python3
"""
Script to update a feature gate in Statsig using the Console API.
This script retrieves an existing gate and adds the "staging" environment 
to the 'environment_toggle' rule.
"""

import os
import json
import requests
from typing import Dict, Any, Optional


def get_feature_gate(api_key: str, gate_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a feature gate by name using the Statsig Console API.
    
    Args:
        api_key: Statsig Console API Key
        gate_name: Name of the feature gate to retrieve
        
    Returns:
        Gate data as a dictionary, or None if not found
    """
    
    # First, we need to list all gates to find the one we want
    api_url = "https://statsigapi.net/console/v1/gates"
    headers = {
        "STATSIG-API-KEY": api_key,
        "STATSIG-API-VERSION": "20240601",
        "Content-Type": "application/json"
    }
    
    print(f"Fetching all gates to find: {gate_name}")
    
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        
        print(f"GET Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            gates_data = response.json()
            print(f"Found {len(gates_data.get('data', []))} gates")
            
            # Find the gate by name
            for gate in gates_data.get('data', []):
                if gate.get('name') == gate_name:
                    print(f"✅ Found gate: {gate_name}")
                    print(f"Gate ID: {gate.get('id')}")
                    return gate
            
            print(f"❌ Gate '{gate_name}' not found")
            return None
        else:
            print(f"❌ Failed to fetch gates. Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None


def update_feature_gate(api_key: str, gate_id: str, gate_data: Dict[str, Any]) -> bool:
    """
    Update a feature gate using the PATCH endpoint.
    
    Args:
        api_key: Statsig Console API Key
        gate_id: ID of the feature gate to update
        gate_data: Updated gate configuration
        
    Returns:
        True if successful, False otherwise
    """
    
    api_url = f"https://statsigapi.net/console/v1/gates/{gate_id}"
    headers = {
        "STATSIG-API-KEY": api_key,
        "STATSIG-API-VERSION": "20240601",
        "Content-Type": "application/json"
    }
    
    print(f"Updating gate ID: {gate_id}")
    print(f"PATCH URL: {api_url}")
    print(f"Updated payload: {json.dumps(gate_data, indent=2)}")
    
    try:
        response = requests.patch(
            api_url,
            headers=headers,
            data=json.dumps(gate_data),
            timeout=30
        )
        
        print(f"PATCH Response Status Code: {response.status_code}")
        
        if response.status_code in [200, 204]:
            print("✅ Feature gate updated successfully!")
            return True
        else:
            print(f"❌ Failed to update feature gate")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def add_staging_environment(gate_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add the 'staging' environment to the 'environment_toggle' rule.
    
    Args:
        gate_data: Original gate configuration
        
    Returns:
        Updated gate configuration
    """
    
    updated_gate = gate_data.copy()
    
    # Find the 'environment_toggle' rule and add staging
    for rule in updated_gate.get('rules', []):
        if rule.get('name') == 'environment_toggle':
            current_environments = rule.get('environments', [])
            print(f"Current environments: {current_environments}")
            
            if 'staging' not in current_environments:
                rule['environments'] = current_environments + ['staging']
                print(f"Updated environments: {rule['environments']}")
            else:
                print("Staging environment already exists in the rule")
            break
    else:
        print("❌ 'environment_toggle' rule not found in gate data")
    
    return updated_gate


def main():
    """Main function to update the feature gate."""
    
    # Get Console API Key from environment variable
    api_key = os.getenv('STATSIG_CONSOLE_API_KEY')
    
    if not api_key:
        print("Error: STATSIG_CONSOLE_API_KEY environment variable not set")
        print("Please set it with: export STATSIG_CONSOLE_API_KEY='your_console_api_key_here'")
        return
    
    gate_name = "development-test-gate"
    
    # Step 1: Retrieve the existing gate
    print("=" * 50)
    print("STEP 1: Retrieving existing feature gate")
    print("=" * 50)
    
    gate_data = get_feature_gate(api_key, gate_name)
    
    if not gate_data:
        print(f"Cannot proceed - gate '{gate_name}' not found")
        return
    
    # Step 2: Add staging environment to the rule
    print("\n" + "=" * 50)
    print("STEP 2: Adding staging environment to rule")
    print("=" * 50)
    
    updated_gate_data = add_staging_environment(gate_data)
    
    # Step 3: Update the gate using PATCH
    print("\n" + "=" * 50)
    print("STEP 3: Updating feature gate via PATCH")
    print("=" * 50)
    
    gate_id = gate_data.get('id')
    if gate_id:
        success = update_feature_gate(api_key, gate_id, updated_gate_data)
        
        if success:
            print("\n🎉 Success! The feature gate has been updated.")
            print("The 'environment_toggle' rule now includes both 'development' and 'staging' environments.")
        else:
            print(f"\n💥 Failed to update feature gate")
    else:
        print("❌ No gate ID found in the retrieved data")


if __name__ == "__main__":
    main()
