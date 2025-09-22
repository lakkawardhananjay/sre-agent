#!/bin/bash

# Local testing script for SRE Agent
# This script runs comprehensive local tests

set -e

echo "🧪 Running SRE Agent tests"

# Start the application in background
echo "🚀 Starting SRE Agent..."
PYTHONPATH=/home/runner/work/sre-agent/sre-agent/src python -m uvicorn sre_agent.main:app --host 0.0.0.0 --port 8000 &
APP_PID=$!

# Wait for app to start
echo "⏳ Waiting for application to start..."
sleep 5

# Test endpoints
echo "🔍 Testing endpoints..."

# Test root endpoint
echo "Testing root endpoint..."
curl -s http://localhost:8000/ | jq . > /dev/null || { echo "❌ Root endpoint failed"; kill $APP_PID; exit 1; }
echo "✅ Root endpoint OK"

# Test health endpoint
echo "Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
echo $HEALTH_RESPONSE | jq . > /dev/null || { echo "❌ Health endpoint failed"; kill $APP_PID; exit 1; }
echo "✅ Health endpoint OK"

# Test metrics endpoint
echo "Testing metrics endpoint..."
curl -s http://localhost:8000/metrics | grep "# HELP" > /dev/null || { echo "❌ Metrics endpoint failed"; kill $APP_PID; exit 1; }
echo "✅ Metrics endpoint OK"

# Test docs endpoint
echo "Testing docs endpoint..."
curl -s http://localhost:8000/docs | grep -i "swagger\|fastapi\|openapi" > /dev/null || { echo "❌ Docs endpoint failed"; kill $APP_PID; exit 1; }
echo "✅ Docs endpoint OK"

# Check if Kubernetes integration is working (expected to fail in CI)
echo "Testing Kubernetes integration..."
K8S_STATUS=$(echo $HEALTH_RESPONSE | jq -r '.checks.kubernetes')
if [ "$K8S_STATUS" = "false" ]; then
    echo "⚠️  Kubernetes integration disabled (expected in CI environment)"
else
    echo "✅ Kubernetes integration OK"
fi

# Check Gemini integration status
echo "Testing Gemini integration..."
GEMINI_STATUS=$(echo $HEALTH_RESPONSE | jq -r '.checks.gemini')
if [ "$GEMINI_STATUS" = "false" ]; then
    echo "⚠️  Gemini integration disabled (API key not configured)"
else
    echo "✅ Gemini integration OK"
fi

# Stop the application
echo "🛑 Stopping application..."
kill $APP_PID
wait $APP_PID 2>/dev/null

echo ""
echo "🎉 All tests passed!"
echo ""
echo "Test Summary:"
echo "✅ Root endpoint functional"
echo "✅ Health endpoint functional"  
echo "✅ Metrics endpoint functional"
echo "✅ Documentation accessible"
echo "⚠️  Kubernetes integration (requires cluster access)"
echo "⚠️  Gemini integration (requires API key)"
echo ""
echo "To test with full functionality:"
echo "1. Configure Kubernetes access (kubectl config)"
echo "2. Set GEMINI_API_KEY in .env file"
echo "3. Re-run this script"