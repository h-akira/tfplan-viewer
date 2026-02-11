#!/bin/bash

# Run all tests (test001, test002, test003, test004)
# This script executes all phases for each test directory

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Running all tests"
echo "=========================================="
echo ""

# Find all test directories
for test_dir in "$SCRIPT_DIR"/test[0-9][0-9][0-9]; do
  if [ -d "$test_dir" ]; then
    TEST_NAME=$(basename "$test_dir")

    echo ""
    echo "=========================================="
    echo "Running: $TEST_NAME"
    echo "=========================================="
    bash "$SCRIPT_DIR/run_all_phases.sh" "$TEST_NAME"
    echo ""
    echo "✓ $TEST_NAME completed"
  fi
done

echo ""
echo "=========================================="
echo "All tests completed successfully"
echo "=========================================="
