#!/usr/bin/env python3
"""
Reference resolution module (Phase 2-2)

Resolves all references in OriginValue objects to human-readable identifiers.
Input: List of resources with OriginValue objects (special processing completed)
Output: List of resources with resolved references in OriginValue objects
"""

import sys
import json
import pickle
import argparse
from pathlib import Path

# Import OriginValue from data_extraction
sys.path.insert(0, str(Path(__file__).parent))
from data_extraction import OriginValue
from identifier_config import load_identifier_config, get_identifier_attribute


def _get_resource_identifier(resource, resource_type, identifier_config=None):
  """
  Get identifier value from a resource

  Args:
    resource: Resource data (with values field)
    resource_type: Resource type
    identifier_config: Optional custom identifier configuration

  Returns:
    Identifier string, or None if not found
  """
  # Get identifier attribute (default is 'name')
  identifier_attr = get_identifier_attribute(resource_type, identifier_config)

  # Handle nested attributes (e.g., 'tags.Name')
  if '.' in identifier_attr:
    parts = identifier_attr.split('.')
    value = resource.get('values', {})
    for part in parts:
      if isinstance(value, dict):
        value = value.get(part)
      else:
        return None

    # Extract value from OriginValue if necessary
    if hasattr(value, 'value'):
      return value.value
    return value
  else:
    # Single attribute case
    attr_value = resource.get('values', {}).get(identifier_attr)
    if hasattr(attr_value, 'value'):
      return attr_value.value
    return attr_value


def _resolve_single_reference(reference, all_resources, identifier_config=None):
  """
  Resolve a reference to an identifier string

  Args:
    reference: Reference address (e.g., "aws_iam_policy.s3_access_policy")
    all_resources: List of all resources
    identifier_config: Optional custom identifier configuration

  Returns:
    Identifier string, or original reference if not resolved
  """
  if not reference:
    return None

  # Handle module output references (e.g., module.network.vpc_id)
  if reference.startswith('module.'):
    parts = reference.split('.')
    if len(parts) >= 3:
      module_name = parts[1]
      output_name = parts[2]

      # Search for resources in this module
      for resource in all_resources:
        if resource.get('module') != f"module.{module_name}":
          continue

        resource_type = resource.get('type', '')
        expected_types = [resource_type]

        # Derive expected resource type from output name
        # e.g., vpc_id -> aws_vpc
        if output_name.endswith('_id'):
          base_name = output_name[:-3]  # vpc_id -> vpc
          expected_types.append(f"aws_{base_name}")

        # If resource type matches, consider this as the reference target
        if resource_type in expected_types:
          identifier = _get_resource_identifier(resource, resource['type'], identifier_config)
          if identifier:
            return identifier

    # Cannot map module reference
    return reference

  # Search for resource by address
  for resource in all_resources:
    # Check by address
    if resource.get('address') == reference:
      identifier = _get_resource_identifier(resource, resource['type'], identifier_config)
      # If identifier not found (e.g., no tags.Name), use address
      if identifier is None:
        return f"address {reference}"
      return identifier

    # Check by type.name
    resource_addr = f"{resource['type']}.{resource['name']}"
    if resource_addr == reference:
      identifier = _get_resource_identifier(resource, resource['type'], identifier_config)
      # If identifier not found, use address
      if identifier is None:
        return f"address {reference}"
      return identifier

  # Not found - return original reference
  return reference


def _resolve_value_recursive(value, all_resources, identifier_config=None):
  """
  Recursively resolve references in OriginValue objects

  Args:
    value: Value to process (dict, list, OriginValue, or primitive)
    all_resources: List of all resources
    identifier_config: Optional custom identifier configuration

  Returns:
    Processed value with resolved references
  """
  if isinstance(value, dict):
    result = {}
    for key, val in value.items():
      result[key] = _resolve_value_recursive(val, all_resources, identifier_config)
    return result
  elif isinstance(value, list):
    return [_resolve_value_recursive(item, all_resources, identifier_config) for item in value]
  elif hasattr(value, 'value'):
    # OriginValue instance - resolve reference
    if value.reference:
      resolved_ref = _resolve_single_reference(value.reference, all_resources, identifier_config)
      # Update reference to resolved identifier
      value.reference = resolved_ref
    return value
  else:
    # Primitive value - return as is
    return value


def resolve_references(extracted_data, identifier_config=None):
  """
  Resolve all references in the extracted data

  Args:
    extracted_data: List of resources with OriginValue objects
    identifier_config: Optional custom identifier configuration

  Returns:
    List of resources with resolved references
  """
  # Deep copy to avoid modifying original data
  import copy
  resolved_data = copy.deepcopy(extracted_data)

  # Resolve references in all resources
  for resource in resolved_data:
    resource['values'] = _resolve_value_recursive(resource['values'], resolved_data, identifier_config)

  return resolved_data


def test():
  """Test function for development and debugging"""
  parser = argparse.ArgumentParser(
    description='Phase 2-2: Resolve references in OriginValue objects'
  )
  parser.add_argument(
    'input_file',
    help='Input file (pickle or JSON from Phase 2-1)'
  )
  parser.add_argument(
    '--pickle-load',
    action='store_true',
    help='Load input from pickle file'
  )
  parser.add_argument(
    '--output',
    help='Output JSON file path (optional, for visualization)'
  )
  parser.add_argument(
    '--pickle-dump',
    help='Output pickle file path (for Phase 2-3)'
  )
  parser.add_argument(
    '--identifier-config',
    help='Custom identifier configuration JSON file'
  )

  args = parser.parse_args()

  # Load input data
  if args.pickle_load:
    with open(args.input_file, 'rb') as f:
      input_data = pickle.load(f)
    print(f"Loaded {len(input_data)} resources from pickle", file=sys.stderr)
  else:
    with open(args.input_file, 'r') as f:
      input_data = json.load(f)
    print(f"Loaded {len(input_data)} resources from JSON", file=sys.stderr)

  # Load identifier configuration
  identifier_config = None
  if args.identifier_config:
    identifier_config = load_identifier_config(args.identifier_config)

  # Resolve references
  resolved_data = resolve_references(input_data, identifier_config)
  print(f"Resolved references in {len(resolved_data)} resources", file=sys.stderr)

  # Save pickle dump if requested
  if args.pickle_dump:
    with open(args.pickle_dump, 'wb') as f:
      pickle.dump(resolved_data, f)
    print(f"Pickle dump written to {args.pickle_dump}", file=sys.stderr)

  # Save JSON output if requested
  if args.output:
    # Convert OriginValue to dict for JSON serialization
    def convert_for_json(obj):
      if hasattr(obj, 'to_dict'):
        return obj.to_dict()
      elif hasattr(obj, '__dict__'):
        return {
          'value': obj.value,
          'reference': getattr(obj, 'reference', None),
          'description': getattr(obj, 'description', ''),
          'required': getattr(obj, 'required', False)
        }
      elif isinstance(obj, dict):
        return {k: convert_for_json(v) for k, v in obj.items()}
      elif isinstance(obj, list):
        return [convert_for_json(item) for item in obj]
      else:
        return obj

    output_json = convert_for_json(resolved_data)

    with open(args.output, 'w') as f:
      json.dump(output_json, f, indent=2)
    print(f"Output written to {args.output}", file=sys.stderr)


if __name__ == '__main__':
  test()
