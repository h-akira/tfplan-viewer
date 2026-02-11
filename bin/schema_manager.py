#!/usr/bin/env python3
"""
Schema Manager

Extract resource type schemas from plan.json and schema.json,
and save them as per-resource-type JSON files in schema/d*/ directories.
Only new resource types (diff) are saved in new version directories.
"""

import sys
import json
import argparse
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

from schema_loader import load_merged_schema


def _extract_resource_types_from_plan(plan_json):
  """
  Extract unique resource types from plan.json

  Args:
    plan_json: Parsed plan JSON data

  Returns:
    Set of resource type strings (e.g., {'aws_iam_role', 'aws_s3_bucket'})
  """
  resource_types = set()

  if 'resource_changes' in plan_json:
    for resource in plan_json['resource_changes']:
      if 'type' in resource:
        resource_types.add(resource['type'])

  return resource_types


def _extract_schemas_per_type(schema_json, resource_types):
  """
  Extract per-resource-type schema data from full schema.json

  Args:
    schema_json: Full Terraform provider schema JSON
    resource_types: Set of resource type strings to extract

  Returns:
    dict: {resource_type: {"resource_type": str, "provider": str, "schema": dict}}
  """
  result = {}

  if 'provider_schemas' in schema_json:
    for provider_name, provider_data in schema_json['provider_schemas'].items():
      if 'resource_schemas' in provider_data:
        for resource_type, resource_schema in provider_data['resource_schemas'].items():
          if resource_type in resource_types:
            result[resource_type] = {
              "resource_type": resource_type,
              "provider": provider_name,
              "schema": resource_schema
            }

  return result


def _get_latest_version_number(schema_dir):
  """
  Get the latest version number from existing d*/ directories.

  Returns:
    int or None: Latest version number, or None if no d*/ exists
  """
  schema_path = Path(schema_dir)
  if not schema_path.exists():
    return None

  d_dirs = sorted(schema_path.glob('d*'))
  d_dirs = [d for d in d_dirs if d.is_dir()]

  if not d_dirs:
    return None

  # Extract number from latest d_dir name (e.g., "d0005" -> 5)
  latest = d_dirs[-1].name
  try:
    return int(latest[1:])
  except ValueError:
    return None


def _get_existing_resource_types(schema_dir):
  """
  Get set of existing resource types from schema/d*/*.json

  Args:
    schema_dir: Path to schema directory

  Returns:
    set: Set of existing resource type strings
  """
  schema_path = Path(schema_dir)
  if not schema_path.exists():
    return set()

  existing = set()
  for d_dir in sorted(schema_path.glob('d*')):
    if not d_dir.is_dir():
      continue
    for json_file in d_dir.glob('*.json'):
      try:
        with open(json_file, 'r') as f:
          data = json.load(f)
        rt = data.get('resource_type')
        if rt:
          existing.add(rt)
      except (json.JSONDecodeError, KeyError):
        pass

  return existing


def _save_schemas(output_dir, version_num, schemas):
  """
  Save per-resource-type schema files to dXXXX/ directory.

  Args:
    output_dir: Base schema directory
    version_num: Version number for directory name
    schemas: dict of {resource_type: schema_data}
  """
  d_name = f"d{version_num:04d}"
  d_path = Path(output_dir) / d_name
  d_path.mkdir(parents=True, exist_ok=True)

  for resource_type, schema_data in schemas.items():
    file_path = d_path / f"{resource_type}.json"
    with open(file_path, 'w') as f:
      json.dump(schema_data, f, indent=2)

  return d_path


def main():
  """Main entry point"""
  parser = argparse.ArgumentParser(
    description='Extract and manage per-resource-type schema files'
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
    default='schema',
    help='Schema output directory (default: schema)'
  )
  parser.add_argument(
    '--force',
    action='store_true',
    help='Force create new version even without changes'
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
    resource_types = _extract_resource_types_from_plan(plan_json)

    # Extract per-type schemas from full schema.json
    extracted = _extract_schemas_per_type(schema_json, resource_types)

    # Check existing schemas
    existing_types = _get_existing_resource_types(args.output)
    latest_version = _get_latest_version_number(args.output)

    # Detect new resource types
    new_types = set(extracted.keys()) - existing_types

    # Display found resource types
    print(f"Found {len(resource_types)} resource types in plan.json:", file=sys.stderr)
    for rt in sorted(resource_types):
      suffix = " (new)" if existing_types and rt in new_types else ""
      print(f"  - {rt}{suffix}", file=sys.stderr)

    if existing_types:
      print(f"\nLoading existing schemas from {args.output}/...", file=sys.stderr)
      print(f"  ✓ Loaded {len(existing_types)} existing resource types", file=sys.stderr)

    if args.force:
      # Force mode: save all resource types to new version
      new_version = (latest_version + 1) if latest_version is not None else 0
      d_path = _save_schemas(args.output, new_version, extracted)
      print(f"\n✓ Created new version: {d_path}/", file=sys.stderr)
      print(f"✓ Saved {len(extracted)} resource type schemas (forced)", file=sys.stderr)

    elif latest_version is None:
      # First run: save all resource types as baseline
      d_path = _save_schemas(args.output, 0, extracted)
      print(f"\n✓ Created new version: {d_path}/", file=sys.stderr)
      print(f"✓ Saved {len(extracted)} resource type schemas", file=sys.stderr)

    elif new_types:
      # Save only new resource types as diff
      new_schemas = {rt: extracted[rt] for rt in new_types}

      print(f"\nComparing with existing schemas...", file=sys.stderr)
      for rt in sorted(new_types):
        print(f"  + {rt} (added)", file=sys.stderr)

      d_path = _save_schemas(args.output, latest_version + 1, new_schemas)
      print(f"\n✓ Created new version: {d_path}/", file=sys.stderr)
      print(f"✓ Saved {len(new_schemas)} resource type schema{'s' if len(new_schemas) > 1 else ''} (diff only)", file=sys.stderr)

    else:
      # No changes
      print(f"\nNo changes detected. Schema is up to date.", file=sys.stderr)

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
