"""
Schema Loader Module

Load and merge resource type schemas from schema/d*/*.json directories.
Returns Terraform standard schema format for use by data_extraction.py.
"""

import json
import sys
from pathlib import Path


def load_merged_schema(schema_dir):
  """
  Load and merge all resource type schemas from schema/d*/*.json.

  Scans d0000, d0001, ... directories in sorted order.
  When the same resource type exists in multiple versions,
  the latest dXXXX takes priority with a warning.

  Args:
    schema_dir: Path to schema directory containing d*/ subdirectories

  Returns:
    dict: Terraform standard schema format:
      {
        "format_version": "1.0",
        "provider_schemas": {
          "registry.terraform.io/hashicorp/aws": {
            "resource_schemas": {
              "aws_iam_role": { ... },
              ...
            }
          }
        }
      }
  """
  schema_path = Path(schema_dir)

  if not schema_path.exists():
    print(f"ERROR: Schema directory not found: {schema_dir}", file=sys.stderr)
    sys.exit(1)

  # Find all d* directories sorted
  d_dirs = sorted(schema_path.glob('d*'))
  d_dirs = [d for d in d_dirs if d.is_dir()]

  if not d_dirs:
    print(f"ERROR: No schema files found in {schema_dir}/d*/", file=sys.stderr)
    print("Please run schema_manager.py to extract schemas from plan.json and schema.json.", file=sys.stderr)
    sys.exit(1)

  # Track resource types: resource_type -> (d_dir_name, provider, schema)
  resource_map = {}
  # Track duplicates for warning: resource_type -> list of d_dir_names
  seen_in = {}

  for d_dir in d_dirs:
    d_name = d_dir.name
    json_files = sorted(d_dir.glob('*.json'))

    for json_file in json_files:
      try:
        with open(json_file, 'r') as f:
          data = json.load(f)
      except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse {json_file}: {e}", file=sys.stderr)
        sys.exit(1)

      resource_type = data.get('resource_type')
      provider = data.get('provider')
      schema = data.get('schema')

      if not resource_type or not provider or schema is None:
        print(f"ERROR: Invalid schema file format: {json_file}", file=sys.stderr)
        print("Expected keys: resource_type, provider, schema", file=sys.stderr)
        sys.exit(1)

      # Track which d_dirs contain this resource type
      if resource_type not in seen_in:
        seen_in[resource_type] = []
      seen_in[resource_type].append(d_name)

      # Always overwrite with latest version
      resource_map[resource_type] = (d_name, provider, schema)

  # Warn about duplicates
  for resource_type, d_names in seen_in.items():
    if len(d_names) > 1:
      print(
        f"WARNING: {resource_type} found in multiple versions ({', '.join(d_names)}), using {d_names[-1]}",
        file=sys.stderr
      )

  # Build Terraform standard format
  # Group by provider
  providers = {}
  for resource_type, (d_name, provider, schema) in resource_map.items():
    if provider not in providers:
      providers[provider] = {}
    providers[provider][resource_type] = schema

  result = {
    "format_version": "1.0",
    "provider_schemas": {}
  }

  for provider, resource_schemas in providers.items():
    result["provider_schemas"][provider] = {
      "resource_schemas": resource_schemas
    }

  return result


def test():
  """Test function for development and debugging"""
  import argparse

  parser = argparse.ArgumentParser(
    description='Load and merge schema files from d*/ directories'
  )
  parser.add_argument(
    'schema_dir',
    help='Schema directory path containing d*/ subdirectories'
  )
  parser.add_argument(
    '--output', '-o',
    help='Output merged schema to JSON file'
  )

  args = parser.parse_args()

  result = load_merged_schema(args.schema_dir)

  # Count resources
  total = sum(
    len(pd.get('resource_schemas', {}))
    for pd in result.get('provider_schemas', {}).values()
  )
  print(f"Loaded {total} resource type schemas", file=sys.stderr)

  if args.output:
    with open(args.output, 'w') as f:
      json.dump(result, f, indent=2)
    print(f"Merged schema written to: {args.output}", file=sys.stderr)
  else:
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
  test()
