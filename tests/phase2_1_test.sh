#!/bin/bash

# Phase 2-1 test: Special Resource Processing
# Merges dependent resources into parent resources
#
# Usage: ./phase2_1_test.sh <test_dir>
# Example: ./phase2_1_test.sh test001

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

EXTRACTED_PKL="$TARGET_DIR/extracted.pkl"
SPECIAL_PKL="$TARGET_DIR/special.pkl"
SPECIAL_JSON="$TARGET_DIR/special.json"

echo "=========================================="
echo "Phase 2-1: Special Resource Processing ($TEST_DIR)"
echo "=========================================="

# Check input files
if [ ! -f "$EXTRACTED_PKL" ]; then
  echo "ERROR: extracted.pkl not found in $TEST_DIR"
  echo "Run phase1_test.sh first"
  exit 1
fi

echo "Input:  $EXTRACTED_PKL"
echo "Output: $SPECIAL_PKL, $SPECIAL_JSON"

python3 "$PROJECT_ROOT/lib/special_processor.py" "$EXTRACTED_PKL" --pickle-load \
  --pickle-dump "$SPECIAL_PKL" \
  --output "$SPECIAL_JSON"

if [ $? -eq 0 ]; then
  echo "✓ SUCCESS"
  echo ""
  echo "Generated files:"
  echo "  - $SPECIAL_PKL"
  echo "  - $SPECIAL_JSON"
else
  echo "✗ FAILED"
  exit 1
fi
