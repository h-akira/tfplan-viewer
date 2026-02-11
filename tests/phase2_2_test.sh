#!/bin/bash

# Phase 2-2 test: Reference Resolution
# Resolves resource references to actual values
#
# Usage: ./phase2_2_test.sh <test_dir>
# Example: ./phase2_2_test.sh test001

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

SPECIAL_PKL="$TARGET_DIR/special.pkl"
REFERENCE_PKL="$TARGET_DIR/reference.pkl"
REFERENCE_JSON="$TARGET_DIR/reference.json"

echo "=========================================="
echo "Phase 2-2: Reference Resolution ($TEST_DIR)"
echo "=========================================="

# Check input files
if [ ! -f "$SPECIAL_PKL" ]; then
  echo "ERROR: special.pkl not found in $TEST_DIR"
  echo "Run phase2_1_test.sh first"
  exit 1
fi

echo "Input:  $SPECIAL_PKL"
echo "Output: $REFERENCE_PKL, $REFERENCE_JSON"

python3 "$PROJECT_ROOT/lib/reference_resolver.py" "$SPECIAL_PKL" --pickle-load \
  --pickle-dump "$REFERENCE_PKL" \
  --output "$REFERENCE_JSON"

if [ $? -eq 0 ]; then
  echo "✓ SUCCESS"
  echo ""
  echo "Generated files:"
  echo "  - $REFERENCE_PKL"
  echo "  - $REFERENCE_JSON"
else
  echo "✗ FAILED"
  exit 1
fi
