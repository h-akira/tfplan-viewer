#!/usr/bin/env python3
"""
Resource configuration for HTML generation

リソースタイプごとのHTML出力設定を定義:
- ファイル配置（どのHTMLファイルに出力するか）
- パラメータ表示方法（展開可能、隠す、など）
- ソート順
- 優先度（同じファイルに複数リソースタイプがある場合）
"""


# Collapsible parameter function
def make_collapsible(param_name: str, value: str, format_json: bool = False) -> str:
  """
  Make a parameter value collapsible (click to expand)

  Args:
    param_name: Parameter name
    value: Parameter value
    format_json: Whether to format as JSON

  Returns:
    HTML string with collapsible content
  """
  import html
  escaped_value = html.escape(str(value))

  if format_json:
    try:
      import json
      # Try to pretty-print JSON
      parsed = json.loads(value) if isinstance(value, str) else value
      escaped_value = html.escape(json.dumps(parsed, indent=2, ensure_ascii=False))
    except:
      pass

  return f'''<details>
  <summary>表示</summary>
  <div class="collapsible-content">{escaped_value}</div>
</details>'''


# Resource type configurations
RESOURCE_CONFIGS = [
  # ==================== AWS IAM ====================
  {
    "resource_types": ["aws_iam_role"],
    "file_path": "aws/iam/role.html",
    "priority": 1,
    "sort_by": "name",  # Sort by this parameter value
    "special_parameters": [
      {
        "name": "assume_role_policy",
        "display": "collapsible",
        "format_json": True
      },
      {
        "name": "inline_policy",
        "display": "collapsible",
        "format_json": True
      }
    ],
    "column_widths": {
      "assume_role_policy": "200px",
      "description": "250px",
      "name": "180px",
      "tags": "200px",
      "attached_policies": "250px",
      "managed_policy_arns": "250px"
    }
  },
  {
    "resource_types": ["aws_iam_policy"],
    "file_path": "aws/iam/policy.html",
    "priority": 1,
    "sort_by": "name",
    "special_parameters": [
      {
        "name": "policy",
        "display": "collapsible",
        "format_json": True
      }
    ]
  },
  {
    "resource_types": ["aws_iam_user", "aws_iam_group"],
    "file_path": "aws/iam/user_group.html",
    "priority": 2,  # aws_iam_user first, then aws_iam_group
    "sort_by": "name"
  },
  {
    "resource_types": ["aws_iam_role_policy", "aws_iam_user_policy", "aws_iam_group_policy"],
    "file_path": "aws/iam/inline_policy.html",
    "priority": 1,
    "sort_by": "name",
    "special_parameters": [
      {
        "name": "policy",
        "display": "collapsible",
        "format_json": True
      }
    ]
  },

  # ==================== AWS S3 ====================
  {
    "resource_types": ["aws_s3_bucket"],
    "file_path": "aws/s3/bucket.html",
    "priority": 1,
    "sort_by": "bucket"
  },
  {
    "resource_types": ["aws_s3_bucket_policy"],
    "file_path": "aws/s3/bucket_policy.html",
    "priority": 1,
    "sort_by": "bucket",
    "special_parameters": [
      {
        "name": "policy",
        "display": "collapsible",
        "format_json": True
      }
    ]
  },
  {
    "resource_types": [
      "aws_s3_bucket_versioning",
      "aws_s3_bucket_server_side_encryption_configuration",
      "aws_s3_bucket_public_access_block"
    ],
    "file_path": "aws/s3/bucket_config.html",
    "priority": 2,
    "sort_by": "bucket"
  },

  # ==================== AWS Lambda ====================
  {
    "resource_types": ["aws_lambda_function"],
    "file_path": "aws/lambda/function.html",
    "priority": 1,
    "sort_by": "function_name",
    "special_parameters": [
      {
        "name": "environment",
        "display": "collapsible",
        "format_json": False
      }
    ]
  },
  {
    "resource_types": ["aws_lambda_permission"],
    "file_path": "aws/lambda/permission.html",
    "priority": 2,
    "sort_by": "function_name"
  },

  # ==================== AWS VPC ====================
  {
    "resource_types": ["aws_vpc"],
    "file_path": "aws/vpc/vpc.html",
    "priority": 1,
    "sort_by": "tags.Name"
  },
  {
    "resource_types": ["aws_subnet"],
    "file_path": "aws/vpc/subnet.html",
    "priority": 1,
    "sort_by": "tags.Name"
  },
  {
    "resource_types": ["aws_internet_gateway", "aws_nat_gateway"],
    "file_path": "aws/vpc/gateway.html",
    "priority": 2,
    "sort_by": "tags.Name"
  },
  {
    "resource_types": ["aws_route_table", "aws_route_table_association"],
    "file_path": "aws/vpc/route.html",
    "priority": 3,
    "sort_by": "tags.Name"
  },

  # ==================== AWS EC2 ====================
  {
    "resource_types": ["aws_instance"],
    "file_path": "aws/ec2/instance.html",
    "priority": 1,
    "sort_by": "tags.Name",
    "special_parameters": [
      {
        "name": "user_data",
        "display": "collapsible",
        "format_json": False
      }
    ]
  },
  {
    "resource_types": ["aws_security_group"],
    "file_path": "aws/ec2/security_group.html",
    "priority": 1,
    "sort_by": "name"
  },
  {
    "resource_types": ["aws_security_group_rule"],
    "file_path": "aws/ec2/security_group_rule.html",
    "priority": 2,
    "sort_by": "security_group_id"
  },
  {
    "resource_types": ["aws_key_pair"],
    "file_path": "aws/ec2/key_pair.html",
    "priority": 3,
    "sort_by": "key_name"
  },

  # ==================== AWS RDS ====================
  {
    "resource_types": ["aws_db_instance"],
    "file_path": "aws/rds/instance.html",
    "priority": 1,
    "sort_by": "identifier"
  },
  {
    "resource_types": ["aws_db_subnet_group", "aws_db_parameter_group"],
    "file_path": "aws/rds/config.html",
    "priority": 2,
    "sort_by": "name"
  },

  # ==================== AWS CloudWatch ====================
  {
    "resource_types": ["aws_cloudwatch_log_group"],
    "file_path": "aws/cloudwatch/log_group.html",
    "priority": 1,
    "sort_by": "name"
  },
  {
    "resource_types": ["aws_cloudwatch_metric_alarm"],
    "file_path": "aws/cloudwatch/alarm.html",
    "priority": 1,
    "sort_by": "alarm_name"
  },
]


def get_resource_config(resource_type: str) -> dict:
  """
  Get configuration for a specific resource type

  Args:
    resource_type: Resource type (e.g., "aws_iam_role")

  Returns:
    Configuration dict, or None if not found
  """
  for config in RESOURCE_CONFIGS:
    if resource_type in config["resource_types"]:
      return config
  return None


def get_file_path(resource_type: str) -> str:
  """
  Get file path for a resource type

  Args:
    resource_type: Resource type

  Returns:
    File path (e.g., "aws/iam/role.html")
  """
  config = get_resource_config(resource_type)
  if config:
    return config["file_path"]

  # Fallback: use provider_service pattern
  parts = resource_type.split('_', 2)
  if len(parts) >= 2:
    provider = parts[0]
    service = parts[1]
    return f"{provider}/{service}/other.html"
  else:
    return "unknown/other.html"


def get_sort_key(resource_type: str) -> str:
  """
  Get sort key for a resource type

  Args:
    resource_type: Resource type

  Returns:
    Sort key (e.g., "name", "tags.Name")
  """
  config = get_resource_config(resource_type)
  if config and "sort_by" in config:
    return config["sort_by"]
  return "name"  # Default


def get_priority(resource_type: str) -> int:
  """
  Get priority for a resource type

  Args:
    resource_type: Resource type

  Returns:
    Priority (lower number = higher priority)
  """
  config = get_resource_config(resource_type)
  if config and "priority" in config:
    return config["priority"]
  return 999  # Default low priority


def get_special_parameters(resource_type: str) -> list:
  """
  Get special parameter configurations for a resource type

  Args:
    resource_type: Resource type

  Returns:
    List of special parameter configs
  """
  config = get_resource_config(resource_type)
  if config and "special_parameters" in config:
    return config["special_parameters"]
  return []


def should_collapse_parameter(resource_type: str, param_name: str) -> dict:
  """
  Check if a parameter should be displayed as collapsible

  Args:
    resource_type: Resource type
    param_name: Parameter name

  Returns:
    Dict with 'collapsible' (bool) and 'format_json' (bool), or None
  """
  special_params = get_special_parameters(resource_type)
  for param_config in special_params:
    if param_config["name"] == param_name:
      if param_config.get("display") == "collapsible":
        return {
          "collapsible": True,
          "format_json": param_config.get("format_json", False)
        }
  return None


def get_column_widths(resource_type: str) -> dict:
  """
  Get column width configurations for a resource type

  Args:
    resource_type: Resource type

  Returns:
    Dict mapping column names to width strings (e.g., {"name": "180px"})
  """
  config = get_resource_config(resource_type)
  if config and "column_widths" in config:
    return config["column_widths"]
  return {}
