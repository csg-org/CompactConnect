#!/usr/bin/env python3
"""
Simple test script for Statsig feature flags.
This script checks if the 'first-flag' feature flag is enabled or disabled.
"""

import os
from statsig import statsig, StatsigOptions, StatsigEnvironmentTier
from statsig.statsig_user import StatsigUser


def main():
    # Get the server secret key from environment variable
    # You'll need to set this: export STATSIG_SERVER_SECRET_KEY="your_actual_key_here"
    server_secret_key = 'secret-z0vOLM3ENYOFrlAeNpJsTHHftdVbOybyk5JHDEKFdLe'
    
    if not server_secret_key:
        print("Error: STATSIG_SERVER_SECRET_KEY environment variable not set")
        print("Please set it with: export STATSIG_SERVER_SECRET_KEY='your_actual_key_here'")
        return
    
    try:
        # Initialize Statsig with your server secret key
        print("Initializing Statsig...")
        statsig.initialize(server_secret_key, options=StatsigOptions(tier=StatsigEnvironmentTier.development))
        
        # Create a test user (you can customize this as needed)
        test_user = StatsigUser(
            user_id="test-user-1234"
        )
        
        # Check the 'first-flag' feature flag
        flag_name = 'development-test-gate'
        print(f"Checking feature flag: {flag_name}")

        result = statsig.check_gate(test_user, flag_name)
        print(result)
        
        if result:
            print(f"✅ Feature flag '{flag_name}' is ENABLED")
            print("This feature is turned on!")
        else:
            print(f"❌ Feature flag '{flag_name}' is DISABLED")
            print("This feature is turned off!")
            
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        # Always shutdown Statsig before the application exits
        print("Shutting down Statsig...")
        statsig.shutdown()


if __name__ == "__main__":
    main()
