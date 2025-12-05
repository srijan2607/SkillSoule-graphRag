# Security

## Input Validation

- **Validation Library:** Pydantic 2.x (request/response models)
- **Validation Location:** API boundary (FastAPI route handlers, before service layer)
- **Required Rules:**
  - All external inputs (query text, CSV files, skill IDs) MUST be validated
  - Validation at API boundary before processing (never trust client input)
  - Whitelist approach preferred over blacklist (e.g., allowed characters for skill names)

**Example (Query Validation):**
```python
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)  # Prevent empty or excessive queries
    session_id: Optional[UUID] = None
    include_metrics: bool = True

    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace")
        # Basic XSS prevention (backend generates responses, but defense in depth)
        if any(char in v for char in ['<', '>', '&']):
            raise ValueError("Query contains invalid characters")
        return v
```

## Authentication & Authorization

- **Auth Method:** JWT (JSON Web Tokens) with HS256 signing
- **Session Management:** Stateless tokens (30-day expiration), refresh token rotation not implemented in MVP
- **Required Patterns:**
  - All protected endpoints MUST verify JWT token via `@requires_auth` decorator
  - Password storage: bcrypt hashing (cost factor 12)
  - Token payload: `{user_id, email, exp}` (no sensitive data in token)

**Example (JWT Middleware):**
```python
from fastapi import Depends, HTTPException, Header
import jwt

def verify_jwt_token(authorization: str = Header(...)) -> str:
    """Extract and verify JWT token from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")

    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
```

## Secrets Management

- **Development:** `.env` file (gitignored, example in `.env.example`)
- **Production:** Environment variables injected via hosting platform (e.g., Vercel, Railway)
- **Code Requirements:**
  - NEVER hardcode secrets (API keys, database passwords, JWT secret)
  - Access via `os.getenv()` or Pydantic `BaseSettings` configuration
  - No secrets in logs or error messages (mask sensitive values)

**Example (Configuration):**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_password: str
    openrouter_api_key: str
    jwt_secret: str

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()  # Loads from .env or environment variables
```

## API Security

- **Rate Limiting:** 10 requests/min per user (sliding window, in-memory cache for MVP)
- **CORS Policy:**
  - Development: Allow `http://localhost:5173` (React dev server)
  - Production: Allow `https://career-intelligence.example.com` (whitelist only)
- **Security Headers:**
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Content-Security-Policy: default-src 'self'`
- **HTTPS Enforcement:** Required in production (redirect HTTP → HTTPS)

**Example (FastAPI CORS):**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Dev only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Data Protection

- **Encryption at Rest:**
  - Neo4j Aura: TLS encryption for data in transit + cloud provider encryption at rest
  - PostgreSQL (Supabase): TLS + encryption at rest (default)
- **Encryption in Transit:**
  - TLS 1.2+ for all external API calls (OpenRouter, HuggingFace)
  - Neo4j: `neo4j+s://` (secure Bolt protocol)
- **PII Handling:**
  - Minimal PII (email, full_name)
  - No collection of résumés, phone numbers, addresses
  - User can request data deletion (GDPR compliance for future)
- **Logging Restrictions:**
  - NEVER log: password_hash, JWT tokens, API keys
  - Mask email in logs (e.g., `u***@example.com`)
  - Log `user_id` only for debugging, not personal details

## Dependency Security

- **Scanning Tool:** `pip-audit` (Python), `npm audit` (JavaScript)
- **Update Policy:** Monthly dependency updates, critical security patches within 48 hours
- **Approval Process:**
  - New dependencies require justification (why needed, alternatives considered)
  - Security scan before adding to `requirements.txt` / `package.json`
  - Pin versions (no `^` or `~` ranges in production)

## Security Testing

- **SAST Tool:** `bandit` (Python static analysis for security issues)
- **DAST Tool:** Manual penetration testing for MVP (future: OWASP ZAP automation)
- **Penetration Testing:** Pre-production manual testing (SQL injection, XSS, auth bypass attempts)

**Security Checklist (Pre-Deployment):**
- [ ] All secrets removed from code (grep for API keys, passwords)
- [ ] JWT secret rotation plan in place
- [ ] Rate limiting active on all public endpoints
- [ ] CORS configured for production domain only
- [ ] Security headers verified (CSP, X-Frame-Options)
- [ ] Dependency scan clean (no high/critical vulnerabilities)

---
