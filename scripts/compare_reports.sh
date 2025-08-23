#!/bin/bash

# Simple comparison script that uses existing .env file
# Usage: ./compare_reports.sh <inspection_id>

INSPECTION_ID=${1:-"759c864b-6ced-4983-955a-93287857a0a5"}

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"

# Load environment variables from api/.env using Python (handles complex JSON properly)
echo "✅ Loading environment from api/.env"
export $(python3 -c "
import os
import json

env_file = '$PROJECT_ROOT/api/.env'
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Only export simple key=value pairs, skip the complex JSON
                if '=' in line and not '{' in line:
                    key = line.split('=')[0]
                    if key not in ['FIREBASE_SERVICE_ACCOUNT_JSON']:
                        print(line)
" | xargs)

# Set the Firebase JSON separately (it's complex and needs special handling)
export FIREBASE_SERVICE_ACCOUNT_JSON=$(python3 -c "
import os
env_file = '$PROJECT_ROOT/api/.env'
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        content = f.read()
        # Find the FIREBASE_SERVICE_ACCOUNT_JSON line
        for line in content.split('\n'):
            if line.startswith('FIREBASE_SERVICE_ACCOUNT_JSON='):
                # Extract everything after the = sign
                json_str = line[len('FIREBASE_SERVICE_ACCOUNT_JSON='):]
                print(json_str)
                break
")

# Run the comparison from the project root
cd "$PROJECT_ROOT"
echo "🚀 Running report comparison for inspection: $INSPECTION_ID"
python3 scripts/compare_with_pdf_fixed.py "$INSPECTION_ID"

# Show results
echo ""
echo "📁 Results saved in: pdf_comparison_*/"
echo "📄 Open PDFs with: open pdf_comparison_*/*.pdf"