#!/usr/bin/env python3
"""
Script to create a feature gate in Statsig using the Console API.
This script creates a feature gate that is enabled in the development environment tier.
"""

import os
import json
import requests
from typing import Dict, Any


def create_feature_gate(
    api_key: str,
    gate_name: str = "development-test-gate",
    description: str = "Test feature gate enabled in development environment"
) -> Dict[str, Any]:
    
    # API endpoint and headers
    api_url = "https://statsigapi.net/console/v1/gates"
    headers = {
        "STATSIG-API-KEY": api_key,
        "STATSIG-API-VERSION": "20240601",  # Latest API version
        "Content-Type": "application/json"
    }
    
    # Feature gate configuration - simplified payload based on API docs
    gate_payload = {
        "name": gate_name,
        "description": description,
        "isEnabled": True,
        "rules": [
            {
                "name": "environment_toggle",
                "conditions": [],
                "environments": ["development"],
                "passPercentage": 100

            }
        ]
    }
    
    requests.post(
        api_url,
        headers=headers,
        data=json.dumps(gate_payload),
        timeout=30
    )



def main():

    api_key = os.getenv('STATSIG_CONSOLE_API_KEY')
    
    create_feature_gate(
        api_key=api_key,
        gate_name="development-test-gate",
        description="Test feature gate enabled in development environment tier"
    )


if __name__ == "__main__":
    main()
