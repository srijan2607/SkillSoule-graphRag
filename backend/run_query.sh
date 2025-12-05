#!/bin/bash

# Extract token from login response (it's under "token" key)
echo "=== Getting JWT Token ==="
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser1761412084@example.com",
    "password": "SecurePassword123!"
  }')

JWT_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

if [ -z "$JWT_TOKEN" ]; then
  echo "❌ Failed to get JWT token"
  echo "Response: $LOGIN_RESPONSE"
  exit 1
fi

echo "✅ JWT Token obtained: ${JWT_TOKEN:0:50}..."

# Execute the query
echo -e "\n=== Executing Query: 'What skills do I need for data science?' ==="
QUERY_RESPONSE=$(curl -s -X POST http://localhost:8000/query/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "query": "What skills do I need for data science?",
    "session_id": "test-session-'$(date +%s)'"
  }')

echo "$QUERY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$QUERY_RESPONSE"

# Save to file for inspection
echo "$QUERY_RESPONSE" > /tmp/query_response.json
echo -e "\n✅ Full response saved to /tmp/query_response.json"
