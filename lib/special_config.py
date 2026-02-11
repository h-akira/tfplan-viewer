"""
Special Resource Configuration

Defines how dependent resources should be merged into their parent resources.
Example: aws_iam_role_policy_attachment -> aws_iam_role
"""

import json
from typing import Optional

# Default special resource type configurations
SPECIAL_RESOURCE_TYPES = [
  {
    "type": "aws_iam_role_policy_attachment",
    "merge_into": {
      "parent_type": "aws_iam_role",
      "parent_key": "attached_policies",
      "match_by": "role",
      "exclude_keys": ["role", "id"]
    }
  },
  {
    "type": "aws_subnet",
    "merge_into": {
      "parent_type": "aws_vpc",
      "parent_key": "subnets",
      "match_by": "vpc_id",
      "exclude_keys": ["vpc_id"]
    }
  }
]


def load_special_configs(config_file: Optional[str] = None) -> list:
  """
  Load special resource configurations.

  Args:
    config_file: Optional path to external JSON configuration file

  Returns:
    list: Special resource type configurations
  """
  if config_file:
    try:
      with open(config_file, 'r') as f:
        return json.load(f)
    except Exception as e:
      print(f"WARNING: Failed to load special config from {config_file}: {e}")
      print("Using default configurations")

  return SPECIAL_RESOURCE_TYPES


def get_special_config(resource_type: str, configs: Optional[list] = None) -> Optional[dict]:
  """
  Get special configuration for a resource type.

  Args:
    resource_type: Resource type (e.g., "aws_iam_role_policy_attachment")
    configs: Optional list of configurations (defaults to SPECIAL_RESOURCE_TYPES)

  Returns:
    dict: Configuration for the resource type, or None if not found
  """
  if configs is None:
    configs = SPECIAL_RESOURCE_TYPES

  for config in configs:
    if config['type'] == resource_type:
      return config

  return None
