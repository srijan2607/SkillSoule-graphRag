# GitHub Copilot Instructions

## Project Overview

This is a **Career Intelligence AI System** - a Graph RAG (Retrieval-Augmented Generation) application that combines Neo4j knowledge graphs with LangGraph orchestration to provide conversational career guidance. Users can upload skills/jobs data via CSV, and ask natural language questions about careers, skills, salary ranges, and job requirements.

**Core Technologies:**
- **Backend**: Python 3.11+, FastAPI, LangGraph, OpenRouter LLM API
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS
- **Databases**: Neo4j (graph), PostgreSQL (relational via Prisma)
- **AI/ML**: HuggingFace Transformers, sentence-transformers, OpenRouter API

## Architecture Pattern

**Monorepo Structure:**
```
/backend/        # FastAPI application
  /app/
    /api/        # FastAPI route handlers
    /agents/     # LangGraph workflow nodes
    /services/   # Business logic (auth, neo4j, langgraph)
    /repositories/ # Database access layer (Prisma)
    /models/     # Pydantic schemas
    /utils/      # Utilities (logger, validation)
    main.py      # FastAPI app entry point
/frontend/       # React application
  /src/
    /pages/      # React pages (Chat, Upload, Auth)
    /components/ # Reusable React components
    /hooks/      # Custom React hooks
    /utils/      # API client, auth utilities
```

**Data Flow:**
1. CSV Upload → FastAPI validates → Batch processing → Neo4j graph construction
2. User Query → LangGraph workflow → Hybrid search (vector + graph) → LLM response

## Code Style & Conventions

### Python (Backend)

**General Guidelines:**
- Use async/await for all I/O operations (database, HTTP, file operations)
- Type hints required for all function signatures
- Pydantic models for request/response validation
- Dependency injection via FastAPI's `Depends()`
- Error handling with custom exception classes

**Naming Conventions:**
- Files: `snake_case.py` (e.g., `auth_service.py`)
- Classes: `PascalCase` (e.g., `AuthService`, `UserRepository`)
- Functions/variables: `snake_case` (e.g., `generate_embeddings`, `user_id`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_FILE_SIZE`, `JWT_SECRET`)

**Example Pattern - FastAPI Endpoint:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.request import QueryRequest
from app.models.response import QueryResponse
from app.services.langgraph_service import LangGraphService
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/query", tags=["query"])

@router.post("/", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    user_id: int = Depends(get_current_user),
    langgraph_service: LangGraphService = Depends()
) -> QueryResponse:
    """Process natural language query using LangGraph RAG workflow."""
    try:
        result = await langgraph_service.process_query(
            query=request.query,
            user_id=user_id
        )
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )
```

**Example Pattern - Service Layer:**
```python
from typing import List, Dict, Any
from neo4j import AsyncDriver

class Neo4jService:
    def __init__(self, driver: AsyncDriver):
        self._driver = driver
    
    async def vector_search(
        self, 
        query_embedding: List[float], 
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search on embeddings."""
        async with self._driver.session() as session:
            result = await session.run(
                """
                CALL db.index.vector.queryNodes(
                    'skill_embedding_index', 
                    $limit, 
                    $embedding
                ) YIELD node, score
                RETURN node, score
                """,
                limit=limit,
                embedding=query_embedding
            )
            return [record.data() async for record in result]
```

**LangGraph Node Pattern:**
```python
from typing import TypedDict
from langchain_core.runnables import RunnableConfig

class GraphState(TypedDict):
    user_query: str
    query_embedding: List[float]
    query_intent: str
    vector_results: List[Dict]
    response: str

async def query_understanding_node(
    state: GraphState, 
    config: RunnableConfig
) -> GraphState:
    """LangGraph node: Classify query intent and generate embedding."""
    embedding_service = config["configurable"]["embedding_service"]
    
    # Generate embedding
    embedding = await embedding_service.generate_embedding(state["user_query"])
    
    # Classify intent (simple keyword matching)
    query_lower = state["user_query"].lower()
    if any(kw in query_lower for kw in ["skills for", "skills needed"]):
        intent = "skill_requirement"
    elif any(kw in query_lower for kw in ["salary", "pay"]):
        intent = "salary_analysis"
    else:
        intent = "general"
    
    return {
        **state,
        "query_embedding": embedding,
        "query_intent": intent
    }
```

### TypeScript/React (Frontend)

**General Guidelines:**
- Functional components with hooks (no class components)
- TypeScript for all components and utilities
- Custom hooks for reusable logic (e.g., `useAuth`, `useApi`)
- TailwindCSS for styling (no CSS modules/styled-components)
- Async operations with `useEffect` + `useState` or React Query

**Naming Conventions:**
- Files: `PascalCase.tsx` for components (e.g., `ChatInterface.tsx`)
- Files: `camelCase.ts` for utilities (e.g., `apiClient.ts`)
- Components: `PascalCase` (e.g., `ChatMessage`, `FileUpload`)
- Functions/variables: `camelCase` (e.g., `sendMessage`, `userId`)
- Types/Interfaces: `PascalCase` with `I` prefix for interfaces (e.g., `IMessage`, `IUser`)

**Example Pattern - React Component:**
```typescript
import React, { useState, useEffect } from 'react';
import { apiClient } from '@/utils/apiClient';

interface IMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Array<{ node_type: string; node_id: string }>;
}

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<IMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: IMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await apiClient.post('/query', { query: inputValue });
      
      const assistantMessage: IMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString(),
        sources: response.data.sources
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Query failed:', error);
      // Add error message to chat
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {isLoading && <TypingIndicator />}
      </div>
      
      {/* Input field */}
      <div className="border-t bg-white p-4">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Ask about careers, skills, or jobs..."
          className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2"
        />
      </div>
    </div>
  );
};
```

**Example Pattern - API Client:**
```typescript
import axios, { AxiosInstance } from 'axios';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
      headers: { 'Content-Type': 'application/json' }
    });

    // Add JWT token to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('jwt_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle 401 errors (redirect to login)
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('jwt_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  async post<T>(url: string, data: any): Promise<T> {
    const response = await this.client.post<T>(url, data);
    return response.data;
  }
}

export const apiClient = new ApiClient();
```

## Key Domain Concepts

### 1. Graph Schema (Neo4j)

**Node Types:**
- `Job`: Job postings (Job Title, Salary, Description, Location, Company)
- `Skill`: Skills taxonomy (ID, NAME, LEVEL, CATEGORY, DESCRIPTION, embedding)
- `Company`: Employers (Company Name, CIN, NIC codes, Description)
- `Location`: Job locations (Location name, District)
- `Category`: Skill categories (CATEGORY_NAME)
- `Subcategory`: Skill subcategories (SUBCATEGORY_NAME)

**Relationship Types:**
- `Job -[REQUIRES]-> Skill` (with similarity_score property)
- `Job -[POSTED_BY]-> Company`
- `Job -[LOCATED_IN]-> Location`
- `Skill -[BELONGS_TO_CATEGORY]-> Category`
- `Skill -[BELONGS_TO_SUBCATEGORY]-> Subcategory`
- `Skill -[SIMILAR_TO]-> Skill` (with similarity_score > 0.7)

**Example Cypher Query:**
```cypher
// Find skills required for Data Scientist jobs
MATCH (j:Job {Job_Title: "Data Scientist"})-[r:REQUIRES]->(s:Skill)
RETURN j.Job_Title, s.NAME, r.similarity_score
ORDER BY r.similarity_score DESC
LIMIT 10
```

### 2. LangGraph Workflow

**State Graph Nodes:**
1. **QueryUnderstanding**: Classify intent → generate embedding
2. **VectorSearch**: Find similar nodes using Neo4j vector indexes
3. **GraphTraversal**: Explore relationships from vector results
4. **ContextConstruction**: Combine results into LLM context
5. **ResponseGeneration**: Call OpenRouter LLM → return answer

**Query Intent Types:**
- `skill_requirement`: "What skills for X job?"
- `career_path`: "How to transition from X to Y?"
- `salary_analysis`: "High-paying jobs with X skills?"
- `skill_relationship`: "What skills similar to X?"
- `company_query`: "Companies hiring for X skills?"

### 3. Embedding Generation

**Model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional)

**Text Fields to Embed:**
- Job: Job Description (primary), Description (fallback)
- Skill: DESCRIPTION (primary), WIKI_EXTRACT (secondary)
- Company: Company Description

**Batch Processing:**
- Generate embeddings in batches of 32-64 texts
- Store embeddings as node properties in Neo4j
- Use for vector similarity search (cosine similarity)

### 4. Authentication Flow

**JWT-Based Auth:**
1. User registers → Password hashed with bcrypt → Stored in PostgreSQL
2. User logs in → Password verified → JWT token generated (24h expiration)
3. Frontend stores token in localStorage
4. Protected requests include `Authorization: Bearer <token>` header
5. Backend middleware verifies token → Attaches user_id to request context

## Common Tasks & Patterns

### When Creating a New API Endpoint:

1. Define request/response Pydantic models in `app/models/`
2. Create route handler in `app/api/routes/`
3. Implement business logic in `app/services/`
4. Add JWT protection with `Depends(get_current_user)`
5. Add error handling with try/except → HTTPException
6. Write unit tests in `tests/unit/test_<feature>.py`

### When Adding a New LangGraph Node:

1. Define node function with signature: `async def node_name(state: GraphState, config: RunnableConfig) -> GraphState`
2. Update `GraphState` TypedDict with new state keys if needed
3. Add node to graph: `graph.add_node("node_name", node_name)`
4. Connect nodes: `graph.add_edge("previous_node", "node_name")`
5. Test node in isolation with mock state

### When Working with Neo4j:

1. Always use parameterized queries to prevent Cypher injection:
   ```python
   session.run("MATCH (s:Skill {NAME: $name}) RETURN s", name=skill_name)
   ```
2. Use async operations: `async with driver.session() as session`
3. Commit batches (500-1000 records) for bulk inserts
4. Create indexes for frequently queried properties
5. Use MERGE for upsert behavior (avoid duplicates)

### When Handling CSV Uploads:

1. Validate file type and size before processing
2. Use pandas for CSV parsing: `df = pd.read_csv(file)`
3. Validate required columns exist: `required_cols.issubset(df.columns)`
4. Process in batches (configurable via `BATCH_SIZE` env var)
5. Track progress: `{records_processed, records_failed, total_records}`
6. Log errors with row numbers for debugging

## Environment Variables

**Backend (.env):**
```bash
# Neo4j
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password

# PostgreSQL
DATABASE_URL=postgresql://user:pass@host:5432/db

# JWT
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_MODEL=meta-llama/llama-3.3-8b-instruct:free

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# CSV Processing
MAX_FILE_SIZE_MB=100
BATCH_SIZE=1000
```

**Frontend (.env):**
```bash
VITE_API_URL=http://localhost:8000
```

## Testing Guidelines

**Unit Tests (pytest):**
- Test business logic in isolation (services, utilities)
- Mock external dependencies (Neo4j, PostgreSQL, OpenRouter)
- Use fixtures for common test data
- Aim for >80% code coverage on critical paths

**Example Test Pattern:**
```python
import pytest
from unittest.mock import AsyncMock, patch
from app.services.auth_service import AuthService

@pytest.mark.asyncio
async def test_login_success(mock_user_repository):
    # Arrange
    mock_user_repository.get_by_email = AsyncMock(return_value={
        "id": 1,
        "email": "test@example.com",
        "password_hash": "$2b$12$hashed_password"
    })
    auth_service = AuthService(user_repository=mock_user_repository)
    
    # Act
    with patch('app.services.auth_service.verify_password', return_value=True):
        result = await auth_service.login("test@example.com", "correct_password")
    
    # Assert
    assert "token" in result
    assert result["user"]["email"] == "test@example.com"
```

## Performance Considerations

**Backend:**
- Use async operations for all I/O (database, HTTP, file reads)
- Batch database operations (commit every 500-1000 records)
- Connection pooling for Neo4j and PostgreSQL
- Cache embeddings in Neo4j (don't regenerate on every query)
- Limit vector search results (top 15-20 nodes)
- Limit graph traversal depth (2-3 hops max)

**Frontend:**
- Debounce input fields (e.g., search as you type)
- Poll ingestion status every 2 seconds (not more frequently)
- Lazy load components with React.lazy()
- Optimize re-renders with React.memo() for expensive components

**Target Metrics:**
- Query response time: <5 seconds
- CSV ingestion: ~5-10 minutes for 50K records
- Vector search: <1 second
- Graph traversal: <2 seconds

## Common Pitfalls to Avoid

1. **Don't** store JWT tokens in cookies or sessionStorage (use localStorage)
2. **Don't** commit `.env` files to git (use `.env.example` instead)
3. **Don't** use synchronous I/O in FastAPI routes (always async)
4. **Don't** forget to close Neo4j sessions (use `async with` context manager)
5. **Don't** hardcode environment values (always use env vars)
6. **Don't** ignore CSV validation errors (log them for data quality)
7. **Don't** exceed OpenRouter rate limits (implement retry logic)
8. **Don't** forget to normalize strings when matching (use `toLower()` in Cypher)

## Security Best Practices

- Hash passwords with bcrypt (12 rounds minimum)
- Validate all user inputs (Pydantic for backend, Zod for frontend)
- Use parameterized queries (prevent SQL/Cypher injection)
- Implement rate limiting on API endpoints (SlowAPI)
- Set CORS to allow only frontend origin
- Don't log sensitive data (passwords, tokens)
- Use HTTPS in production (even though MVP is HTTP)

## Helpful Commands

**Backend:**
```bash
# Run development server
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/ -v

# Run linting
ruff check app/

# Format code
black app/

# Generate Prisma client
prisma generate

# Apply migrations
prisma db push
```

**Frontend:**
```bash
# Run development server
cd frontend && npm run dev

# Run tests
npm test

# Build for production
npm run build

# Lint code
npm run lint
```

## Documentation References

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **Neo4j Cypher Manual**: https://neo4j.com/docs/cypher-manual/current/
- **Prisma Python Docs**: https://prisma-client-py.readthedocs.io/
- **React TypeScript Cheatsheet**: https://react-typescript-cheatsheet.netlify.app/

## Project Status & Roadmap

**Current Version**: MVP v1.0

**Completed Features:**
- User authentication (register/login with JWT)
- CSV upload and validation (skills and jobs)
- Neo4j graph construction with embeddings
- LangGraph RAG workflow
- Chat interface with natural language queries
- Conversation history support

**Known Issues:**
- See `/docs/known-issues-mvp-v1.0.md` for details
- Intent detection improvements needed for framework/technology queries
- Graph insights formatting in frontend

**Next Steps (Post-MVP):**
- Multi-turn conversation context
- Advanced query analytics
- User query history dashboard
- Export conversation transcripts
- Graph visualization in UI

---

**Last Updated**: October 28, 2025

**Questions?** Check the main README.md or PRD in `/docs/prd.md` for comprehensive documentation.
