#!/bin/bash
set -e
echo "=== TEST 4: FastAPI main.py - OPTIONS handler registration order ==="

cd backend

# Check that @app.options is defined AFTER all include_router calls
OPTIONS_LINE=$(grep -n "app.options" app/main.py | head -1 | cut -d: -f1)
LAST_ROUTER_LINE=$(grep -n "include_router" app/main.py | tail -1 | cut -d: -f1)

echo "Last include_router at line: $LAST_ROUTER_LINE"
echo "@app.options handler at line: $OPTIONS_LINE"

if [ "$OPTIONS_LINE" -gt "$LAST_ROUTER_LINE" ]; then
  echo "✅ PASS: @app.options is registered AFTER all routers (line $OPTIONS_LINE > $LAST_ROUTER_LINE)"
else
  echo "❌ FAIL: @app.options is registered BEFORE routers — CORS catch-all will shadow router paths"
  exit 1
fi

echo ""
echo "=== TEST 5: FastAPI main.py - CORSMiddleware explicit method list ==="
if grep -q '"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"' app/main.py; then
  echo "✅ PASS: CORSMiddleware uses explicit method list (not wildcard '*')"
else
  echo "❌ FAIL: CORSMiddleware still uses wildcard allow_methods"
  exit 1
fi

echo ""
echo "=== TEST 6: API Gateway Terraform - passthrough_behavior set ==="
cd ../infra
if grep -q 'passthrough_behavior = "WHEN_NO_MATCH"' modules/api_gateway/main.tf; then
  COUNT=$(grep -c 'passthrough_behavior = "WHEN_NO_MATCH"' modules/api_gateway/main.tf)
  echo "✅ PASS: passthrough_behavior found ($COUNT occurrences — proxy + root OPTIONS)"
else
  echo "❌ FAIL: passthrough_behavior NOT set"
  exit 1
fi

echo ""
echo "=== TEST 7: API Gateway Terraform - root OPTIONS resources exist ==="
if grep -q '"options_root"' modules/api_gateway/main.tf; then
  echo "✅ PASS: Root OPTIONS MOCK resources found in api_gateway/main.tf"
else
  echo "❌ FAIL: Root OPTIONS resources missing"
  exit 1
fi

echo ""
echo "=== TEST 8: Terraform deployment trigger includes root OPTIONS ==="
if grep -q 'options_root_integration_response.id' modules/api_gateway/main.tf; then
  echo "✅ PASS: Deployment redeployment trigger includes root OPTIONS integration response"
else
  echo "❌ FAIL: Deployment trigger missing root OPTIONS"
  exit 1
fi

echo ""
echo "========================================"
echo "✅ ALL TESTS PASSED — safe to merge and deploy"
echo "========================================"
