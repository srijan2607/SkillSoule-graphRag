#!/bin/bash

# Register test user
echo "=== Registering test user ==="
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123456"
  }')

echo "$REGISTER_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$REGISTER_RESPONSE"

# Login to get JWT
echo -e "\n=== Logging in ==="
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test123456"
  }')

echo "$LOGIN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LOGIN_RESPONSE"

# Extract JWT token
JWT_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -n "$JWT_TOKEN" ]; then
  echo -e "\n✅ JWT Token obtained: ${JWT_TOKEN:0:50}..."
  echo "$JWT_TOKEN" > /tmp/jwt_token.txt
else
  echo -e "\n❌ Failed to get JWT token"
fi
