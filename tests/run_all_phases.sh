#!/bin/bash

# Execute all phases sequentially for a test directory
# This script runs all test phases from Phase 1 to Phase 3
#
# Usage: ./run_all_phases.sh <test_dir>
# Example: ./run_all_phases.sh test001

set -e  # Exit on error

if [ $# -ne 1 ]; then
  echo "Usage: $0 <test_dir>"
  echo "Example: $0 test001"
  exit 1
fi

TEST_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -d "$SCRIPT_DIR/$TEST_DIR" ]; then
  echo "ERROR: Test directory not found: $SCRIPT_DIR/$TEST_DIR"
  exit 1
fi

echo "=========================================="
echo "Executing all phases for $TEST_DIR"
echo "=========================================="
echo ""

# Phase 1: Data Extraction
bash "$SCRIPT_DIR/phase1_test.sh" "$TEST_DIR"
echo ""

# Phase 2-1: Special Resource Processing
bash "$SCRIPT_DIR/phase2_1_test.sh" "$TEST_DIR"
echo ""

# Phase 2-2: Reference Resolution
bash "$SCRIPT_DIR/phase2_2_test.sh" "$TEST_DIR"
echo ""

# Phase 2-3: View Conversion
bash "$SCRIPT_DIR/phase2_3_test.sh" "$TEST_DIR"
echo ""

# Phase 3: HTML Generation
bash "$SCRIPT_DIR/phase3_test.sh" "$TEST_DIR"
echo ""

echo "=========================================="
echo "All phases completed successfully for $TEST_DIR"
echo "=========================================="
