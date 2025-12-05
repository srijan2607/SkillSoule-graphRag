# Comprehensive Testing Guide - Pipeline Monitoring System

**Version:** 1.0
**Date:** October 25, 2025
**Audience:** QA Engineers, Test Automation Teams

---

## Table of Contents

1. [Test Environment Setup](#test-environment-setup)
2. [Functional Test Cases](#functional-test-cases)
3. [Integration Test Cases](#integration-test-cases)
4. [Performance Test Cases](#performance-test-cases)
5. [Error Handling Test Cases](#error-handling-test-cases)
6. [WebSocket Test Cases](#websocket-test-cases)
7. [Automation Scripts](#automation-scripts)
8. [Test Data](#test-data)

---

## Test Environment Setup

### Prerequisites

#### 1. Verify Neo4j Vector Indexes

```bash
# Connect to Neo4j
cypher-shell -u neo4j -p yourpassword

# Check indexes
SHOW INDEXES;

# Expected output:
# name                    type    entityType  labelsOrTypes  properties     state    populationPercent
# skill_embedding_idx     VECTOR  NODE        Skill          [embedding]    ONLINE   100.0
# job_embedding_idx       VECTOR  NODE        Job            [embedding]    ONLINE   100.0
# company_embedding_idx   VECTOR  NODE        Company        [embedding]    ONLINE   100.0
```

✅ **Pass Criteria:** All 3 vector indexes exist with ONLINE status and 100% population

---

#### 2. Start Backend Server

```bash
cd /Users/srijan26/Desktop/Dev/backend

# Install dependencies (if needed)
pip install -r requirements.txt

# Start server with reload
python -m uvicorn app.main:app --reload --port 8000 --log-level debug

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

✅ **Pass Criteria:** Server starts without errors, logs show "Application startup complete"

---

#### 3. Create Test WebSocket Client

Save as `test_websocket.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Pipeline Monitoring Test Client</title>
    <style>
        body { font-family: monospace; margin: 20px; }
        #events { border: 1px solid #ccc; padding: 10px; height: 400px; overflow-y: scroll; }
        .event { padding: 5px; margin: 5px 0; border-left: 3px solid #ccc; }
        .started { border-color: #3b82f6; background: #eff6ff; }
        .completed { border-color: #10b981; background: #ecfdf5; }
        .failed { border-color: #ef4444; background: #fef2f2; }
        #stats { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>Pipeline Monitoring Test Client</h1>

    <div>
        <button onclick="connect()">Connect</button>
        <button onclick="disconnect()">Disconnect</button>
        <button onclick="clearEvents()">Clear Events</button>
        <span id="status">Disconnected</span>
    </div>

    <div id="stats">
        <strong>Statistics:</strong>
        <span id="event-count">0 events received</span> |
        <span id="last-event">No events yet</span>
    </div>

    <div id="events"></div>

    <script>
        let ws = null;
        let eventCount = 0;

        function connect() {
            ws = new WebSocket('ws://localhost:8000/monitor/live');

            ws.onopen = () => {
                document.getElementById('status').textContent = 'Connected ✅';
                document.getElementById('status').style.color = 'green';
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                displayEvent(message);
                updateStats(message);
            };

            ws.onclose = () => {
                document.getElementById('status').textContent = 'Disconnected ❌';
                document.getElementById('status').style.color = 'red';
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
        }

        function disconnect() {
            if (ws) {
                ws.close();
            }
        }

        function displayEvent(message) {
            const eventsDiv = document.getElementById('events');
            const eventDiv = document.createElement('div');

            if (message.event_type === 'pipeline_stage') {
                eventDiv.className = `event ${message.status}`;
                eventDiv.innerHTML = `
                    <strong>${message.stage}</strong>: ${message.status}
                    ${message.duration_ms ? `(${message.duration_ms.toFixed(1)}ms)` : ''}
                    <br>
                    <small>${message.timestamp}</small>
                    ${message.data ? `<br><small>${JSON.stringify(message.data)}</small>` : ''}
                `;
            } else {
                eventDiv.className = 'event';
                eventDiv.innerHTML = `<pre>${JSON.stringify(message, null, 2)}</pre>`;
            }

            eventsDiv.insertBefore(eventDiv, eventsDiv.firstChild);
        }

        function updateStats(message) {
            eventCount++;
            document.getElementById('event-count').textContent = `${eventCount} events received`;
            document.getElementById('last-event').textContent = `Last: ${message.event_type || 'unknown'}`;
        }

        function clearEvents() {
            document.getElementById('events').innerHTML = '';
            eventCount = 0;
            document.getElementById('event-count').textContent = '0 events received';
        }
    </script>
</body>
</html>
```

Open in browser: `file:///path/to/test_websocket.html`

✅ **Pass Criteria:** Can connect and see "Connected ✅" status

---

## Functional Test Cases

### Test Case 1: Happy Path - Complete Pipeline Execution

**Test ID:** TC-001
**Priority:** CRITICAL
**Objective:** Verify full RAG pipeline executes successfully with monitoring

#### Test Steps:

1. Connect WebSocket test client
2. Send POST request:
   ```bash
   curl -X POST http://localhost:8000/api/chat/query \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "test-user-001",
       "query": "What skills do I need for data science?"
     }'
   ```

3. Monitor WebSocket events
4. Wait for HTTP response

#### Expected Results:

**WebSocket Events (10 total):**
```
Event 1: pipeline_stage | query_understanding | started
Event 2: pipeline_stage | query_understanding | completed
         data: { intent: "skill_requirement", confidence: 0.9+ }
Event 3: pipeline_stage | vector_search | started
Event 4: pipeline_stage | vector_search | completed
         data: { skills_found: >0, jobs_found: >0, total_results: >0 }
Event 5: pipeline_stage | graph_traversal | started
Event 6: pipeline_stage | graph_traversal | completed
         data: { nodes_accessed: >0, relationships_traversed: >0 }
Event 7: pipeline_stage | context_construction | started
Event 8: pipeline_stage | context_construction | completed
         data: { context_tokens: >0, was_truncated: false }
Event 9: pipeline_stage | response_generation | started
Event 10: pipeline_stage | response_generation | completed
          data: { model: "...", tokens_used: >0 }
```

**HTTP Response:**
```json
{
  "response": "Based on the job market data, data science roles...",
  "metadata": {
    "session_id": "...",
    "total_duration_ms": 1200-2500
  }
}
```

#### Pass Criteria:
- ✅ Received exactly 10 WebSocket events
- ✅ Events in correct order (started → completed per stage)
- ✅ All COMPLETED events have `duration_ms > 0`
- ✅ All COMPLETED events have stage-specific data
- ✅ No FAILED events
- ✅ HTTP response is conversational (not technical tables)
- ✅ Total duration < 3000ms

#### Failure Indicators:
- ❌ Missing events (< 10 received)
- ❌ Events out of order
- ❌ Any FAILED status
- ❌ duration_ms = 0 or negative
- ❌ Response contains markdown tables

---

### Test Case 2: Intent Detection Accuracy

**Test ID:** TC-002
**Priority:** HIGH
**Objective:** Verify correct intent classification for different query types

#### Test Data:

| Query | Expected Intent | Min Confidence |
|-------|----------------|----------------|
| "What skills do I need for machine learning?" | skill_requirement | 0.85 |
| "How do I transition from Java to Python?" | career_path | 0.80 |
| "What is the salary for senior developers?" | salary_analysis | 0.85 |
| "Which companies hire React developers?" | company_query | 0.85 |
| "Is Python similar to JavaScript?" | skill_relationship | 0.80 |

#### Test Steps:

For each query:
1. Send POST request with query
2. Capture `query_understanding:completed` event
3. Extract `intent` and `confidence` from event data

#### Expected Results:

```javascript
// Event data structure
{
  "event_type": "pipeline_stage",
  "stage": "query_understanding",
  "status": "completed",
  "data": {
    "intent": "<expected_intent>",
    "confidence": 0.XX,  // >= min confidence
    "entities": [...]
  }
}
```

#### Pass Criteria:
- ✅ Intent matches expected for all 5 queries
- ✅ Confidence >= minimum threshold
- ✅ At least 1 entity extracted per query

---

### Test Case 3: Vector Search Results

**Test ID:** TC-003
**Priority:** HIGH
**Objective:** Verify vector search returns relevant results

#### Test Steps:

1. Send query: "Python programming skills"
2. Capture `vector_search:completed` event
3. Verify result counts

#### Expected Results:

```json
{
  "stage": "vector_search",
  "status": "completed",
  "data": {
    "skills_found": 5-15,      // Should find Python-related skills
    "jobs_found": 5-15,        // Should find Python jobs
    "companies_found": 0-10,   // May or may not find companies
    "total_results": 10-20,    // Combined top results
    "threshold": 0.75          // Similarity threshold
  }
}
```

#### Pass Criteria:
- ✅ `skills_found > 0`
- ✅ `jobs_found > 0`
- ✅ `total_results >= skills_found + jobs_found`
- ✅ `threshold` between 0.5 and 0.9
- ✅ Duration < 100ms

---

### Test Case 4: Conversational Response Format

**Test ID:** TC-004
**Priority:** HIGH
**Objective:** Verify response is user-friendly, not technical

#### Test Steps:

1. Send query: "What skills do I need for data science?"
2. Capture HTTP response
3. Analyze response format

#### Expected Response Characteristics:

```markdown
✅ Should contain:
- Natural language intro ("Based on the job market data...")
- Bullet points with skill categories
- Conversational language ("most positions", "typically")
- Actionable recommendations ("Start with...", "Focus on...")
- Collapsible <details> section at end

❌ Should NOT contain:
- Markdown tables
- Exact percentages (e.g., "95.3%")
- Technical jargon in main text ("confidence: 0.94")
- Query execution details in main text
- Raw metrics visible by default
```

#### Pass Criteria:
- ✅ Response starts with conversational intro
- ✅ Contains "**Essential Skills:**" or similar section
- ✅ Contains "**Next Steps:**" or similar
- ✅ Has `<details>` tag for technical details
- ✅ No markdown tables in main response
- ✅ Uses natural language ("most", "typically")

#### Validation Script:

```python
def validate_response_format(response_text):
    checks = {
        'conversational_intro': bool(re.search(r'Based on.*data', response_text)),
        'has_essential_skills': '**Essential Skills:**' in response_text,
        'has_next_steps': '**Next Steps:**' in response_text or 'recommend' in response_text.lower(),
        'has_details_section': '<details>' in response_text,
        'no_tables': '|---|' not in response_text,
        'uses_natural_language': any(word in response_text for word in ['most', 'typically', 'usually'])
    }
    return all(checks.values()), checks

# Usage
is_valid, details = validate_response_format(response)
print(f"Valid: {is_valid}")
print(f"Details: {details}")
```

---

## Integration Test Cases

### Test Case 5: Multi-Intent Query Handling

**Test ID:** TC-005
**Priority:** MEDIUM
**Objective:** Verify system handles queries with multiple intents

#### Test Steps:

1. Send complex query: "What skills and salary can I expect for data science roles at Google?"
2. Monitor all pipeline events
3. Verify multi-intent handling

#### Expected Behavior:

```json
// query_understanding:completed
{
  "data": {
    "intent": "skill_requirement",  // Primary intent
    "confidence": 0.XX,
    "entities": [
      { "type": "skill", "value": "data science" },
      { "type": "company", "value": "Google" }
    ]
  }
}

// graph_traversal:completed
{
  "data": {
    "traversal_patterns": [
      "skill_requirement",
      "salary_analysis",
      "company_query"
    ]  // Multiple patterns executed
  }
}
```

#### Pass Criteria:
- ✅ Multiple entities detected (skill + company)
- ✅ Graph traversal uses multiple patterns
- ✅ Response addresses all aspects (skills, salary, company)

---

### Test Case 6: Context Truncation Handling

**Test ID:** TC-006
**Priority:** MEDIUM
**Objective:** Verify system handles large context gracefully

#### Test Steps:

1. Send broad query: "Tell me everything about software engineering careers"
2. Monitor `context_construction:completed` event
3. Check if truncation occurred

#### Expected Results:

**If truncated (`context_tokens > 4000`):**
```json
{
  "stage": "context_construction",
  "status": "completed",
  "data": {
    "context_tokens": 4000,  // Capped at limit
    "context_length": ~25000,
    "was_truncated": true
  }
}
```

**Response should include note:**
```markdown
...

*Note: Some graph relationships were truncated to fit context limit.*

<details>
...
</details>
```

#### Pass Criteria:
- ✅ `context_tokens <= 4000`
- ✅ If truncated, `was_truncated = true`
- ✅ Response includes truncation note
- ✅ Response generation still succeeds

---

## Performance Test Cases

### Test Case 7: Stage Duration Benchmarks

**Test ID:** TC-007
**Priority:** MEDIUM
**Objective:** Verify each stage completes within acceptable time

#### Test Steps:

1. Send 10 sequential queries (varied topics)
2. Record duration_ms for each stage
3. Calculate average per stage

#### Expected Duration Ranges:

| Stage | Min (ms) | Target (ms) | Max (ms) | % of Total |
|-------|----------|-------------|----------|------------|
| Query Understanding | 50 | 120 | 200 | 5-10% |
| Vector Search | 30 | 50 | 100 | 2-5% |
| Graph Traversal | 40 | 70 | 150 | 3-7% |
| Context Construction | 15 | 30 | 60 | 1-3% |
| Response Generation | 800 | 1500 | 3000 | 60-80% |
| **TOTAL** | **935** | **1770** | **3510** | **100%** |

#### Pass Criteria:
- ✅ 90% of queries complete in < 2500ms
- ✅ No stage exceeds max duration
- ✅ Response generation is largest contributor (50%+)

#### Performance Report Script:

```python
import statistics

def analyze_performance(query_results):
    """Analyze performance across multiple queries."""
    stages = ['query_understanding', 'vector_search', 'graph_traversal',
              'context_construction', 'response_generation']

    report = {}
    for stage in stages:
        durations = [q[stage]['duration_ms'] for q in query_results]
        report[stage] = {
            'min': min(durations),
            'max': max(durations),
            'avg': statistics.mean(durations),
            'median': statistics.median(durations),
            'stdev': statistics.stdev(durations) if len(durations) > 1 else 0
        }

    return report

# Example usage
results = run_10_queries()
performance = analyze_performance(results)
print_performance_table(performance)
```

---

### Test Case 8: Concurrent User Load

**Test ID:** TC-008
**Priority:** LOW
**Objective:** Verify system handles multiple simultaneous users

#### Test Setup:

```python
import asyncio
import aiohttp

async def send_query(session, user_id, query):
    """Send a query and collect events."""
    async with session.post(
        'http://localhost:8000/api/chat/query',
        json={'user_id': user_id, 'query': query}
    ) as response:
        return await response.json()

async def concurrent_load_test(num_users=10):
    """Run concurrent queries from multiple users."""
    async with aiohttp.ClientSession() as session:
        tasks = [
            send_query(session, f'user-{i}', 'What skills for data science?')
            for i in range(num_users)
        ]
        results = await asyncio.gather(*tasks)
        return results

# Run test
results = asyncio.run(concurrent_load_test(10))
```

#### Expected Results:

- All 10 queries complete successfully
- Each query receives 10 WebSocket events
- No event cross-contamination (user A doesn't see user B's events)
- Average duration < 3000ms per query

#### Pass Criteria:
- ✅ 100% success rate (all queries succeed)
- ✅ No duplicate or mixed events
- ✅ Performance degradation < 20% (avg duration)

---

## Error Handling Test Cases

### Test Case 9: Neo4j Connection Failure

**Test ID:** TC-009
**Priority:** HIGH
**Objective:** Verify graceful handling when Neo4j is unavailable

#### Test Steps:

1. Stop Neo4j database:
   ```bash
   neo4j stop
   ```

2. Send query: "What skills for data science?"

3. Monitor events

#### Expected Results:

```json
// vector_search:failed
{
  "event_type": "pipeline_stage",
  "stage": "vector_search",
  "status": "failed",
  "duration_ms": 5000,  // Timeout duration
  "data": {
    "error": "Failed to connect to Neo4j..."
  }
}
```

**HTTP Response:**
```json
{
  "response": "We're having trouble accessing our database. Please try again in a moment.",
  "error": "vector_search_failed",
  "session_id": "..."
}
```

#### Pass Criteria:
- ✅ FAILED event emitted for vector_search
- ✅ Error message is user-friendly (not technical stack trace)
- ✅ Pipeline stops gracefully (no subsequent stage events)
- ✅ Session ID provided for support

#### Cleanup:
```bash
neo4j start
# Wait for startup
sleep 10
```

---

### Test Case 10: LLM Rate Limiting

**Test ID:** TC-010
**Priority:** MEDIUM
**Objective:** Verify handling of OpenRouter rate limit errors

#### Test Steps:

1. Send 5 rapid queries (to trigger rate limit)
2. Observe 5th query behavior

#### Expected Results:

```json
// response_generation:failed (after 3 retries)
{
  "event_type": "pipeline_stage",
  "stage": "response_generation",
  "status": "failed",
  "duration_ms": 15000,  // 3 retries with backoff
  "data": {
    "error": "Rate limit exceeded. Please try again shortly."
  }
}
```

**HTTP Response:**
```json
{
  "response": "Unable to generate response due to high demand. Please try again in a moment.",
  "error": "llm_rate_limited"
}
```

#### Pass Criteria:
- ✅ System attempts 3 retries with exponential backoff
- ✅ FAILED event emitted after retries exhausted
- ✅ User receives friendly error message
- ✅ Pipeline stages before response_generation still succeeded

---

## WebSocket Test Cases

### Test Case 11: WebSocket Connection Lifecycle

**Test ID:** TC-011
**Priority:** HIGH
**Objective:** Verify WebSocket connection/disconnection handling

#### Test Steps:

**Phase 1: Connection**
1. Connect WebSocket client
2. Verify connection established message

**Phase 2: Active Session**
3. Send 3 queries
4. Verify events received for all 3

**Phase 3: Disconnection**
5. Disconnect WebSocket
6. Send 4th query (WebSocket disconnected)
7. Reconnect WebSocket
8. Send 5th query

#### Expected Results:

**Phase 1:**
```json
{
  "event_type": "connection_established",
  "message": "Connected to monitoring stream..."
}
```

**Phase 2:**
- Receive 30 events (3 queries × 10 events each)

**Phase 3:**
- Query 4: Succeeds via HTTP (no WebSocket events received)
- Query 5: After reconnect, receive 10 new events

#### Pass Criteria:
- ✅ Connection message received immediately
- ✅ All events received during active connection
- ✅ No errors when client disconnects
- ✅ Reconnection works seamlessly
- ✅ Server logs show clean connection lifecycle

---

### Test Case 12: WebSocket Event Ordering

**Test ID:** TC-012
**Priority:** MEDIUM
**Objective:** Verify events arrive in correct order

#### Test Steps:

1. Connect WebSocket
2. Send query
3. Capture all events with timestamps
4. Analyze ordering

#### Expected Event Order:

```
1. query_understanding:started      (t0)
2. query_understanding:completed    (t0 + duration1)
3. vector_search:started            (t0 + duration1)
4. vector_search:completed          (t0 + duration1 + duration2)
5. graph_traversal:started          (...)
6. graph_traversal:completed
7. context_construction:started
8. context_construction:completed
9. response_generation:started
10. response_generation:completed
```

#### Validation Script:

```python
def validate_event_order(events):
    """Validate events are in correct order."""
    expected_order = [
        ('query_understanding', 'started'),
        ('query_understanding', 'completed'),
        ('vector_search', 'started'),
        ('vector_search', 'completed'),
        ('graph_traversal', 'started'),
        ('graph_traversal', 'completed'),
        ('context_construction', 'started'),
        ('context_construction', 'completed'),
        ('response_generation', 'started'),
        ('response_generation', 'completed')
    ]

    actual_order = [(e['stage'], e['status']) for e in events]

    return actual_order == expected_order

# Usage
is_valid = validate_event_order(captured_events)
assert is_valid, f"Event order mismatch! Got: {actual_order}"
```

#### Pass Criteria:
- ✅ Events arrive in expected order
- ✅ STARTED before COMPLETED for each stage
- ✅ Timestamps are monotonically increasing

---

## Automation Scripts

### Full Test Suite Runner

```python
"""
Pipeline Monitoring Test Suite
Run all test cases and generate report
"""
import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any

class TestResult:
    def __init__(self, test_id: str, name: str):
        self.test_id = test_id
        self.name = name
        self.status = 'pending'
        self.duration_ms = 0
        self.errors = []
        self.details = {}

class PipelineTestSuite:
    def __init__(self, base_url='http://localhost:8000'):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.ws = None

    async def run_all_tests(self):
        """Run all test cases."""
        print("=" * 60)
        print("PIPELINE MONITORING TEST SUITE")
        print("=" * 60)
        print(f"Started: {datetime.now().isoformat()}")
        print()

        test_cases = [
            self.test_happy_path,
            self.test_intent_detection,
            self.test_vector_search,
            self.test_response_format,
            self.test_multi_intent,
            self.test_context_truncation,
            self.test_performance,
            self.test_concurrent_load,
            self.test_neo4j_failure,
            self.test_llm_rate_limit,
            self.test_websocket_lifecycle,
            self.test_event_ordering
        ]

        for test_func in test_cases:
            await test_func()
            await asyncio.sleep(1)  # Brief pause between tests

        self.print_summary()

    async def test_happy_path(self):
        """TC-001: Happy Path"""
        result = TestResult('TC-001', 'Happy Path - Complete Pipeline')
        start = time.time()

        try:
            # Connect WebSocket
            # ... (implementation)

            # Send query
            response = await self.send_query('What skills for data science?')

            # Validate events
            assert len(self.captured_events) == 10, "Expected 10 events"
            assert response['response'].startswith('Based on'), "Response not conversational"

            result.status = 'passed'
        except Exception as e:
            result.status = 'failed'
            result.errors.append(str(e))
        finally:
            result.duration_ms = (time.time() - start) * 1000
            self.results.append(result)

    # ... (implement other test methods)

    def print_summary(self):
        """Print test execution summary."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.status == 'passed')
        failed = sum(1 for r in self.results if r.status == 'failed')
        total = len(self.results)

        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {passed/total*100:.1f}%")
        print()

        if failed > 0:
            print("FAILED TESTS:")
            for result in self.results:
                if result.status == 'failed':
                    print(f"  - {result.test_id}: {result.name}")
                    for error in result.errors:
                        print(f"    ❌ {error}")

        print()
        print(f"Completed: {datetime.now().isoformat()}")

# Run tests
if __name__ == '__main__':
    suite = PipelineTestSuite()
    asyncio.run(suite.run_all_tests())
```

---

## Test Data

### Sample Queries for Testing

```python
TEST_QUERIES = {
    'skill_requirement': [
        "What skills do I need for data science?",
        "What skills for machine learning engineer?",
        "Required skills for backend developer?"
    ],
    'career_path': [
        "How do I transition from Java to Python?",
        "Career path from developer to architect",
        "How to become a data scientist?"
    ],
    'salary_analysis': [
        "What is the salary for senior developers?",
        "Salary expectations for ML engineer in India",
        "How much do data scientists earn?"
    ],
    'company_query': [
        "Which companies hire React developers?",
        "Companies using Python in India",
        "Top tech companies in Bangalore"
    ],
    'skill_relationship': [
        "Is Python similar to JavaScript?",
        "Difference between React and Vue",
        "Java vs Kotlin comparison"
    ],
    'multi_intent': [
        "What skills and salary for data science at Google?",
        "Career path and companies for ML engineers",
        "Skills needed and expected pay for React developers"
    ]
}
```

---

## Test Execution Checklist

### Pre-Test Setup
- [ ] Neo4j running with vector indexes
- [ ] Backend server running on port 8000
- [ ] Test WebSocket client ready
- [ ] Test data loaded

### Execution
- [ ] Run TC-001 through TC-012 in order
- [ ] Document all failures with screenshots
- [ ] Capture WebSocket event logs
- [ ] Record performance metrics

### Post-Test
- [ ] Generate test report
- [ ] Analyze failure patterns
- [ ] Update documentation if needed
- [ ] File bugs for critical issues

---

**End of Comprehensive Testing Guide**
