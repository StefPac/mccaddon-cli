#!/bin/bash
# Validates all JSON files in a directory

if [ -z "$1" ]; then
    echo "Usage: ./validate-json.sh <directory>"
    exit 1
fi

ERROR=0
find "$1" -name "*.json" -type f | while read json_file; do
    if ! jq empty "$json_file" 2>/dev/null; then
        echo "✗ Invalid JSON: $json_file"
        ERROR=1
    fi
done

if [ $ERROR -eq 0 ]; then
    echo "✓ All JSON files valid"
fi

exit $ERROR
