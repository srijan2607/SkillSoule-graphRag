#!/bin/bash

# Try creating a unique test user
TIMESTAMP=$(date +%s)
EMAIL="testuser${TIMESTAMP}@example.com"
PASSWORD="SecurePassword123!"

echo "=== Registering new test user: $EMAIL ==="
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\"
  }")

echo "$REGISTER_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$REGISTER_RESPONSE"

# Login immediately
echo -e "\n=== Logging in with new user ==="
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\"
  }")

echo "$LOGIN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$LOGIN_RESPONSE"

# Extract JWT token
JWT_TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -n "$JWT_TOKEN" ]; then
  echo -e "\n✅ JWT Token obtained successfully!"
  echo "Token (first 50 chars): ${JWT_TOKEN:0:50}..."
  echo "$JWT_TOKEN" > /tmp/jwt_token.txt
  echo "Full token saved to /tmp/jwt_token.txt"
else
  echo -e "\n❌ Failed to get JWT token"
fi
