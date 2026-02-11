#!/bin/bash

# Phase 2-3 test: View Conversion
# Converts data to ViewValue format for HTML generation
#
# Usage: ./phase2_3_test.sh <test_dir>
# Example: ./phase2_3_test.sh test001

set -e  # Exit on error

if [ $# -ne 1 ]; then
  echo "Usage: $0 <test_dir>"
  echo "Example: $0 test001"
  exit 1
fi

TEST_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_DIR="$SCRIPT_DIR/$TEST_DIR"

if [ ! -d "$TARGET_DIR" ]; then
  echo "ERROR: Test directory not found: $TARGET_DIR"
  exit 1
fi

REFERENCE_PKL="$TARGET_DIR/reference.pkl"
VIEW_PKL="$TARGET_DIR/view.pkl"
VIEW_JSON="$TARGET_DIR/view.json"

echo "=========================================="
echo "Phase 2-3: View Conversion ($TEST_DIR)"
echo "=========================================="

# Check input files
if [ ! -f "$REFERENCE_PKL" ]; then
  echo "ERROR: reference.pkl not found in $TEST_DIR"
  echo "Run phase2_2_test.sh first"
  exit 1
fi

echo "Input:  $REFERENCE_PKL"
echo "Output: $VIEW_PKL, $VIEW_JSON"

python3 "$PROJECT_ROOT/lib/view_converter.py" "$REFERENCE_PKL" --pickle-load \
  --pickle-dump "$VIEW_PKL" \
  --output "$VIEW_JSON"

if [ $? -eq 0 ]; then
  echo "✓ SUCCESS"
  echo ""
  echo "Generated files:"
  echo "  - $VIEW_PKL"
  echo "  - $VIEW_JSON"
else
  echo "✗ FAILED"
  exit 1
fi
