#!/usr/bin/env python3
"""Enrich OpenAPI specs with example path parameter values for ZAP scanning.

ZAP's openapi import replaces {paramName} with the literal string "paramName"
when no example value is provided. This script patches the generated OAS specs
to include valid example values so ZAP constructs real, reachable URLs.

Usage:
    python3 enrich-oas-for-zap.py <input.json> <output.json>
"""

import json
import sys

# Known valid values for path parameters in the test environment
PARAM_EXAMPLES = {
    "compact": "aslp",
    "jurisdiction": "oh",
    "licenseType": "audiologist",
    "providerId": "33f813a7-9526-4bba-95d6-570fcc2a5a12",

    # Test user specifically created in test environment for modification by the ZAP scan
    "userId": "3478a468-10f1-7011-b884-a2b4987561b4",
    "attestationId": "jurisprudence-confirmation",
    "encumbranceId": "c8083de6-19a7-4e9c-8411-09e883fbc8ff",
    "flagId": "00000000-0000-4000-8000-000000000000",
    "investigationId": "3758ff63-1271-41d5-9257-54689192ac6a",
}


# Valid baseline request bodies for selected endpoints, keyed by (method, path).
# Only read-only endpoints are listed here — mutation endpoints would flood the
# test DB with junk records. ZAP uses each example as the baseline for active
# scanning, then fuzzes variants around it.
BODY_EXAMPLES = {
    # Read-only provider search (staff + public share one schema)
    ("post", "/v1/compacts/{compact}/providers/query"): {
        "query": {"jurisdiction": "oh"},
        "pagination": {"pageSize": 10},
    },
    ("post", "/v1/public/compacts/{compact}/providers/query"): {
        "query": {"jurisdiction": "oh"},
        "pagination": {"pageSize": 10},
    },
    # State API provider search — different schema, requires a date-time window
    ("post", "/v1/compacts/{compact}/jurisdictions/{jurisdiction}/providers/query"): {
        "query": {
            "startDateTime": "2024-01-01T00:00:00Z",
            "endDateTime": "2025-01-01T00:00:00Z",
        },
    },
}


# HTTP methods to strip from the spec before ZAP ingests it.
# DELETE is excluded to prevent ZAP from deleting staff users during scans.
EXCLUDED_METHODS = {"delete"}


def enrich_spec(spec):
    """Add example values to path parameters and fix schema issues."""
    for path, methods in list(spec.get("paths", {}).items()):
        # Remove excluded HTTP methods
        for method in EXCLUDED_METHODS:
            if method in methods:
                del methods[method]
                print(f"Removed {method.upper()} {path}")

        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            for param in operation.get("parameters", []):
                if param.get("in") == "path" and "example" not in param:
                    name = param.get("name", "")
                    if name in PARAM_EXAMPLES:
                        param["example"] = PARAM_EXAMPLES[name]

            body_example = BODY_EXAMPLES.get((method, path))
            if body_example is not None:
                json_content = (
                    operation.get("requestBody", {})
                    .get("content", {})
                    .get("application/json")
                )
                if json_content is not None and "example" not in json_content:
                    json_content["example"] = body_example

    # Fix arrays missing 'items' — CDK-generated specs sometimes omit this,
    # which is technically invalid OpenAPI and causes ZAP's parser to fail.
    for name, schema in spec.get("components", {}).get("schemas", {}).items():
        _fix_missing_array_items(schema)

    return spec


def _fix_missing_array_items(obj):
    """Recursively add items: {type: string} to arrays missing an items field."""
    if not isinstance(obj, dict):
        return
    if obj.get("type") == "array" and "items" not in obj:
        obj["items"] = {"type": "string"}
    for value in obj.values():
        if isinstance(value, dict):
            _fix_missing_array_items(value)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.json> <output.json>", file=sys.stderr)
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]

    with open(input_path) as f:
        spec = json.load(f)

    spec = enrich_spec(spec)

    with open(output_path, "w") as f:
        json.dump(spec, f, indent=2)

    # Count how many parameters and bodies were enriched
    param_count = 0
    body_count = 0
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            for param in operation.get("parameters", []):
                if param.get("in") == "path" and "example" in param:
                    param_count += 1
            json_content = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
            )
            if "example" in json_content:
                body_count += 1
    print(
        f"Enriched {param_count} path parameters and {body_count} request bodies"
    )


if __name__ == "__main__":
    main()
