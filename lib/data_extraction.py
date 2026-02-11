"""
Data Extraction Module

Extracts non-computed attributes from Terraform plan.json using schema.json.
Based on spec/spec.md specification.
"""

import json
import sys
from typing import Any, Optional


class OriginValue:
  """Data class for original values from plan.json and schema.json"""

  def __init__(self, value=None, reference=None, required=False, description=""):
    self.value = value
    self.reference = reference
    self.required = required
    self.description = description

  def to_dict(self):
    """Convert to dictionary for JSON serialization"""
    return {
      'value': self.value,
      'reference': self.reference,
      'required': self.required,
      'description': self.description
    }

  def __repr__(self):
    return f"OriginValue(value={self.value!r}, reference={self.reference!r}, required={self.required}, description={self.description!r})"


def extract_data(plan_json: dict, schema_json: dict) -> list:
  """
  Extract non-computed attributes from plan.json using schema.json.

  Returns:
    list: [
      {
        "module": str,
        "address": str,
        "type": str,
        "name": str,
        "values": dict  # Nested structure with OriginValue instances at leaf nodes
      },
      ...
    ]
  """
  extracted_resources = []

  # Extract resources from planned_values
  resources_in_plan = _collect_resources_from_plan(plan_json)

  # Extract configuration expressions
  config_expressions = _extract_config_expressions(plan_json)

  # Build module variable mapping (module_name -> var_name -> reference)
  module_var_map = _build_module_variable_map(plan_json)

  # Process each resource
  for resource in resources_in_plan:
    resource_type = resource['type']
    address = resource['address']

    # Get schema for this resource type
    schema = _get_resource_schema(schema_json, resource_type)
    if not schema:
      print(f"WARNING: Schema not found for resource type '{resource_type}'", file=sys.stderr)
      continue

    # Get non-computed attributes from schema
    non_computed_attrs = _get_non_computed_attributes(schema)

    # Get configuration expressions for this resource
    expressions = config_expressions.get(address, {})

    # Extract values for each non-computed attribute
    values = _extract_values(
      resource['values'],
      non_computed_attrs,
      expressions,
      resource_type,
      address,
      resource.get('module'),
      module_var_map,
      schema
    )

    extracted_resources.append({
      'module': resource.get('module'),
      'address': address,
      'type': resource_type,
      'name': resource['name'],
      'values': values
    })

  return extracted_resources


def _collect_resources_from_plan(plan_json: dict) -> list:
  """Collect all resources from planned_values"""
  resources = []
  root = plan_json.get('planned_values', {}).get('root_module', {})

  # Root module resources
  for res in root.get('resources', []):
    resources.append({
      'address': res['address'],
      'type': res['type'],
      'name': res['name'],
      'values': res.get('values', {}),
      'module': None
    })

  # Child module resources
  for module in root.get('child_modules', []):
    module_address = module.get('address', '')
    module_name = module_address.replace('module.', '')

    for res in module.get('resources', []):
      resources.append({
        'address': res['address'],
        'type': res['type'],
        'name': res['name'],
        'values': res.get('values', {}),
        'module': module_name
      })

  return resources


def _build_module_variable_map(plan_json: dict) -> dict:
  """
  Build mapping of module variables to their source references.

  Returns:
    dict: {
      "module_name": {
        "var_name": "reference"
      }
    }
  """
  var_map = {}
  config = plan_json.get('configuration', {})
  root = config.get('root_module', {})

  for mod_name, mod_def in root.get('module_calls', {}).items():
    var_map[mod_name] = {}
    for var_name, expr in mod_def.get('expressions', {}).items():
      if 'references' in expr:
        # Use the same logic as _extract_resource_address
        refs = expr['references']
        resource_refs = [
          ref for ref in refs
          if not ref.startswith(('count.', 'each.'))
        ]
        if resource_refs:
          # Apply the same [-1]/[-2] logic
          if len(resource_refs) >= 2 and resource_refs[-1].startswith('module.'):
            var_map[mod_name][var_name] = resource_refs[-2]
          else:
            var_map[mod_name][var_name] = resource_refs[-1]

  return var_map


def _extract_config_expressions(plan_json: dict) -> dict:
  """Extract expressions from configuration section"""
  expressions = {}
  config = plan_json.get('configuration', {})
  root = config.get('root_module', {})

  # Root module resources
  for res in root.get('resources', []):
    expressions[res['address']] = res.get('expressions', {})

  # Child module resources
  for mod_name, mod_def in root.get('module_calls', {}).items():
    for res in mod_def.get('module', {}).get('resources', []):
      full_address = f"module.{mod_name}.{res['address']}"
      expressions[full_address] = res.get('expressions', {})

  return expressions


def _get_resource_schema(schema_json: dict, resource_type: str) -> Optional[dict]:
  """Get schema for a specific resource type"""
  providers = schema_json.get('provider_schemas', {})

  # Try AWS provider (most common)
  aws_provider = providers.get('registry.terraform.io/hashicorp/aws', {})
  resource_schemas = aws_provider.get('resource_schemas', {})

  if resource_type in resource_schemas:
    return resource_schemas[resource_type]

  # Try other providers if not found in AWS
  for provider_name, provider_data in providers.items():
    resource_schemas = provider_data.get('resource_schemas', {})
    if resource_type in resource_schemas:
      return resource_schemas[resource_type]

  return None


def _get_non_computed_attributes(schema: dict) -> dict:
  """
  Get non-computed attributes from schema.

  Excludes attributes that are computed-only (computed=true, required!=true, optional!=true)
  Includes deprecated attributes if they are settable (required or optional)
  """
  attributes = schema.get('block', {}).get('attributes', {})
  non_computed = {}

  for attr_name, attr_def in attributes.items():
    is_required = attr_def.get('required', False)
    is_optional = attr_def.get('optional', False)
    is_computed = attr_def.get('computed', False)

    # Include if required or optional (even if deprecated)
    # Exclude if computed-only (computed=true, required!=true, optional!=true)
    if is_required or is_optional:
      non_computed[attr_name] = attr_def

  return non_computed


def _extract_values(
  planned_values: dict,
  non_computed_attrs: dict,
  expressions: dict,
  resource_type: str,
  address: str,
  current_module: Optional[str],
  module_var_map: dict,
  schema: dict
) -> dict:
  """Extract values for non-computed attributes"""
  values = {}

  # Smart validation: warn only for truly unexpected attributes
  # Skip computed-only attributes and block_types (handled separately)
  all_schema_attrs = schema.get('block', {}).get('attributes', {})
  block_types = schema.get('block', {}).get('block_types', {})

  for attr_name in planned_values.keys():
    if attr_name not in non_computed_attrs:
      # Check if it's a known attribute in schema
      if attr_name in all_schema_attrs:
        # This is a computed-only attribute (expected)
        continue

      # Check if it's a block_type (handled separately)
      if attr_name in block_types:
        # This is a block type (expected)
        continue

      # If we reach here, it's truly unexpected
      print(f"WARNING: Attribute '{attr_name}' in resource '{address}' not found in schema", file=sys.stderr)

  # Process each non-computed attribute from schema
  for attr_name, attr_def in non_computed_attrs.items():
    description = attr_def.get('description', '')
    is_required = attr_def.get('required', False)
    is_optional = attr_def.get('optional', False)
    is_computed = attr_def.get('computed', False)

    # Check if value exists in planned_values
    if attr_name in planned_values:
      attr_value = planned_values[attr_name]

      # Check for references in configuration
      attr_expr = expressions.get(attr_name, {})
      references = attr_expr.get('references', [])

      # Process value (recursively for nested structures)
      values[attr_name] = _process_value(
        attr_value,
        references,
        is_required,
        description,
        current_module,
        module_var_map
      )

    # Check if exists in configuration but not in planned_values
    elif attr_name in expressions:
      attr_expr = expressions[attr_name]
      references = attr_expr.get('references', [])

      if references:
        # Has reference but no value in planned_values
        # Store reference information (extract resource address)
        reference = _extract_resource_address(references, current_module, module_var_map)
        if reference:
          values[attr_name] = OriginValue(
            value=None,
            reference=reference,
            required=is_required,
            description=description
          )

    # Not in planned_values nor in configuration
    else:
      # If optional AND computed, include with null value
      # (e.g., id, name_prefix - can be specified by user or computed)
      if is_optional and is_computed:
        values[attr_name] = OriginValue(
          value=None,
          reference=None,
          required=is_required,
          description=description
        )
      # Only warn if required
      elif is_required:
        print(f"WARNING: Attribute '{attr_name}' in resource '{address}' defined in schema but missing in plan", file=sys.stderr)

  return values


def _extract_resource_address(references: list, current_module: Optional[str] = None, module_var_map: dict = None) -> Optional[str]:
  """
  Extract resource address from references, resolving module variables.

  Terraform provides references in arrays with specific patterns:
  - Resource attributes: ["resource.name.attr", "resource.name"] → use [-1]
  - Module outputs: ["module.name.output", "module.name"] → use [-2] to keep output name
  - Variables: ["var.name"] → resolve using module_var_map if in a module

  Examples:
    - ["aws_iam_role.lambda.arn", "aws_iam_role.lambda"] -> "aws_iam_role.lambda"
    - ["module.vpc.vpc_id", "module.vpc"] -> "module.vpc.vpc_id"
    - ["var.vpc_id"] in module "compute" -> "module.network.vpc_id" (resolved)
  """
  if module_var_map is None:
    module_var_map = {}

  # Check for variable references first
  var_refs = [ref for ref in references if ref.startswith('var.')]
  if var_refs and current_module and current_module in module_var_map:
    # Resolve variable reference using module_var_map
    var_name = var_refs[0][4:]  # Remove 'var.' prefix
    if var_name in module_var_map[current_module]:
      return module_var_map[current_module][var_name]

  # Filter resource/module references (exclude data., local., count., each.)
  # Keep var. for now in case it wasn't resolved
  resource_refs = [
    ref for ref in references
    if not ref.startswith(('data.', 'local.', 'count.', 'each.'))
  ]

  # Remove var. references if they weren't resolved
  resource_refs = [ref for ref in resource_refs if not ref.startswith('var.')]

  if not resource_refs:
    return None

  # If last element starts with 'module.', use second-to-last to preserve output name
  # Otherwise, use last element (resource address without attribute)
  if len(resource_refs) >= 2 and resource_refs[-1].startswith('module.'):
    return resource_refs[-2]
  else:
    return resource_refs[-1]


def _process_value(value: Any, references: list, required: bool, description: str, current_module: Optional[str] = None, module_var_map: dict = None) -> Any:
  """
  Process a value recursively.

  Nested structures (dict/list) are preserved, with OriginValue at leaf nodes only.
  """
  # Handle None
  if value is None:
    # Only set reference if value is None
    reference = _extract_resource_address(references, current_module, module_var_map) if references else None
    return OriginValue(
      value=None,
      reference=reference,
      required=required,
      description=description
    )

  # Handle nested dict
  if isinstance(value, dict):
    result = {}
    for key, val in value.items():
      result[key] = _process_value(val, [], False, '')
    return result

  # Handle nested list
  if isinstance(value, list):
    result = []
    for item in value:
      result.append(_process_value(item, [], False, ''))
    return result

  # Leaf node with value - reference should be None since value exists
  return OriginValue(
    value=value,
    reference=None,
    required=required,
    description=description
  )


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
  import pickle
  from pathlib import Path

  parser = argparse.ArgumentParser(description='Test data extraction')
  parser.add_argument('plan_json', help='Path to plan.json')
  parser.add_argument('schema', help='Path to schema.json or schema directory')
  parser.add_argument('--output', help='Output JSON file path (optional)')
  parser.add_argument('--pickle-dump', help='Output pickle file path for Python object (optional)')
  args = parser.parse_args()

  # Load JSON files
  with open(args.plan_json) as f:
    plan_json = json.load(f)

  # Load schema from directory or file
  schema_path = Path(args.schema)
  if schema_path.is_dir():
    from schema_loader import load_merged_schema
    schema_json = load_merged_schema(args.schema)
  else:
    with open(args.schema) as f:
      schema_json = json.load(f)

  # Execute extraction
  result = extract_data(plan_json, schema_json)

  # Save pickle if requested (Python objects with OriginValue instances)
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
