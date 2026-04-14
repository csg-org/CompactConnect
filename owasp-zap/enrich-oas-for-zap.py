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
    "userId": "740864a8-8091-7097-3bb4-d96fb1619a15",
    "attestationId": "00000000-0000-4000-8000-000000000000",
    "encumbranceId": "c8083de6-19a7-4e9c-8411-09e883fbc8ff",
    "flagId": "00000000-0000-4000-8000-000000000000",
    "investigationId": "00000000-0000-4000-8000-000000000000",
}


def enrich_spec(spec):
    """Add example values to all path parameters in the spec."""
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            for param in operation.get("parameters", []):
                if param.get("in") == "path" and "example" not in param:
                    name = param.get("name", "")
                    if name in PARAM_EXAMPLES:
                        param["example"] = PARAM_EXAMPLES[name]
    return spec


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

    # Count how many parameters were enriched
    count = 0
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue
            for param in operation.get("parameters", []):
                if param.get("in") == "path" and "example" in param:
                    count += 1
    print(f"Enriched {count} path parameters with example values")


if __name__ == "__main__":
    main()
