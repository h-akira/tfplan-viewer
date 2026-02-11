#!/usr/bin/env python3
"""
Resource Identifier Configuration

Defines how to identify resources when resolving references.
Each resource type can specify which attribute should be used as the identifier.
"""

import json
from typing import Optional


# Default resource identifier attributes
RESOURCE_IDENTIFIER_ATTRIBUTES = {
  'aws_iam_role': 'name',
  'aws_iam_policy': 'name',
  'aws_iam_user': 'name',
  'aws_iam_group': 'name',
  'aws_s3_bucket': 'bucket',
  'aws_lambda_function': 'function_name',
  'aws_security_group': 'name',
  'aws_vpc': 'tags.Name',
  'aws_subnet': 'tags.Name',
  'aws_instance': 'tags.Name',
  'aws_db_instance': 'identifier',
  'aws_rds_cluster': 'cluster_identifier',
  # Default: use 'name' attribute
}


def load_identifier_config(config_file: Optional[str] = None) -> dict:
  """
  Load resource identifier configuration

  Args:
    config_file: Optional path to JSON config file

  Returns:
    Dictionary mapping resource types to identifier attributes
  """
  config = dict(RESOURCE_IDENTIFIER_ATTRIBUTES)

  if config_file:
    try:
      with open(config_file, 'r') as f:
        custom_config = json.load(f)

      # Merge custom config (overrides defaults)
      config.update(custom_config)
      print(f"Loaded custom identifier config from {config_file}", file=__import__('sys').stderr)
    except FileNotFoundError:
      print(f"WARNING: Config file not found: {config_file}", file=__import__('sys').stderr)
      print("Using default configuration", file=__import__('sys').stderr)
    except json.JSONDecodeError as e:
      print(f"WARNING: Failed to parse config file {config_file}: {e}", file=__import__('sys').stderr)
      print("Using default configuration", file=__import__('sys').stderr)
    except Exception as e:
      print(f"WARNING: Failed to load config from {config_file}: {e}", file=__import__('sys').stderr)
      print("Using default configuration", file=__import__('sys').stderr)

  return config


def get_identifier_attribute(resource_type: str, config: Optional[dict] = None) -> str:
  """
  Get identifier attribute for a resource type

  Args:
    resource_type: Resource type (e.g., 'aws_iam_role')
    config: Optional custom config dictionary

  Returns:
    Identifier attribute name (default: 'name')
  """
  if config is None:
    config = RESOURCE_IDENTIFIER_ATTRIBUTES

  return config.get(resource_type, 'name')


if __name__ == '__main__':
  """Export default configuration as JSON for reference"""
  import sys
  import argparse

  parser = argparse.ArgumentParser(
    description='Resource identifier configuration utility'
  )
  parser.add_argument(
    '--export',
    help='Export default configuration to JSON file'
  )
  parser.add_argument(
    '--validate',
    help='Validate a configuration file'
  )

  args = parser.parse_args()

  if args.export:
    with open(args.export, 'w') as f:
      json.dump(RESOURCE_IDENTIFIER_ATTRIBUTES, f, indent=2)
    print(f"Default configuration exported to {args.export}", file=sys.stderr)

  elif args.validate:
    config = load_identifier_config(args.validate)
    print(f"Configuration valid. Loaded {len(config)} resource type mappings.", file=sys.stderr)
    print(json.dumps(config, indent=2))

  else:
    print("Usage:", file=sys.stderr)
    print("  --export FILE    Export default configuration to JSON file", file=sys.stderr)
    print("  --validate FILE  Validate and display configuration file", file=sys.stderr)
    sys.exit(1)
