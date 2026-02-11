#!/usr/bin/env python3
"""
List attributes missing Japanese descriptions in schema JSON files.

Usage:
  python list_missing.py <schema_dir> [--dXXXX d0000]

Scans schema/d*/*.json (or a specific dXXXX) and prints attributes
that need descriptions. Skips computed-only attributes (computed=true
without optional=true).
"""

import json
import sys
from pathlib import Path


def needs_description(attr_name, attr_data):
  """Check if an attribute needs a description."""
  # Skip computed-only (not user-configurable)
  if attr_data.get('computed') and not attr_data.get('optional'):
    return False

  desc = attr_data.get('description', '')
  # Needs description if empty or not Japanese
  if not desc:
    return True
  # Has text but not Japanese (no CJK characters)
  if not any('\u3000' <= c <= '\u9fff' or '\uff00' <= c <= '\uffef' for c in desc):
    return True
  return False


def scan_attributes(block, path_prefix=""):
  """Recursively scan block for attributes needing descriptions."""
  results = []
  attrs = block.get('attributes', {})
  for name, data in sorted(attrs.items()):
    if needs_description(name, data):
      full_path = f"{path_prefix}{name}" if path_prefix else name
      results.append({
        'path': full_path,
        'type': data.get('type'),
        'required': data.get('required', False),
        'optional': data.get('optional', False),
        'computed': data.get('computed', False),
        'current_description': data.get('description', ''),
      })

  # Scan nested block_types
  for bt_name, bt_data in sorted(block.get('block_types', {}).items()):
    nested_block = bt_data.get('block', {})
    nested_prefix = f"{path_prefix}{bt_name}."
    results.extend(scan_attributes(nested_block, nested_prefix))

  return results


def main():
  import argparse
  parser = argparse.ArgumentParser(description='List attributes missing Japanese descriptions')
  parser.add_argument('schema_dir', help='Schema directory (e.g., schema)')
  parser.add_argument('--dXXXX', help='Specific version directory (e.g., d0000)')
  parser.add_argument('--json', action='store_true', help='Output as JSON')
  args = parser.parse_args()

  schema_path = Path(args.schema_dir)
  if not schema_path.exists():
    print(f"ERROR: {args.schema_dir} not found", file=sys.stderr)
    sys.exit(1)

  # Determine which directories to scan
  if args.dXXXX:
    d_dirs = [schema_path / args.dXXXX]
  else:
    d_dirs = sorted(d for d in schema_path.glob('d*') if d.is_dir())

  all_results = {}
  for d_dir in d_dirs:
    for json_file in sorted(d_dir.glob('*.json')):
      with open(json_file) as f:
        data = json.load(f)
      rt = data['resource_type']
      block = data['schema']['block']
      missing = scan_attributes(block)
      if missing:
        all_results[rt] = {
          'file': str(json_file),
          'missing': missing,
        }

  if args.json:
    print(json.dumps(all_results, indent=2, ensure_ascii=False))
  else:
    total = 0
    for rt, info in sorted(all_results.items()):
      print(f"\n{rt} ({info['file']})")
      for attr in info['missing']:
        flags = []
        if attr['required']:
          flags.append('required')
        if attr['optional']:
          flags.append('optional')
        if attr['computed']:
          flags.append('computed')
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        if attr['current_description']:
          cur = f' (en: "{attr["current_description"]}")'
        else:
          cur = ""
        print(f"  - {attr['path']}{flag_str}{cur}")
        total += 1
    print(f"\nTotal: {total} attributes need descriptions")


if __name__ == '__main__':
  main()
