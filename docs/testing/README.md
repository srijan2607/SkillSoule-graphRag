# E2E Testing Documentation

This directory contains comprehensive End-to-End (E2E) testing documentation and automated tests for the Graph RAG MVP application.

## Contents

- **e2e-test-checklist.md** - Manual testing checklist for all test scenarios
- **Automated E2E Tests** - Located in `frontend/src/test/e2e/`
- **Test Data** - Sample CSV files in `backend/tests/fixtures/`

---

## Test Scenarios Overview

### Scenario 1: User Registration and Login Flow
**Location**: `frontend/src/test/e2e/auth-flow.spec.js`

Tests the complete authentication workflow:
- User registration with validation
- Successful login and redirect to chat
- Invalid login error handling
- Logout and re-login functionality

**Key Features**:
- Unique test user generation per run
- Form validation testing
- Error message verification
- Session persistence testing

---

### Scenario 2: CSV Upload Flow
**Location**: Existing `frontend/src/test/e2e/upload-workflow.spec.js`

Tests CSV file upload and ingestion:
- Skills CSV upload and validation
- Jobs CSV upload and validation
- Preview functionality
- Ingestion progress tracking
- Success message verification

**Test Data**:
- `backend/tests/fixtures/skills_sample.csv` (20 records)
- `backend/tests/fixtures/jobs_sample.csv` (20 records)

---

### Scenario 3: Query Flow with Sources
**Location**: `frontend/src/test/e2e/query-flow.spec.js`

Tests the complete RAG query workflow:
- Query submission and processing
- Loading indicator display
- Response generation (< 10 seconds)
- Sources section display and expansion
- Response relevance verification
- Multiple query handling

**Performance Metrics**:
- Response time tracking
- Relevance checking
- Source display validation

---

### Scenario 4: Multi-Turn Conversation
**Location**: `frontend/src/test/e2e/multi-turn-conversation.spec.js`

Tests conversation context and memory:
- Multiple query handling
- Context maintenance across turns
- Follow-up question processing
- Conversation history display
- Clear/new chat functionality

**MVP Note**: Basic session memory is acceptable. Full conversation history passed to LLM is not required for MVP.

---

### Scenario 5: Error Handling
**Location**: `frontend/src/test/e2e/error-handling.spec.js`

Tests comprehensive error scenarios:
- **5A: Invalid Login** (in `auth-flow.spec.js`)
  - Wrong password handling
  - User-friendly error messages
  - No redirect on failure

- **5B: Empty Query Validation**
  - Empty input prevention
  - Whitespace-only query rejection
  - Input validation display

- **5C: API Failure Handling**
  - Network error recovery
  - Timeout handling
  - User-friendly error messages
  - No raw stack traces displayed
  - App recovery after API restoration

---

## Running the Tests

### Prerequisites
```bash
# Ensure backend and frontend dependencies are installed
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
```

### Manual Testing
```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# Start frontend (in separate terminal)
cd frontend
npm run dev

# Follow the checklist in docs/testing/e2e-test-checklist.md
```

### Automated E2E Tests
```bash
# Run all E2E tests
cd frontend
npm run test:e2e

# Run tests with UI mode
npm run test:e2e:ui

# Run tests in debug mode
npm run test:e2e:debug

# Run specific test file
npx playwright test src/test/e2e/auth-flow.spec.js

# Run tests in specific browser
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

### Test Reports
```bash
# View HTML test report
npx playwright show-report

# Reports are generated in: playwright-report/
```

---

## Test Data Management

### Sample CSV Files
Location: `backend/tests/fixtures/`

**skills_sample.csv**:
- 20 realistic skill records
- Covers various categories (Programming, AI/ML, DevOps, Soft Skills)
- Includes embeddings-ready data
- Tests vector search functionality

**jobs_sample.csv**:
- 20 realistic job postings
- Major tech companies (Google, Microsoft, Meta, etc.)
- Salary ranges and locations
- Skills mapped to jobs
- Tests graph traversal

### Using Test Data
```bash
# Skills CSV is automatically loaded in upload tests
# Jobs CSV is automatically loaded in upload tests

# Manual upload for testing:
# 1. Start application
# 2. Navigate to /upload
# 3. Upload backend/tests/fixtures/skills_sample.csv
# 4. Upload backend/tests/fixtures/jobs_sample.csv
```

---

## Test Environment Setup

### Required Services
1. **PostgreSQL** - User authentication and job tracking
   - Connection: `localhost:5432`
   - Database: `graph_rag_db` (or configured name)

2. **Neo4j** - Graph database for skills/jobs
   - Connection: `localhost:7687`
   - Browser: `http://localhost:7474`

3. **Backend API** - FastAPI application
   - URL: `http://localhost:8000`
   - Health check: `http://localhost:8000/health`

4. **Frontend** - React application
   - URL: `http://localhost:5173`
   - Vite dev server

### Environment Variables
Ensure `.env` files are properly configured:

**Backend `.env`**:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/graph_rag_db
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
JWT_SECRET=your_secret_key
OPENROUTER_API_KEY=your_openrouter_key
```

**Frontend `.env`**:
```bash
VITE_API_URL=http://localhost:8000
```

---

## Test Scenarios Checklist

Use `docs/testing/e2e-test-checklist.md` for manual testing with these sections:

- [x] Test Environment Setup
- [ ] Scenario 1: User Registration Flow
- [ ] Scenario 2A: Skills CSV Upload
- [ ] Scenario 2B: Jobs CSV Upload
- [ ] Scenario 3: Query Flow
- [ ] Scenario 4: Multi-Turn Conversation
- [ ] Scenario 5A: Invalid Login
- [ ] Scenario 5B: Empty Query
- [ ] Scenario 5C: API Failure
- [ ] Overall Test Results
- [ ] MVP Approval

---

## CI/CD Integration

### GitHub Actions (Future)
```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: Install Playwright browsers
        run: cd frontend && npx playwright install --with-deps
      - name: Run E2E tests
        run: cd frontend && npm run test:e2e
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

---

## Debugging Tests

### Using Playwright Inspector
```bash
# Debug specific test
npx playwright test src/test/e2e/auth-flow.spec.js --debug

# Debug from specific line
npx playwright test src/test/e2e/query-flow.spec.js:25 --debug
```

### Using Trace Viewer
```bash
# Run with trace
npx playwright test --trace on

# View trace
npx playwright show-trace trace.zip
```

### Screenshots and Videos
Configured in `playwright.config.js`:
- Screenshots: Captured on failure
- Videos: Captured on first retry
- Traces: Enabled on first retry

---

## Common Issues and Solutions

### Issue: Tests fail with "Timeout waiting for element"
**Solution**: Increase timeout or check if element selector is correct
```javascript
await expect(element).toBeVisible({ timeout: 10000 })
```

### Issue: API calls fail during tests
**Solution**: Ensure backend is running and API_URL is correct
```bash
# Check backend health
curl http://localhost:8000/health
```

### Issue: Database state affects tests
**Solution**: Clear test data between runs
```bash
# Backend has fixtures for clean database state
# Tests use unique user emails per run
```

### Issue: Tests pass locally but fail in CI
**Solution**: Check environment variables and service availability
```bash
# Ensure all services start in CI
# Use docker-compose for consistent environment
```

---

## Test Coverage Goals

### Current Coverage (Story 5.6)
- ✅ Authentication flows (registration, login, logout)
- ✅ CSV upload workflows
- ✅ Query processing and response generation
- ✅ Multi-turn conversations
- ✅ Error handling (validation, network, API failures)

### Future Enhancements
- [ ] Performance testing under load
- [ ] Accessibility testing (WCAG compliance)
- [ ] Cross-browser compatibility testing
- [ ] Mobile responsiveness testing
- [ ] Security testing (XSS, CSRF, SQL injection)

---

## Contributing to Tests

### Adding New Tests
1. Create test file in `frontend/src/test/e2e/`
2. Follow existing patterns and naming conventions
3. Use descriptive test names: `'Scenario X: Description'`
4. Add assertions for both positive and negative cases
5. Document test data requirements
6. Update this README with new scenarios

### Test Writing Best Practices
- Use data-testid attributes for reliable selectors
- Avoid hardcoded waits (use `waitForSelector` instead)
- Make tests independent and isolated
- Clean up test data after each run
- Use meaningful assertion messages
- Test both success and failure paths

---

## References

- [Playwright Documentation](https://playwright.dev/docs/intro)
- [Testing Best Practices](https://playwright.dev/docs/best-practices)
- [Story 5.6: E2E Integration Testing](../stories/5.6.story.md)
- [Architecture Documentation](../architecture.md)
- [PRD](../prd.md)

---

## Support

For issues or questions:
1. Check this README
2. Review test files for examples
3. Check Playwright documentation
4. Contact development team

---

*Last Updated: Story 5.6 Implementation*
*Test Framework: Playwright v1.56.1*
*Coverage: 5 Test Scenarios, 25+ Test Cases*
