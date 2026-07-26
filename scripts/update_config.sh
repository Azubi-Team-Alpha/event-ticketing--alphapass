#!/usr/bin/env bash
# ==============================================================================
# AlphaPass Dynamic API URL Auto-Injector & S3 Synchronizer
# Automatically detects the active AWS API Gateway endpoint (or Terraform output)
# and injects it into frontend/js/config.js, then syncs to S3.
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔍 Resolving active API Gateway endpoint..."

API_URL=$(python3 -c "
import subprocess, json, urllib.request

# 1. Try reading Terraform output
try:
    res = subprocess.check_output(['terraform', 'output', '-raw', 'api_endpoint'], cwd='$PROJECT_ROOT/infra', stderr=subprocess.DEVNULL).decode().strip()
    if res and res.startswith('http'):
        print(res)
        exit(0)
except Exception:
    pass

# 2. Fallback: Use known working API ID
try:
    # Use the verified working API Gateway instance
    api_id = '5pk6j1j5bj'
    url = f'https://{api_id}.execute-api.us-east-1.amazonaws.com/dev'
    try:
        req = urllib.request.urlopen(f'{url}/health', timeout=3)
        data = req.read().decode()
        if 'status' in data and 'ok' in data:
            print(url)
            exit(0)
    except Exception:
        pass
except Exception:
    pass

print('')
")

if [ -z "$API_URL" ]; then
    echo "❌ Error: Could not detect active API Gateway endpoint"
    echo "   Please ensure:"
    echo "   1. Terraform output is available: cd infra && terraform output -raw api_endpoint"
    echo "   2. Or API Gateway is deployed and accessible via AWS CLI"
    exit 1
fi

echo "✅ Active API Endpoint: $API_URL"

CONFIG_FILE="$PROJECT_ROOT/frontend/js/config.js"
echo "📝 Updating $CONFIG_FILE..."

cat <<EOF > "$CONFIG_FILE"
/**
 * AlphaPass Global Frontend Configuration
 * Dynamically generated on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
 * Active API Endpoint: $API_URL
 */
if (typeof window.ALPHAPASS_API_URL === 'undefined' || !window.ALPHAPASS_API_URL) {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        window.ALPHAPASS_API_URL = 'http://127.0.0.1:8000';
    } else {
        window.ALPHAPASS_API_URL = '$API_URL';
    }
}
EOF

echo "🚀 Syncing frontend config to S3 (s3://alphapass.alphateam.live)..."
aws s3 cp "$CONFIG_FILE" s3://alphapass.alphateam.live/js/config.js --cache-control "max-age=0,no-cache"

echo "🎉 Success! Frontend API URL updated to: $API_URL"
