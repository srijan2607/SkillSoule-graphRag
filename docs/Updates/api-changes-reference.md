# API Changes Reference - Pipeline Monitoring Update

**Version:** 1.0
**Date:** October 25, 2025
**Audience:** API Consumers, Frontend Developers, Integration Partners

---

## Table of Contents

1. [Overview](#overview)
2. [WebSocket API Changes](#websocket-api-changes)
3. [Event Type Reference](#event-type-reference)
4. [Frontend Integration Guide](#frontend-integration-guide)
5. [Migration Guide](#migration-guide)
6. [Code Examples](#code-examples)

---

## Overview

### What Changed in the API

#### WebSocket Endpoint: `/monitor/live`

**Status:** ENHANCED (backward compatible)

**Before:**
- Only broadcasted Neo4j query logs
- Single event type: `neo4j_query`

**After:**
- Broadcasts Neo4j query logs AND pipeline stage events
- Two event types: `neo4j_query` and `pipeline_stage`

**Backward Compatibility:** ✅ YES
- Existing clients listening for `neo4j_query` continue to work
- New `pipeline_stage` events are additional, not breaking

---

## WebSocket API Changes

### Connection

**Endpoint:** `ws://localhost:8000/monitor/live`

**No Changes Required:** Existing connection code works as-is

```javascript
// Same connection code
const ws = new WebSocket('ws://localhost:8000/monitor/live');
```

### Message Types

#### NEW: Connection Established Message

**Sent:** Immediately after connection
**Purpose:** Confirm successful connection

```json
{
  "event_type": "connection_established",
  "message": "Connected to monitoring stream (Neo4j queries + RAG pipeline)",
  "timestamp": "2025-10-25T10:30:00.000Z"
}
```

**Frontend Action:**
```javascript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.event_type === 'connection_established') {
    console.log('✅ Connected to monitoring');
    // Update UI: Show "Connected" badge
  }
};
```

---

#### EXISTING: Neo4j Query Event

**Type:** `neo4j_query`
**Status:** UNCHANGED
**Description:** Real-time Neo4j query logs

```json
{
  "event_type": "neo4j_query",
  "query_text": "MATCH (s:Skill) WHERE s.name = $name RETURN s",
  "parameters": {"name": "Python"},
  "operation_type": "READ",
  "execution_time_ms": 23.5,
  "result_count": 1,
  "status": "success",
  "timestamp": "2025-10-25T10:30:00.500Z"
}
```

**Frontend Action (Unchanged):**
```javascript
if (message.event_type === 'neo4j_query') {
  // Existing code continues to work
  logQueryToTable(message);
}
```

---

#### NEW: Pipeline Stage Event

**Type:** `pipeline_stage`
**Status:** NEW
**Description:** RAG pipeline stage execution events

**Base Schema:**
```typescript
interface PipelineStageEvent {
  event_type: "pipeline_stage";
  stage: "query_understanding" | "vector_search" | "graph_traversal" |
         "context_construction" | "response_generation";
  status: "started" | "in_progress" | "completed" | "failed" | "skipped";
  session_id: string;
  user_id: string;
  query: string;
  timestamp: string; // ISO 8601
  duration_ms?: number; // Only for completed/failed
  data?: object; // Stage-specific data
}
```

**Event Sequence for Single Query:**
```
1. query_understanding:started
2. query_understanding:completed
3. vector_search:started
4. vector_search:completed
5. graph_traversal:started
6. graph_traversal:completed
7. context_construction:started
8. context_construction:completed
9. response_generation:started
10. response_generation:completed
```

---

### Stage-Specific Event Schemas

#### 1. Query Understanding

**STARTED Event:**
```json
{
  "event_type": "pipeline_stage",
  "stage": "query_understanding",
  "status": "started",
  "session_id": "abc-123",
  "user_id": "user-456",
  "query": "What skills do I need for data science?",
  "timestamp": "2025-10-25T10:30:00.000Z"
}
```

**COMPLETED Event:**
```json
{
  "event_type": "pipeline_stage",
  "stage": "query_understanding",
  "status": "completed",
  "session_id": "abc-123",
  "user_id": "user-456",
  "query": "What skills do I need for data science?",
  "duration_ms": 125.5,
  "data": {
    "intent": "skill_requirement",
    "confidence": 0.94,
    "entities": [
      {
        "type": "skill",
        "value": "data science",
        "confidence": 0.9
      }
    ]
  },
  "timestamp": "2025-10-25T10:30:00.125Z"
}
```

**FAILED Event:**
```json
{
  "event_type": "pipeline_stage",
  "stage": "query_understanding",
  "status": "failed",
  "session_id": "abc-123",
  "user_id": "user-456",
  "query": "What skills do I need for data science?",
  "duration_ms": 50.0,
  "data": {
    "error": "Failed to generate embedding: Connection timeout"
  },
  "timestamp": "2025-10-25T10:30:00.050Z"
}
```

---

#### 2. Vector Search

**COMPLETED Event:**
```json
{
  "event_type": "pipeline_stage",
  "stage": "vector_search",
  "status": "completed",
  "session_id": "abc-123",
  "user_id": "user-456",
  "query": "What skills do I need for data science?",
  "duration_ms": 45.2,
  "data": {
    "skills_found": 10,
    "jobs_found": 5,
    "companies_found": 3,
    "total_results": 18,
    "threshold": 0.75
  },
  "timestamp": "2025-10-25T10:30:00.170Z"
}
```

**Key Fields:**
- `skills_found`: Number of skill nodes found
- `jobs_found`: Number of job nodes found
- `companies_found`: Number of company nodes found
- `total_results`: Total after merging and ranking
- `threshold`: Similarity threshold used (0.0-1.0)

---

#### 3. Graph Traversal

**COMPLETED Event:**
```json
{
  "event_type": "pipeline_stage",
  "stage": "graph_traversal",
  "status": "completed",
  "session_id": "abc-123",
  "user_id": "user-456",
  "query": "What skills do I need for data science?",
  "duration_ms": 58.3,
  "data": {
    "nodes_accessed": 50,
    "relationships_traversed": 75,
    "traversal_patterns": ["skill_requirement"]
  },
  "timestamp": "2025-10-25T10:30:00.228Z"
}
```

**Key Fields:**
- `nodes_accessed`: Number of graph nodes retrieved
- `relationships_traversed`: Number of relationships followed
- `traversal_patterns`: Intent patterns used for traversal

---

#### 4. Context Construction

**COMPLETED Event:**
```json
{
  "event_type": "pipeline_stage",
  "stage": "context_construction",
  "status": "completed",
  "session_id": "abc-123",
  "user_id": "user-456",
  "query": "What skills do I need for data science?",
  "duration_ms": 23.1,
  "data": {
    "context_tokens": 2500,
    "context_length": 15000,
    "was_truncated": false
  },
  "timestamp": "2025-10-25T10:30:00.251Z"
}
```

**Key Fields:**
- `context_tokens`: Token count for LLM context
- `context_length`: Character count
- `was_truncated`: Whether context exceeded 4000 token limit

---

#### 5. Response Generation

**COMPLETED Event:**
```json
{
  "event_type": "pipeline_stage",
  "stage": "response_generation",
  "status": "completed",
  "session_id": "abc-123",
  "user_id": "user-456",
  "query": "What skills do I need for data science?",
  "duration_ms": 1234.5,
  "data": {
    "model": "meta-llama/llama-4-maverick:free",
    "tokens_used": 850,
    "response_length": 1200
  },
  "timestamp": "2025-10-25T10:30:01.485Z"
}
```

**Key Fields:**
- `model`: LLM model used for generation
- `tokens_used`: Total tokens (prompt + completion)
- `response_length`: Response character count

---

## Event Type Reference

### Complete Event Type Matrix

| Event Type | Stage | Status | Has Duration | Has Data | Description |
|-----------|-------|--------|--------------|----------|-------------|
| `pipeline_stage` | `query_understanding` | `started` | ❌ | ❌ | Intent analysis began |
| `pipeline_stage` | `query_understanding` | `completed` | ✅ | ✅ | Intent detected with entities |
| `pipeline_stage` | `query_understanding` | `failed` | ✅ | ✅ | Intent analysis error |
| `pipeline_stage` | `vector_search` | `started` | ❌ | ❌ | Semantic search began |
| `pipeline_stage` | `vector_search` | `completed` | ✅ | ✅ | Found skills/jobs/companies |
| `pipeline_stage` | `vector_search` | `failed` | ✅ | ✅ | Search error (e.g., Neo4j down) |
| `pipeline_stage` | `graph_traversal` | `started` | ❌ | ❌ | Graph navigation began |
| `pipeline_stage` | `graph_traversal` | `completed` | ✅ | ✅ | Retrieved graph context |
| `pipeline_stage` | `graph_traversal` | `failed` | ✅ | ✅ | Traversal error |
| `pipeline_stage` | `context_construction` | `started` | ❌ | ❌ | Building LLM context |
| `pipeline_stage` | `context_construction` | `completed` | ✅ | ✅ | Context ready (tokens, truncation) |
| `pipeline_stage` | `context_construction` | `failed` | ✅ | ✅ | Context build error |
| `pipeline_stage` | `response_generation` | `started` | ❌ | ❌ | Calling LLM |
| `pipeline_stage` | `response_generation` | `completed` | ✅ | ✅ | Response generated (model, tokens) |
| `pipeline_stage` | `response_generation` | `failed` | ✅ | ✅ | LLM error (rate limit, timeout) |
| `neo4j_query` | N/A | N/A | ✅ | ✅ | Neo4j query log (unchanged) |
| `connection_established` | N/A | N/A | ❌ | ❌ | WebSocket connected |

---

## Frontend Integration Guide

### React Example: Pipeline Progress Component

```tsx
import React, { useEffect, useState } from 'react';
import { Progress } from '@/components/ui/progress';

interface PipelineStage {
  name: string;
  label: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  duration_ms?: number;
  data?: any;
}

const PipelineMonitor: React.FC<{ sessionId: string }> = ({ sessionId }) => {
  const [stages, setStages] = useState<PipelineStage[]>([
    { name: 'query_understanding', label: 'Intent Detection', status: 'pending' },
    { name: 'vector_search', label: 'Semantic Search', status: 'pending' },
    { name: 'graph_traversal', label: 'Graph Navigation', status: 'pending' },
    { name: 'context_construction', label: 'Building Context', status: 'pending' },
    { name: 'response_generation', label: 'Generating Response', status: 'pending' }
  ]);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/monitor/live');

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      // Only process pipeline events for this session
      if (message.event_type === 'pipeline_stage' && message.session_id === sessionId) {
        setStages(prevStages =>
          prevStages.map(stage => {
            if (stage.name === message.stage) {
              return {
                ...stage,
                status: message.status === 'started' ? 'in_progress' : message.status,
                duration_ms: message.duration_ms,
                data: message.data
              };
            }
            return stage;
          })
        );
      }
    };

    return () => ws.close();
  }, [sessionId]);

  const completedStages = stages.filter(s => s.status === 'completed').length;
  const progress = (completedStages / stages.length) * 100;

  return (
    <div className="space-y-4">
      <Progress value={progress} className="w-full" />

      <div className="space-y-2">
        {stages.map(stage => (
          <div key={stage.name} className="flex items-center justify-between">
            <span className="text-sm">{stage.label}</span>

            {stage.status === 'pending' && (
              <span className="text-gray-400">⏳ Pending</span>
            )}

            {stage.status === 'in_progress' && (
              <span className="text-blue-500">🔄 In Progress</span>
            )}

            {stage.status === 'completed' && (
              <span className="text-green-500">
                ✅ Done ({stage.duration_ms?.toFixed(1)}ms)
              </span>
            )}

            {stage.status === 'failed' && (
              <span className="text-red-500">❌ Failed</span>
            )}
          </div>
        ))}
      </div>

      {/* Show stage-specific data */}
      {stages.find(s => s.name === 'vector_search' && s.status === 'completed') && (
        <div className="text-sm text-gray-600">
          Found: {stages.find(s => s.name === 'vector_search')?.data?.skills_found} skills,{' '}
          {stages.find(s => s.name === 'vector_search')?.data?.jobs_found} jobs
        </div>
      )}
    </div>
  );
};
```

---

### Vue Example: Event Logger

```vue
<template>
  <div class="pipeline-events">
    <div v-for="event in events" :key="event.id" :class="['event', event.status]">
      <span class="stage">{{ formatStage(event.stage) }}</span>
      <span class="status">{{ event.status }}</span>
      <span v-if="event.duration_ms" class="duration">
        {{ event.duration_ms.toFixed(1) }}ms
      </span>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      events: [],
      ws: null
    };
  },

  mounted() {
    this.ws = new WebSocket('ws://localhost:8000/monitor/live');

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.event_type === 'pipeline_stage') {
        this.events.push({
          id: Date.now(),
          stage: message.stage,
          status: message.status,
          duration_ms: message.duration_ms,
          timestamp: message.timestamp
        });

        // Keep only last 50 events
        if (this.events.length > 50) {
          this.events.shift();
        }
      }
    };
  },

  beforeUnmount() {
    if (this.ws) {
      this.ws.close();
    }
  },

  methods: {
    formatStage(stage) {
      const labels = {
        query_understanding: 'Intent Detection',
        vector_search: 'Vector Search',
        graph_traversal: 'Graph Traversal',
        context_construction: 'Context Build',
        response_generation: 'Response Gen'
      };
      return labels[stage] || stage;
    }
  }
};
</script>

<style scoped>
.event {
  padding: 8px;
  margin: 4px 0;
  border-left: 3px solid #ccc;
}

.event.started { border-color: #3b82f6; }
.event.completed { border-color: #10b981; }
.event.failed { border-color: #ef4444; }
</style>
```

---

### Vanilla JavaScript Example

```javascript
// Initialize WebSocket
const ws = new WebSocket('ws://localhost:8000/monitor/live');

// Track pipeline state
const pipelineState = {
  query_understanding: { status: 'pending' },
  vector_search: { status: 'pending' },
  graph_traversal: { status: 'pending' },
  context_construction: { status: 'pending' },
  response_generation: { status: 'pending' }
};

// Handle incoming messages
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.event_type === 'pipeline_stage') {
    // Update pipeline state
    pipelineState[message.stage] = {
      status: message.status,
      duration_ms: message.duration_ms,
      data: message.data,
      timestamp: message.timestamp
    };

    // Update UI
    updatePipelineUI(message.stage, message.status);

    // Handle completion
    if (message.stage === 'response_generation' && message.status === 'completed') {
      console.log('✅ Pipeline complete!');
      showCompletedMetrics();
    }
  }
};

function updatePipelineUI(stage, status) {
  const element = document.getElementById(`stage-${stage}`);
  element.className = `pipeline-stage ${status}`;

  const statusText = element.querySelector('.status');
  statusText.textContent = status.toUpperCase();
}

function showCompletedMetrics() {
  const totalDuration = Object.values(pipelineState)
    .reduce((sum, stage) => sum + (stage.duration_ms || 0), 0);

  console.log(`Total pipeline duration: ${totalDuration.toFixed(1)}ms`);

  // Show breakdown
  Object.entries(pipelineState).forEach(([stage, data]) => {
    console.log(`  ${stage}: ${data.duration_ms?.toFixed(1)}ms`);
  });
}
```

---

## Migration Guide

### For Existing Frontend Applications

#### Step 1: Update Message Handler

**Before:**
```javascript
ws.onmessage = (event) => {
  const query = JSON.parse(event.data);
  logQuery(query); // Only handled neo4j_query events
};
```

**After:**
```javascript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  // Handle different event types
  if (message.event_type === 'neo4j_query') {
    logQuery(message); // Existing code
  }
  else if (message.event_type === 'pipeline_stage') {
    updatePipelineMonitor(message); // NEW: Handle pipeline events
  }
  else if (message.event_type === 'connection_established') {
    console.log('Connected:', message.message);
  }
};
```

#### Step 2: Add Pipeline Monitoring UI

**New Component Structure:**
```
components/
  ├── monitoring/
  │   ├── PipelineProgress.tsx       (NEW)
  │   ├── StageDetails.tsx           (NEW)
  │   ├── QueryLogger.tsx            (existing)
  │   └── MonitoringDashboard.tsx    (updated)
```

#### Step 3: Session Tracking

**Add session ID to requests:**
```typescript
// Generate session ID on query submission
const sessionId = crypto.randomUUID();

// Send query with session ID
const response = await fetch('/api/chat/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: userId,
    query: userQuery,
    session_id: sessionId  // NEW: Track pipeline for this query
  })
});

// Use same session_id to filter WebSocket events
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.session_id === sessionId) {
    // This event belongs to current query
    updateUI(message);
  }
};
```

---

## Code Examples

### Example 1: Complete Pipeline Monitoring

```typescript
class PipelineMonitor {
  private ws: WebSocket;
  private sessionId: string;
  private stages: Map<string, StageInfo>;
  private callbacks: {
    onStageStart?: (stage: string) => void;
    onStageComplete?: (stage: string, data: any) => void;
    onStageFail?: (stage: string, error: string) => void;
    onPipelineComplete?: (metrics: PipelineMetrics) => void;
  };

  constructor(sessionId: string, callbacks: any) {
    this.sessionId = sessionId;
    this.callbacks = callbacks;
    this.stages = new Map();

    this.ws = new WebSocket('ws://localhost:8000/monitor/live');
    this.ws.onmessage = this.handleMessage.bind(this);
  }

  private handleMessage(event: MessageEvent) {
    const message = JSON.parse(event.data);

    if (message.event_type !== 'pipeline_stage') return;
    if (message.session_id !== this.sessionId) return;

    const { stage, status, duration_ms, data } = message;

    // Update stage info
    this.stages.set(stage, { status, duration_ms, data });

    // Trigger callbacks
    if (status === 'started' && this.callbacks.onStageStart) {
      this.callbacks.onStageStart(stage);
    }
    else if (status === 'completed' && this.callbacks.onStageComplete) {
      this.callbacks.onStageComplete(stage, data);
    }
    else if (status === 'failed' && this.callbacks.onStageFail) {
      this.callbacks.onStageFail(stage, data?.error);
    }

    // Check if pipeline complete
    if (stage === 'response_generation' && status === 'completed') {
      this.onPipelineComplete();
    }
  }

  private onPipelineComplete() {
    const metrics = {
      totalDuration: Array.from(this.stages.values())
        .reduce((sum, stage) => sum + (stage.duration_ms || 0), 0),
      stageBreakdown: Object.fromEntries(this.stages),
      completedAt: new Date().toISOString()
    };

    if (this.callbacks.onPipelineComplete) {
      this.callbacks.onPipelineComplete(metrics);
    }
  }

  close() {
    this.ws.close();
  }
}

// Usage
const monitor = new PipelineMonitor(sessionId, {
  onStageStart: (stage) => {
    console.log(`🔄 ${stage} started`);
    showSpinner(stage);
  },

  onStageComplete: (stage, data) => {
    console.log(`✅ ${stage} completed`, data);
    hideSpinner(stage);
  },

  onStageFail: (stage, error) => {
    console.error(`❌ ${stage} failed:`, error);
    showError(stage, error);
  },

  onPipelineComplete: (metrics) => {
    console.log('🎉 Pipeline complete!', metrics);
    showResults(metrics);
  }
});
```

---

### Example 2: Real-time Metrics Dashboard

```typescript
interface MetricsState {
  totalQueries: number;
  avgDuration: number;
  successRate: number;
  stagePerformance: Record<string, { avg: number, min: number, max: number }>;
}

class MetricsDashboard {
  private metrics: MetricsState = {
    totalQueries: 0,
    avgDuration: 0,
    successRate: 100,
    stagePerformance: {}
  };

  private queryMetrics: Map<string, any[]> = new Map();

  constructor() {
    const ws = new WebSocket('ws://localhost:8000/monitor/live');

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.event_type === 'pipeline_stage' && message.status === 'completed') {
        this.recordStageMetric(message);
      }

      if (message.stage === 'response_generation' && message.status === 'completed') {
        this.recordQueryComplete(message.session_id);
      }
    };
  }

  private recordStageMetric(message: any) {
    const { stage, duration_ms } = message;

    if (!this.metrics.stagePerformance[stage]) {
      this.metrics.stagePerformance[stage] = { avg: 0, min: Infinity, max: 0 };
    }

    const perf = this.metrics.stagePerformance[stage];
    perf.min = Math.min(perf.min, duration_ms);
    perf.max = Math.max(perf.max, duration_ms);

    // Update moving average
    const alpha = 0.2; // Weight for new values
    perf.avg = perf.avg === 0 ? duration_ms : (alpha * duration_ms + (1 - alpha) * perf.avg);

    this.updateDashboard();
  }

  private recordQueryComplete(sessionId: string) {
    this.metrics.totalQueries++;
    this.updateDashboard();
  }

  private updateDashboard() {
    // Update UI with latest metrics
    document.getElementById('total-queries')!.textContent =
      this.metrics.totalQueries.toString();

    // Update stage performance chart
    Object.entries(this.metrics.stagePerformance).forEach(([stage, perf]) => {
      updateChart(stage, perf);
    });
  }
}
```

---

**End of API Changes Reference**
