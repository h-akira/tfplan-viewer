#!/bin/bash

# Phase 1 test: Data Extraction
# Extracts resource data from plan.json and schema.json
#
# Usage: ./phase1_test.sh <test_dir>
# Example: ./phase1_test.sh test001

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

PLAN_JSON="$TARGET_DIR/plan.json"
SCHEMA_DIR="$TARGET_DIR/schema"
SCHEMA_JSON="$TARGET_DIR/schema.json"
EXTRACTED_PKL="$TARGET_DIR/extracted.pkl"
EXTRACTED_JSON="$TARGET_DIR/extracted.json"

echo "=========================================="
echo "Phase 1: Data Extraction ($TEST_DIR)"
echo "=========================================="

# Check input files
if [ ! -f "$PLAN_JSON" ]; then
  echo "ERROR: plan.json not found in $TEST_DIR"
  exit 1
fi

# Use schema directory if available, fall back to schema.json
if [ -d "$SCHEMA_DIR" ]; then
  SCHEMA_SRC="$SCHEMA_DIR"
elif [ -f "$SCHEMA_JSON" ]; then
  SCHEMA_SRC="$SCHEMA_JSON"
else
  echo "ERROR: Neither schema/ directory nor schema.json found in $TEST_DIR"
  exit 1
fi

echo "Input:  $PLAN_JSON, $SCHEMA_SRC"
echo "Output: $EXTRACTED_PKL, $EXTRACTED_JSON"

python3 "$PROJECT_ROOT/lib/data_extraction.py" "$PLAN_JSON" "$SCHEMA_SRC" \
  --pickle-dump "$EXTRACTED_PKL" \
  --output "$EXTRACTED_JSON"

if [ $? -eq 0 ]; then
  echo "✓ SUCCESS"
  echo ""
  echo "Generated files:"
  echo "  - $EXTRACTED_PKL"
  echo "  - $EXTRACTED_JSON"
else
  echo "✗ FAILED"
  exit 1
fi
