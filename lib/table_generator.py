#!/usr/bin/env python3
"""
Table generator module (Phase 3-1)

Generates HTML table strings from ViewValue data.
Input: Resources with ViewValue objects
Output: HTML table strings
"""

import sys
from pathlib import Path

# Import table generation functions from html_view
sys.path.insert(0, str(Path(__file__).parent))
from html_view import (
  _generate_individual_table,
  _generate_list_table,
  HTML_STYLE,
  LIST_TABLE_TYPES
)


def generate_table(resources, table_type='individual', resource_type=None):
  """
  Generate HTML table for resources

  Args:
    resources: Single resource (dict) for individual table,
               or list of resources for list table
    table_type: 'individual' or 'list'
    resource_type: Resource type (required for list tables)

  Returns:
    HTML string (table only, without <html> wrapper)
  """
  if table_type == 'list':
    if not isinstance(resources, list):
      resources = [resources]
    if not resource_type:
      raise ValueError("resource_type is required for list tables")
    return _generate_list_table(resources, resource_type)
  else:
    # Individual table
    if isinstance(resources, list):
      # Multiple individual tables
      html_parts = []
      for resource in resources:
        html_parts.append(_generate_individual_table(resource))
      return '\n\n'.join(html_parts)
    else:
      # Single resource
      return _generate_individual_table(resources)


def get_table_type(resource_type):
  """
  Determine table type for a resource type

  Args:
    resource_type: Resource type string

  Returns:
    'list' or 'individual'
  """
  return 'list' if resource_type in LIST_TABLE_TYPES else 'individual'


def generate_full_html(table_html, title="Terraform Plan"):
  """
  Wrap table HTML with full HTML document structure

  Args:
    table_html: HTML table string
    title: Page title

  Returns:
    Full HTML document string
  """
  html = []
  html.append('<!DOCTYPE html>')
  html.append('<html lang="ja">')
  html.append('<head>')
  html.append('  <meta charset="UTF-8">')
  html.append('  <meta name="viewport" content="width=device-width, initial-scale=1.0">')
  html.append(f'  <title>{title}</title>')
  html.append(HTML_STYLE)
  html.append('</head>')
  html.append('<body>')
  html.append(f'  <h1>{title}</h1>')
  html.append(table_html)
  html.append('</body>')
  html.append('</html>')
  return '\n'.join(html)


def main():
  """Main entry point for table generation (for testing)"""
  import json
  import argparse

  parser = argparse.ArgumentParser(
    description='Phase 3-1: Generate HTML tables from ViewValue data'
  )
  parser.add_argument(
    'input_file',
    help='Input JSON file (view.json from Phase 2-3)'
  )
  parser.add_argument(
    '--output',
    help='Output HTML file path'
  )
  parser.add_argument(
    '--table-type',
    choices=['individual', 'list', 'auto'],
    default='auto',
    help='Table type (default: auto-detect from resource type)'
  )
  parser.add_argument(
    '--title',
    default='Terraform Plan',
    help='HTML page title'
  )

  args = parser.parse_args()

  # Load input data
  with open(args.input_file, 'r') as f:
    view_data = json.load(f)

  print(f"Loaded {len(view_data)} resources from {args.input_file}", file=sys.stderr)

  # Generate tables
  table_parts = []
  for resource in view_data:
    resource_type = resource['resource_type']

    # Determine table type
    if args.table_type == 'auto':
      table_type = get_table_type(resource_type)
    else:
      table_type = args.table_type

    # Generate table
    if table_type == 'list':
      # For list tables, group by resource type
      # (This is simplified - real implementation should group resources)
      table_html = generate_table([resource], table_type, resource_type)
    else:
      table_html = generate_table(resource, table_type)

    table_parts.append(table_html)

  # Combine all tables
  combined_table_html = '\n\n'.join(table_parts)

  # Wrap with full HTML
  full_html = generate_full_html(combined_table_html, args.title)

  # Output
  if args.output:
    with open(args.output, 'w') as f:
      f.write(full_html)
    print(f"HTML output written to {args.output}", file=sys.stderr)
  else:
    print(full_html)


if __name__ == '__main__':
  main()
