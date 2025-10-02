"""
Feature Flag Management Stack

This stack manages feature flags through CloudFormation custom resources.
Feature flags enable/disable functionality dynamically across environments without code deployments.

While we initially create the flag through CDK deployments, updates to the flag configuration are managed through
the respective StatSig account console.

When a flag is no longer used, removing it from this stack should result in cleaning up all the environment based rules
for the flag and deleting it from StatSig once it has been removed from all environments.

Feature Flag Lifecycle:
-----------------------
1. **Creation** (on_create):
   - Creates a new StatSig feature gate if it doesn't exist
   - Adds an environment-specific rule (e.g., '<env name>-rule') to the gate
   - If auto_enable=True: passPercentage=100 (enabled)
   - If auto_enable=False: passPercentage=0 (disabled)

2. **Updates** (on_update):
   - Feature flags are IMMUTABLE once created in an environment
   - Updates are no-ops to prevent overwriting manual console changes

3. **Deletion** (on_delete):
   - Removes the environment-specific rule from the gate
   - If it's the last rule, deletes the entire gate
   - Other environments' rules remain untouched

StatSig Environment Mapping:
-------------------
StatSig has three fixed environment names, so we must map our environments to one of the three environments
- test → development (StatSig tier)
- beta → staging (StatSig tier)
- prod → production (StatSig tier)
- sandbox/other → development (StatSig tier, default)


Checking Flags in Lambda:
-------------------------
There is a common feature flag client python module that can be used to check if a flag is enabled in StatSig

```python
from cc_common.feature_flag_client import is_feature_enabled, FeatureFlagContext

# Simple check
if is_feature_enabled('my-feature-flag-name'):
    # run feature gated code if enabled

# With targeting context
context = FeatureFlagContext(
    user_id='user-123',
    custom_attributes={'compact': 'aslp', 'licenseType': 'slp'}
)
if is_feature_enabled('my-feature-flag-name', context=context):
    # run feature gated code if enabled
```

Custom Attributes:
-----------------
- Values can be strings (converted to lists) or lists
- Used for targeting specific subsets of users/requests
- Examples: compact, jurisdiction, licenseType, etc.
"""

from __future__ import annotations

from common_constructs.stack import AppStack
from constructs import Construct

from stacks.feature_flag_stack.feature_flag_resource import FeatureFlagEnvironmentName, FeatureFlagResource


class FeatureFlagStack(AppStack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment_name: str,
        **kwargs,
    ):
        super().__init__(scope, construct_id, environment_name=environment_name, **kwargs)

        # Feature Flags are deployed through a custom resource
        # one per flag
        self.example_flag = FeatureFlagResource(
            self,
            'ExampleFlag',
            flag_name='example-flag',
            # This causes the flag to automatically be set to enabled for every environment in the list
            auto_enable_envs=[
                FeatureFlagEnvironmentName.TEST,
                FeatureFlagEnvironmentName.BETA,
                FeatureFlagEnvironmentName.PROD,
                FeatureFlagEnvironmentName.SANDBOX,
            ],
            # Note that flags are not updated once set and must be manually updated through the console
            custom_attributes={'compact': ['aslp']},
            environment_name=environment_name,
        )
