#!/bin/bash
# Quick LangSmith API health check using curl

API_KEY="${LANGSMITH_API_KEY:-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}"
PROJECT="ai-troubleshooter-v10"

echo "=========================================="
echo "🔍 LangSmith API Health Check"
echo "=========================================="
echo ""

# Test 1: Check API connectivity
echo "Test 1: API Connectivity"
response=$(curl -s -w "\n%{http_code}" \
  -H "x-api-key: $API_KEY" \
  "https://api.smith.langchain.com/info")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo "   ✅ API is reachable (HTTP $http_code)"
else
    echo "   ❌ API returned HTTP $http_code"
    echo "   Response: $body"
fi
echo ""

# Test 2: List recent runs
echo "Test 2: Fetching Recent Traces"
runs_response=$(curl -s -w "\n%{http_code}" \
  -H "x-api-key: $API_KEY" \
  "https://api.smith.langchain.com/runs?limit=5")

runs_http_code=$(echo "$runs_response" | tail -n1)
runs_body=$(echo "$runs_response" | head -n-1)

if [ "$runs_http_code" = "200" ]; then
    echo "   ✅ Successfully fetched traces (HTTP $runs_http_code)"
    echo "   Response preview:"
    echo "$runs_body" | head -c 500
    echo ""
    echo "   ..."
else
    echo "   ❌ Failed to fetch traces (HTTP $runs_http_code)"
    echo "   Response: $runs_body"
fi
echo ""

echo "🔗 Dashboard URL:"
echo "   https://smith.langchain.com/o/default/projects/p/$PROJECT"
echo ""
