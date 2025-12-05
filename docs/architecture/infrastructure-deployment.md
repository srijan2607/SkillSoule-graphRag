# Infrastructure & Deployment

This section covers the **MVP deployment strategy** - keeping things simple and focused on getting the system running quickly for development and testing.

---

## 7.1 Development Environment Setup

### **Prerequisites**

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Poetry | 1.7+ | Dependency management (optional) |
| Node.js | 18+ | Prisma CLI |
| Docker | 24+ | Containerization |
| Docker Compose | 2.20+ | Multi-container orchestration |
| Git | 2.40+ | Version control |

---

### **Local Setup Steps**

**1. Clone Repository**
```bash
git clone https://github.com/your-org/graph-rag-backend.git
cd graph-rag-backend
```

**2. Create Virtual Environment**
```bash
# Using venv
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# OR using Poetry
poetry install
poetry shell
```

**3. Install Dependencies**
```bash
# Using pip
pip install -r requirements.txt

# OR using Poetry
poetry install
```

**4. Setup Environment Variables**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

**5. Start Databases with Docker Compose**
```bash
docker-compose up -d postgres neo4j
```

**6. Run Database Migrations**
```bash
# Generate Prisma client
prisma generate

# Run migrations
prisma migrate dev --name init
```

**7. Setup Neo4j Indexes**
```bash
python scripts/setup_indexes.py
```

**8. (Optional) Seed Sample Data**
```bash
python scripts/seed_neo4j.py
```

**9. Start Development Server**
```bash
# With uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# OR with Python
python -m app.main
```

**10. Verify Setup**
```bash
# Health check
curl http://localhost:8000/health

# API docs (Swagger UI)
open http://localhost:8000/docs
```

---

## 7.2 Docker Deployment

### **Single Container Deployment**

**Build Image**
```bash
docker build -t graph-rag-backend:latest .
```

**Run Container**
```bash
docker run -d \
  --name graph-rag-api \
  -p 8000:8000 \
  --env-file .env \
  graph-rag-backend:latest
```

---

### **Multi-Container Deployment with Docker Compose**

**Full Stack (Backend + PostgreSQL + Neo4j)**

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Stop and remove volumes (data will be lost)
docker-compose down -v
```

**Service URLs**:
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- Neo4j Browser: `http://localhost:7474`
- Neo4j Bolt: `bolt://localhost:7687`

---

**Run tests locally**:
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=term
```

**Optional: GitHub Actions for basic CI**:

Create `.github/workflows/test.yml`:
```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pytest pytest-asyncio
      - run: pytest tests/ -v
```

---

## 7.4 Basic Monitoring (MVP)

### **Health Check Endpoint**

**Add to `app/main.py`**:
```python
@app.get("/health")
async def health_check():
    """Simple health check for MVP."""
    return {
        "status": "healthy",
        "service": "graph-rag-api",
        "version": "1.0.0"
    }
```

Test it: `curl http://localhost:8000/health`

---

### **Simple Logging**

**`app/utils/logger.py`**:
```python
import logging
import sys

def setup_logger():
    """Basic console logging."""
    logger = logging.getLogger("graph-rag-api")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

logger = setup_logger()
```

**Usage**:
```python
from app.utils.logger import logger

logger.info("CSV ingestion started")
logger.error(f"Database connection failed: {error}")
```

---

## 7.5 MVP Deployment Notes

**For MVP, keep it simple**:

1. **Local Development**: Use `docker-compose up` - that's it
2. **No CI/CD needed yet**: Manual testing is fine for MVP
3. **No monitoring stack**: Basic health check + console logs are enough
4. **No backup strategy**: Focus on building features first
5. **No scaling concerns**: Single instance is fine for MVP
6. **No production hosting yet**: Run locally or use free tiers (Railway, Render) when ready

**When to add production infrastructure**:
- After MVP validation with real users
- When you have consistent traffic
- When downtime becomes costly
- When you need to scale beyond single instance

---

This completes the **Infrastructure & Deployment** section with MVP-focused, simple setup.

---
