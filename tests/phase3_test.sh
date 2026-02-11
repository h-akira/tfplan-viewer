#!/bin/bash

# Phase 3 test: HTML Generation
# Generates HTML files from ViewValue data
#
# Usage: ./phase3_test.sh <test_dir>
# Example: ./phase3_test.sh test001

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

VIEW_PKL="$TARGET_DIR/view.pkl"
HTML_OUTPUT="$TARGET_DIR/html_output"

echo "=========================================="
echo "Phase 3: HTML Generation ($TEST_DIR)"
echo "=========================================="

# Check input files
if [ ! -f "$VIEW_PKL" ]; then
  echo "ERROR: view.pkl not found in $TEST_DIR"
  echo "Run phase2_3_test.sh first"
  exit 1
fi

echo "Input:  $VIEW_PKL"
echo "Output: $HTML_OUTPUT/"

python3 "$PROJECT_ROOT/lib/file_organizer.py" "$VIEW_PKL" "$HTML_OUTPUT" --pickle-load

if [ $? -eq 0 ]; then
  echo "✓ SUCCESS"
  echo ""
  echo "Generated directory:"
  echo "  - $HTML_OUTPUT/"
  echo ""
  echo "To view the result, open: $HTML_OUTPUT/index.html"
else
  echo "✗ FAILED"
  exit 1
fi
