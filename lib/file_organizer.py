#!/usr/bin/env python3
"""
File organizer module (Phase 3-2)

Organizes HTML files and generates index.html.
Input: ViewValue data (pickle file from Phase 2-3)
Output: HTML file structure with index
"""

import sys
import json
import pickle
import argparse
from pathlib import Path

# Import functions from html_view and ViewValue from view_converter
sys.path.insert(0, str(Path(__file__).parent))
from html_view import (
  _group_resources_by_file,
  _generate_file_html,
  _generate_index_html
)
from view_converter import ViewValue


def organize_html_files(view_data, output_dir, title="Terraform Plan"):
  """
  Organize HTML files from view data

  Args:
    view_data: List of resources with ViewValue objects
    output_dir: Output directory path
    title: HTML page title

  Returns:
    Dict with file paths and statistics
  """
  output_path = Path(output_dir)
  output_path.mkdir(parents=True, exist_ok=True)

  # Group resources by file path
  file_groups = _group_resources_by_file(view_data)

  stats = {
    'files_created': 0,
    'total_resources': len(view_data),
    'file_paths': []
  }

  # Generate HTML files
  for file_path, file_data in file_groups.items():
    resources = file_data['resources']

    # Generate HTML content
    html_content = _generate_file_html(resources, file_path, title)

    # Write to file
    output_file = output_path / file_path
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
      f.write(html_content)

    stats['files_created'] += 1
    stats['file_paths'].append(file_path)

  # Generate index.html
  index_html = _generate_index_html(file_groups, title)
  index_path = output_path / 'index.html'

  with open(index_path, 'w') as f:
    f.write(index_html)

  stats['index_created'] = True

  return stats


def test():
  """Test function for development and debugging"""
  parser = argparse.ArgumentParser(
    description='Phase 3-2: Organize HTML files from ViewValue data'
  )
  parser.add_argument(
    'input_file',
    help='Input pickle file (view.pickle from Phase 2-3)'
  )
  parser.add_argument(
    '--output-dir',
    default='html_output',
    help='Output directory for HTML files (default: html_output)'
  )
  parser.add_argument(
    '--title',
    default='Terraform Plan',
    help='HTML page title'
  )

  args = parser.parse_args()

  # Load input data from pickle
  with open(args.input_file, 'rb') as f:
    view_data = pickle.load(f)

  print(f"Loaded {len(view_data)} resources from {args.input_file}", file=sys.stderr)

  # Organize files
  stats = organize_html_files(view_data, args.output_dir, args.title)

  print(f"\nHTML files organized:", file=sys.stderr)
  print(f"  Output directory: {args.output_dir}", file=sys.stderr)
  print(f"  Files created: {stats['files_created']}", file=sys.stderr)
  print(f"  Total resources: {stats['total_resources']}", file=sys.stderr)
  print(f"  Index created: {stats['index_created']}", file=sys.stderr)

  print(f"\nCreated files:", file=sys.stderr)
  for file_path in sorted(stats['file_paths']):
    print(f"  - {file_path}", file=sys.stderr)


if __name__ == '__main__':
  test()
