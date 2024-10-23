#!/bin/bash

# Constants
MAX_LINES=500
MAX_CHANGE_LINES=200
PYTHON_EXEC=python3
CODE_DIRECTORY=airflowproject

# Functions
echo_error() {
  local RED='\033[0;31m'
  local NC='\033[0m' # No Color
  echo -e "${RED}$1${NC}"
}

echo_separator() {
  echo "================================"
}

# Start of script
echo_separator
echo "Running checks before commit"
echo ""
echo_separator
echo "Running code style checking with Flake8"
$PYTHON_EXEC -m flake8 ./$CODE_DIRECTORY
echo ""
echo_separator
echo "Running type checking with MyPy"
$PYTHON_EXEC -m mypy ./$CODE_DIRECTORY
echo ""
echo_separator
echo "Running docstrings checking Pylint"
$PYTHON_EXEC -m pylint ./$CODE_DIRECTORY
echo ""

# File line count check
check_file_line_count() {
  for file in $(git ls-files); do
    if [[ "$file" != *".pylintrc"* ]]; then
      line_count=$(wc -l < "$file")
      if [ "$line_count" -gt "$MAX_LINES" ]; then
        echo_error "File $file has $line_count lines, which exceeds the threshold of $MAX_LINES lines."
        exit 1  # Exit if any file exceeds the line limit
      fi
    fi
  done
}

# Change line count check
check_change_line_count() {
  local changes=$(git diff main --numstat | awk '{added+=$1; deleted+=$2} END {print added+deleted}')
  if [ "$changes" -gt "$MAX_CHANGE_LINES" ]; then
    echo_error "Too many changes: $changes lines. Maximum allowed: $MAX_CHANGE_LINES lines."
    exit 1  # Exit if changes exceed the limit
  else
    echo "Number of changed lines: $changes"
  fi
  echo_separator
  echo "Change line check completed"
}

# Execution
check_file_line_count
echo_separator
echo "Line count check completed"
echo ""

IS_CHECK_CHANGE_LINE=false
while [[ "$#" -gt 0 ]]; do
  case $1 in
    check_change_line) IS_CHECK_CHANGE_LINE=true ;;
    *) echo "Unknown parameter passed: $1"; exit 1 ;;
  esac
  shift
done

[ "$IS_CHECK_CHANGE_LINE" = true ] && check_change_line_count