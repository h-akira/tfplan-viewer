#!/usr/bin/env python3
"""
tfplan-viewer - Terraform Plan JSON to HTML Converter

Main script that integrates Phase 1-3 modules to generate HTML reports
from Terraform plan JSON files.
"""

import sys
import json
import argparse
from pathlib import Path

# Add lib directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

from schema_loader import load_merged_schema
from data_extraction import extract_data
from special_processor import process_special_resources
from special_config import load_special_configs, SPECIAL_RESOURCE_TYPES
from reference_resolver import resolve_references
from identifier_config import load_identifier_config, RESOURCE_IDENTIFIER_ATTRIBUTES
from view_converter import convert_to_view_values
from file_organizer import organize_html_files


def dump_special_config(output_file):
  """Dump default special resource configuration to JSON file"""
  try:
    with open(output_file, 'w') as f:
      json.dump(SPECIAL_RESOURCE_TYPES, f, indent=2)
    print(f"✓ Default special resource configuration exported to {output_file}", file=sys.stderr)
  except Exception as e:
    print(f"ERROR: Failed to export special config: {e}", file=sys.stderr)
    sys.exit(1)


def dump_identifier_config(output_file):
  """Dump default identifier configuration to JSON file"""
  try:
    with open(output_file, 'w') as f:
      json.dump(RESOURCE_IDENTIFIER_ATTRIBUTES, f, indent=2)
    print(f"✓ Default identifier configuration exported to {output_file}", file=sys.stderr)
  except Exception as e:
    print(f"ERROR: Failed to export identifier config: {e}", file=sys.stderr)
    sys.exit(1)


def validate_inputs(args):
  """Validate input files/directories exist"""
  if not Path(args.plan).exists():
    print(f"ERROR: File not found: {args.plan}", file=sys.stderr)
    sys.exit(1)


def load_config_if_specified(config_file, config_type):
  """Load configuration file if specified"""
  if not config_file:
    return None

  if config_type == 'special':
    return load_special_configs(config_file)
  elif config_type == 'identifier':
    return load_identifier_config(config_file)
  else:
    return None


def parse_arguments():
  """Parse command line arguments"""
  parser = argparse.ArgumentParser(
    description='Convert Terraform plan JSON to human-readable HTML',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  # Basic execution (uses schema/ directory by default)
  %(prog)s -p plan.json

  # Specify schema directory
  %(prog)s -p plan.json -s my_schema

  # Specify output directory
  %(prog)s -p plan.json -o my_output

  # Export default configurations
  %(prog)s --dump-special-config special.json
  %(prog)s --dump-identifier-config identifiers.json

  # Use custom configurations
  %(prog)s -p plan.json \\
    --special-config special.json \\
    --identifier-config identifiers.json \\
    --title "Production Environment"
"""
  )

  # Required arguments
  parser.add_argument(
    '-p', '--plan',
    required='--dump-special-config' not in sys.argv and '--dump-identifier-config' not in sys.argv,
    help='Terraform plan JSON file path'
  )
  parser.add_argument(
    '-s', '--schema',
    default='schema',
    help='Schema directory containing d*/ subdirectories (default: schema)'
  )

  # Optional arguments
  parser.add_argument(
    '-o', '--output-dir',
    default='html_output',
    help='HTML output directory (default: html_output)'
  )
  parser.add_argument(
    '--title',
    default='Terraform Plan',
    help='HTML report title (default: "Terraform Plan")'
  )
  parser.add_argument(
    '--special-config',
    help='Custom special resource configuration JSON file'
  )
  parser.add_argument(
    '--identifier-config',
    help='Custom identifier configuration JSON file'
  )

  # Config dump options
  parser.add_argument(
    '--dump-special-config',
    metavar='FILE',
    help='Export default special resource configuration to JSON file and exit'
  )
  parser.add_argument(
    '--dump-identifier-config',
    metavar='FILE',
    help='Export default identifier configuration to JSON file and exit'
  )

  return parser.parse_args()


def main():
  """Main entry point"""
  args = parse_arguments()

  # Handle config dump requests
  if args.dump_special_config:
    dump_special_config(args.dump_special_config)
    return

  if args.dump_identifier_config:
    dump_identifier_config(args.dump_identifier_config)
    return

  # Validate inputs
  validate_inputs(args)

  # Load configurations
  special_config = load_config_if_specified(args.special_config, 'special')
  identifier_config = load_config_if_specified(args.identifier_config, 'identifier')

  try:
    # Load schema from directory
    print(f"Loading schema from {args.schema}/...", file=sys.stderr)
    schema_json = load_merged_schema(args.schema)
    total_schemas = sum(
      len(pd.get('resource_schemas', {}))
      for pd in schema_json.get('provider_schemas', {}).values()
    )
    print(f"  ✓ Loaded {total_schemas} resource type schemas", file=sys.stderr)

    # Load plan JSON
    with open(args.plan, 'r') as f:
      plan_json = json.load(f)

    # Phase 1: Data Extraction
    print("Phase 1: Extracting data...", file=sys.stderr)
    extracted = extract_data(plan_json, schema_json)
    print(f"  ✓ Extracted {len(extracted)} resources", file=sys.stderr)

    # Phase 2-1: Special Resource Processing
    print("Phase 2-1: Processing special resources...", file=sys.stderr)
    processed = process_special_resources(extracted, special_config)
    merged_count = len(extracted) - len(processed)
    if merged_count > 0:
      print(f"  ✓ Merged {merged_count} special resources", file=sys.stderr)
    else:
      print(f"  ✓ No special resources to merge", file=sys.stderr)

    # Phase 2-2: Reference Resolution
    print("Phase 2-2: Resolving references...", file=sys.stderr)
    resolved = resolve_references(processed, identifier_config)
    print(f"  ✓ Resolved references in {len(resolved)} resources", file=sys.stderr)

    # Phase 2-3: View Conversion
    print("Phase 2-3: Converting to view...", file=sys.stderr)
    view_data = convert_to_view_values(resolved)
    print(f"  ✓ Converted {len(view_data)} resources", file=sys.stderr)

    # Phase 3: HTML Generation
    print("Phase 3: Generating HTML...", file=sys.stderr)
    organize_html_files(view_data, args.output_dir, args.title)

    # Count generated files
    output_path = Path(args.output_dir)
    html_files = list(output_path.rglob('*.html'))
    print(f"  ✓ Generated {len(html_files)} HTML files", file=sys.stderr)

    print(f"✓ HTML report generated: {args.output_dir}/index.html", file=sys.stderr)

  except FileNotFoundError as e:
    print(f"ERROR: File not found: {e}", file=sys.stderr)
    sys.exit(1)
  except json.JSONDecodeError as e:
    print(f"ERROR: Failed to parse JSON: {e}", file=sys.stderr)
    sys.exit(1)
  except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)


if __name__ == '__main__':
  main()
