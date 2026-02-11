"""
Special Resource Processor (Phase 2-1)

Merges dependent resources into their parent resources based on configuration.
Example: aws_iam_role_policy_attachment -> aws_iam_role.attached_policies

Based on formatting_data.py's _process_special_aws_iam_role_policy_attachment implementation.
"""

import json
import sys
import pickle
from typing import Optional
from data_extraction import OriginValue
from special_config import load_special_configs


def process_special_resources(extracted_data: list, special_configs: Optional[list] = None) -> list:
  """
  Process special resources by merging dependent resources into their parents.

  Args:
    extracted_data: List of extracted resources (with OriginValue objects)
    special_configs: Optional list of special resource configurations

  Returns:
    list: Processed resources with dependent resources merged
  """
  if special_configs is None:
    special_configs = load_special_configs()

  # Create a working copy to avoid modifying input
  result_resources = list(extracted_data)

  # Separate special resources from normal resources
  special_resources = []
  normal_resources = []

  # Build set of special resource types for quick lookup
  special_types = {config['type'] for config in special_configs}

  for resource in result_resources:
    if resource['type'] in special_types:
      special_resources.append(resource)
    else:
      normal_resources.append(resource)

  # Process each special resource
  for special_res in special_resources:
    config = _get_config_for_type(special_res['type'], special_configs)
    if not config:
      print(f"WARNING: No config found for special resource type '{special_res['type']}'", file=sys.stderr)
      continue

    merge_config = config['merge_into']
    parent_type = merge_config['parent_type']
    parent_key = merge_config['parent_key']
    match_by = merge_config['match_by']
    exclude_keys = merge_config.get('exclude_keys', [])

    # Find parent resource
    parent = _find_parent_resource(
      special_res,
      normal_resources,
      parent_type,
      match_by
    )

    if not parent:
      print(f"WARNING: Parent resource not found for '{special_res['address']}'", file=sys.stderr)
      continue

    # Merge dependent resource into parent
    _merge_dependent_resource(
      special_res,
      parent,
      parent_key,
      match_by,
      exclude_keys
    )

  return normal_resources


def _get_config_for_type(resource_type: str, configs: list) -> Optional[dict]:
  """Get configuration for a specific resource type"""
  for config in configs:
    if config['type'] == resource_type:
      return config
  return None


def _find_parent_resource(
  dependent: dict,
  resources: list,
  parent_type: str,
  match_by: str
) -> Optional[dict]:
  """
  Find parent resource by matching the reference in the dependent resource.

  Based on formatting_data.py's _process_special_aws_iam_role_policy_attachment.

  Args:
    dependent: Dependent resource (e.g., aws_iam_role_policy_attachment)
    resources: List of all normal resources
    parent_type: Parent resource type (e.g., "aws_iam_role")
    match_by: Attribute name to match (e.g., "role")

  Returns:
    dict: Parent resource, or None if not found
  """
  # Get the match field from dependent resource
  match_field = dependent['values'].get(match_by)
  if not match_field or not hasattr(match_field, 'value'):
    print(f"WARNING: Special resource '{dependent['address']}' has no {match_by} field", file=sys.stderr)
    return None

  # Determine search criteria (reference or value)
  reference_identifier = None
  value_identifier = None

  if hasattr(match_field, 'reference') and match_field.reference:
    # Reference case (e.g., "aws_iam_role.lambda_role")
    reference_identifier = match_field.reference
  elif hasattr(match_field, 'value') and match_field.value:
    # Value case (e.g., "sample002-lambda-role")
    value_identifier = match_field.value

  # Search for parent resource
  target_parent = None

  for resource in resources:
    if resource['type'] != parent_type:
      continue

    # Reference case: check by address or type.name
    if reference_identifier:
      if resource.get('address') == reference_identifier:
        target_parent = resource
        break
      resource_addr = f"{resource['type']}.{resource['name']}"
      if resource_addr == reference_identifier:
        target_parent = resource
        break

    # Value case: check by name field (or other identifier)
    elif value_identifier:
      # Assume 'name' field for matching (could be configurable)
      name_field = resource['values'].get('name')
      if name_field and hasattr(name_field, 'value'):
        if name_field.value == value_identifier:
          target_parent = resource
          break

  if not target_parent:
    identifier_str = reference_identifier if reference_identifier else f"name={value_identifier}"
    print(f"WARNING: Referenced {parent_type} '{identifier_str}' not found for '{dependent['address']}'", file=sys.stderr)

  return target_parent


def _merge_dependent_resource(
  dependent: dict,
  parent: dict,
  parent_key: str,
  match_by: str,
  exclude_keys: list
):
  """
  Merge dependent resource attributes into parent resource.

  Args:
    dependent: Dependent resource
    parent: Parent resource
    parent_key: Key in parent where dependent attributes will be merged
    match_by: Attribute used for matching (to be excluded)
    exclude_keys: Additional attributes to exclude from merge
  """
  # Initialize parent_key as array if not exists
  if parent_key not in parent['values']:
    parent['values'][parent_key] = []

  # Collect all attributes except excluded ones
  merged_attrs = {}
  all_exclude = set(exclude_keys) | {match_by}

  for key, value in dependent['values'].items():
    if key not in all_exclude:
      merged_attrs[key] = value

  # Add to parent's array
  parent['values'][parent_key].append(merged_attrs)


def _serialize_for_json(obj):
  """Convert OriginValue instances to dict for JSON serialization"""
  if isinstance(obj, OriginValue):
    return obj.to_dict()
  elif isinstance(obj, dict):
    return {k: _serialize_for_json(v) for k, v in obj.items()}
  elif isinstance(obj, list):
    return [_serialize_for_json(item) for item in obj]
  else:
    return obj


def test():
  """Test function using argparse"""
  import argparse

  parser = argparse.ArgumentParser(description='Process special resources')
  parser.add_argument('input_file', help='Path to extracted data (pickle)')
  parser.add_argument('--pickle-load', action='store_true', help='Load input as pickle file')
  parser.add_argument('--output', help='Output JSON file path (optional)')
  parser.add_argument('--pickle-dump', help='Output pickle file path (optional)')
  parser.add_argument('--config', help='Path to special config JSON file (optional)')
  args = parser.parse_args()

  # Load input data
  if args.pickle_load:
    with open(args.input_file, 'rb') as f:
      extracted_data = pickle.load(f)
    print(f"Loaded {len(extracted_data)} resources from pickle", file=sys.stderr)
  else:
    print("ERROR: Only pickle input is supported (use --pickle-load)", file=sys.stderr)
    sys.exit(1)

  # Load special configs
  special_configs = load_special_configs(args.config)

  # Process special resources
  result = process_special_resources(extracted_data, special_configs)
  print(f"Processed: {len(result)} normal resources ({len(extracted_data) - len(result)} merged)", file=sys.stderr)

  # Save pickle if requested
  if args.pickle_dump:
    with open(args.pickle_dump, 'wb') as f:
      pickle.dump(result, f)
    print(f"Pickle dump written to {args.pickle_dump}", file=sys.stderr)

  # Serialize for JSON output
  result_serialized = _serialize_for_json(result)

  # Output result
  if args.output:
    with open(args.output, 'w') as f:
      json.dump(result_serialized, f, indent=2, ensure_ascii=False)
    print(f"Output written to {args.output}", file=sys.stderr)
  else:
    print(json.dumps(result_serialized, indent=2, ensure_ascii=False))


if __name__ == '__main__':
  test()
