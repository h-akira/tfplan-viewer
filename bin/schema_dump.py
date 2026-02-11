#!/usr/bin/env python3
"""
Schema Dump Utility

Extract only the resource types used in plan.json from schema.json.
This creates a minimal schema file containing only the necessary provider schemas.
"""

import sys
import json
import argparse
from pathlib import Path


def extract_resource_types_from_plan(plan_json):
  """
  Extract unique resource types from plan.json

  Args:
    plan_json: Parsed plan JSON data

  Returns:
    Set of resource type strings (e.g., {'aws_iam_role', 'aws_s3_bucket'})
  """
  resource_types = set()

  # Extract from resource_changes
  if 'resource_changes' in plan_json:
    for resource in plan_json['resource_changes']:
      if 'type' in resource:
        resource_types.add(resource['type'])

  return resource_types


def extract_schema_for_types(schema_json, resource_types):
  """
  Extract schema entries only for specified resource types

  Args:
    schema_json: Full schema JSON data
    resource_types: Set of resource type strings to extract

  Returns:
    Filtered schema JSON containing only specified resource types
  """
  extracted_schema = {
    'format_version': schema_json.get('format_version'),
    'provider_schemas': {}
  }

  # Iterate through all providers
  if 'provider_schemas' in schema_json:
    for provider_name, provider_data in schema_json['provider_schemas'].items():
      # Filter resource_schemas
      if 'resource_schemas' in provider_data:
        filtered_resources = {
          resource_type: resource_schema
          for resource_type, resource_schema in provider_data['resource_schemas'].items()
          if resource_type in resource_types
        }

        # Only include provider if it has matching resources
        if filtered_resources:
          extracted_schema['provider_schemas'][provider_name] = {
            'resource_schemas': filtered_resources
          }

  return extracted_schema


def main():
  """Main entry point"""
  parser = argparse.ArgumentParser(
    description='Extract resource schemas from schema.json based on plan.json'
  )
  parser.add_argument(
    '-p', '--plan',
    required=True,
    help='Terraform plan JSON file path'
  )
  parser.add_argument(
    '-s', '--schema',
    required=True,
    help='Terraform provider schema JSON file path'
  )
  parser.add_argument(
    '-o', '--output',
    default='schema_extracted.json',
    help='Output file path (default: schema_extracted.json)'
  )

  args = parser.parse_args()

  # Validate input files
  if not Path(args.plan).exists():
    print(f"ERROR: Plan file not found: {args.plan}", file=sys.stderr)
    sys.exit(1)

  if not Path(args.schema).exists():
    print(f"ERROR: Schema file not found: {args.schema}", file=sys.stderr)
    sys.exit(1)

  try:
    # Load JSON files
    with open(args.plan, 'r') as f:
      plan_json = json.load(f)

    with open(args.schema, 'r') as f:
      schema_json = json.load(f)

    # Extract resource types from plan
    resource_types = extract_resource_types_from_plan(plan_json)
    print(f"Found {len(resource_types)} resource types in plan.json:", file=sys.stderr)
    for rt in sorted(resource_types):
      print(f"  - {rt}", file=sys.stderr)

    # Extract schema for those types
    extracted_schema = extract_schema_for_types(schema_json, resource_types)

    # Count extracted resources
    total_resources = sum(
      len(provider_data.get('resource_schemas', {}))
      for provider_data in extracted_schema.get('provider_schemas', {}).values()
    )

    # Write output
    with open(args.output, 'w') as f:
      json.dump(extracted_schema, f, indent=2)

    print(f"\n✓ Extracted {total_resources} resource schemas", file=sys.stderr)
    print(f"✓ Output written to: {args.output}", file=sys.stderr)

  except json.JSONDecodeError as e:
    print(f"ERROR: Failed to parse JSON: {e}", file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)


if __name__ == '__main__':
  main()
