#!/usr/bin/env python3
"""
View conversion module (Phase 2-3)

Converts OriginValue objects to ViewValue objects for display.
Input: List of resources with resolved OriginValue objects
Output: List of resources with ViewValue objects (ready for table generation)
"""

import sys
import json
import pickle
import argparse
from pathlib import Path

# Import OriginValue from data_extraction
sys.path.insert(0, str(Path(__file__).parent))
from data_extraction import OriginValue


class ViewValue:
  """Data class for view-ready values with resolved references"""

  def __init__(self, value=None, description="", required=False):
    self.value = value
    self.description = description
    self.required = required

  def to_dict(self):
    """Convert to dictionary for JSON serialization"""
    return {
      'value': self.value,
      'description': self.description,
      'required': self.required
    }


# Default attributes to exclude from view
DEFAULT_EXCLUDE_ATTRIBUTES = ['tags_all']


def _convert_origin_to_view(origin_value):
  """
  Convert OriginValue to ViewValue

  Args:
    origin_value: OriginValue instance or primitive value

  Returns:
    ViewValue instance or primitive value
  """
  # If not OriginValue, return as is
  if not hasattr(origin_value, 'value'):
    return origin_value

  # Convert reference to "(ref) identifier" format
  if origin_value.reference:
    value = f"(ref) {origin_value.reference}"
  else:
    value = origin_value.value

  # Convert to ViewValue
  return ViewValue(
    value=value,
    description=origin_value.description,  # Future: override with custom description
    required=origin_value.required
  )


def _process_values_recursive(values, exclude_attributes=None):
  """
  Recursively process values and convert OriginValue to ViewValue

  Args:
    values: Value to process (dict, list, OriginValue, or primitive)
    exclude_attributes: List of attribute names to exclude

  Returns:
    Converted value
  """
  if exclude_attributes is None:
    exclude_attributes = []

  if isinstance(values, dict):
    result = {}
    for key, val in values.items():
      # Skip excluded attributes
      if key in exclude_attributes:
        continue
      result[key] = _process_values_recursive(val, exclude_attributes)
    return result
  elif isinstance(values, list):
    return [_process_values_recursive(item, exclude_attributes) for item in values]
  elif hasattr(values, 'value'):
    # OriginValue instance
    return _convert_origin_to_view(values)
  else:
    # Primitive value
    return values


def convert_to_view_values(resolved_data, exclude_attributes=None):
  """
  Convert OriginValue objects to ViewValue objects

  Args:
    resolved_data: List of resources with resolved OriginValue objects
    exclude_attributes: List of attribute names to exclude (default: ['tags_all'])

  Returns:
    list: [
      {
        "resource_type": str,
        "resource_name": str,
        "values": dict  # ViewValue instances
      },
      ...
    ]
  """
  if exclude_attributes is None:
    exclude_attributes = DEFAULT_EXCLUDE_ATTRIBUTES

  view_resources = []
  for resource in resolved_data:
    # Recursively convert values
    converted_values = _process_values_recursive(
      resource['values'],
      exclude_attributes
    )

    # Create output resource data (remove internal information)
    view_resource = {
      'resource_type': resource['type'],
      'resource_name': resource['name'],
      'values': converted_values
    }

    view_resources.append(view_resource)

  return view_resources


def _serialize_for_json(obj):
  """
  Convert object to JSON serializable format

  Args:
    obj: Object to convert (ViewValue, dict, list, or primitive)

  Returns:
    JSON serializable object
  """
  if hasattr(obj, 'to_dict'):
    return obj.to_dict()
  elif isinstance(obj, dict):
    return {k: _serialize_for_json(v) for k, v in obj.items()}
  elif isinstance(obj, list):
    return [_serialize_for_json(item) for item in obj]
  else:
    return obj


def test():
  """Test function for development and debugging"""
  parser = argparse.ArgumentParser(
    description='Phase 2-3: Convert OriginValue to ViewValue'
  )
  parser.add_argument(
    'input_file',
    help='Input pickle file from Phase 2-2'
  )
  parser.add_argument(
    '--pickle-load',
    action='store_true',
    help='Load input as pickle file'
  )
  parser.add_argument(
    '--output',
    help='Output JSON file path (optional)'
  )
  parser.add_argument(
    '--pickle-dump',
    help='Output pickle file path (optional)'
  )
  parser.add_argument(
    '--exclude-attributes',
    nargs='*',
    default=None,
    help='Attributes to exclude from view (default: tags_all)'
  )

  args = parser.parse_args()

  # Load input data
  if args.pickle_load:
    with open(args.input_file, 'rb') as f:
      input_data = pickle.load(f)
    print(f"Loaded {len(input_data)} resources from pickle", file=sys.stderr)
  else:
    print("ERROR: Only pickle input is supported (use --pickle-load)", file=sys.stderr)
    sys.exit(1)

  # Convert to view values
  view_data = convert_to_view_values(input_data, args.exclude_attributes)
  print(f"Converted {len(view_data)} resources to ViewValue", file=sys.stderr)

  # Save pickle if requested
  if args.pickle_dump:
    with open(args.pickle_dump, 'wb') as f:
      pickle.dump(view_data, f)
    print(f"Pickle dump written to {args.pickle_dump}", file=sys.stderr)

  # Serialize for JSON output
  output_json = _serialize_for_json(view_data)

  # Output result
  if args.output:
    with open(args.output, 'w') as f:
      json.dump(output_json, f, indent=2, ensure_ascii=False)
    print(f"Output written to {args.output}", file=sys.stderr)
  else:
    print(json.dumps(output_json, indent=2, ensure_ascii=False))


if __name__ == '__main__':
  test()
