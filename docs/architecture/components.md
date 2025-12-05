# Components

This section describes all major components in the backend architecture, organized by layer.

---

## 5.1 API Layer (FastAPI Endpoints)

The API layer exposes REST endpoints organized by domain. All endpoints follow RESTful conventions and return JSON responses.

### **Authentication Endpoints**

**Router**: `/api/auth`
**Module**: `app/api/auth.py`

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/auth/register` | User registration | `UserCreate` | `UserResponse` |
| POST | `/auth/login` | User login | `UserLogin` | `TokenResponse` |

**Example Implementation**:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, auth_service: AuthService = Depends()):
    """Register a new user account."""
    return await auth_service.register_user(user_data)

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, auth_service: AuthService = Depends()):
    """Authenticate user and return JWT token."""
    return await auth_service.login_user(credentials)
```

---

### **Ingestion Endpoints**

**Router**: `/api/ingest`
**Module**: `app/api/ingest.py`

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/ingest/skills` | Upload skills CSV | `UploadFile` | `IngestionJobResponse` |
| POST | `/ingest/jobs` | Upload jobs CSV | `UploadFile` | `IngestionJobResponse` |
| GET | `/ingest/status/{job_id}` | Check ingestion status | - | `IngestionStatusResponse` |

**Example Implementation**:
```python
from fastapi import APIRouter, UploadFile, File, Depends
from app.models.ingestion import IngestionJobResponse, IngestionStatusResponse
from app.services.ingestion_service import IngestionService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

@router.post("/skills", response_model=IngestionJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_skills_csv(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends()
):
    """Upload and process skills taxonomy CSV."""
    return await ingestion_service.start_skills_ingestion(file, current_user)

@router.post("/jobs", response_model=IngestionJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_jobs_csv(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends()
):
    """Upload and process jobs taxonomy CSV."""
    return await ingestion_service.start_jobs_ingestion(file, current_user)

@router.get("/status/{job_id}", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    job_id: str,
    current_user: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends()
):
    """Poll ingestion job status and progress."""
    return await ingestion_service.get_job_status(job_id, current_user)
```

---

### **Query Endpoint**

**Router**: `/api/query`
**Module**: `app/api/query.py`

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/query/ask` | Conversational AI query | `QueryRequest` | `QueryResponse` |

**Example Implementation**:
```python
from fastapi import APIRouter, Depends
from app.models.query import QueryRequest, QueryResponse
from app.services.langgraph_service import LangGraphService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/query", tags=["query"])

@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    query_data: QueryRequest,
    current_user: str = Depends(get_current_user),
    langgraph_service: LangGraphService = Depends()
):
    """Process natural language query through LangGraph RAG workflow."""
    return await langgraph_service.execute_query(query_data, current_user)
```

---

## 5.2 LangGraph Agent Layer

The LangGraph layer orchestrates the RAG workflow using a StateGraph with 5 specialized nodes.

### **StateGraph Definition**

**Module**: `app/agents/graph.py`

```python
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from app.agents.nodes import (
    query_understanding_node,
    vector_search_node,
    graph_traversal_node,
    context_construction_node,
    response_generation_node
)

class GraphRAGState(BaseModel):
    """
    Type-safe shared state for the RAG workflow.

    Uses Pydantic for runtime validation to prevent silent failures:
    - Typos in field names raise validation errors immediately
    - Type mismatches are caught at runtime
    - Required vs optional fields are enforced
    - Extra fields are forbidden (catches typos like 'user_qeury')
    """

    # Input fields (required)
    user_query: str = Field(..., min_length=1, description="Original user query text")
    user_id: str = Field(..., description="UUID of authenticated user")

    # Intermediate state (set by nodes, optional initially)
    intent: Optional[str] = Field(default=None, description="Detected query intent")
    entities: List[str] = Field(default_factory=list, description="Extracted named entities")
    vector_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Vector similarity search results from Neo4j"
    )
    graph_context: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Graph traversal context from Neo4j"
    )
    constructed_context: Optional[str] = Field(
        default=None,
        description="Constructed context string for LLM prompt"
    )

    # Output field (set by final node)
    final_response: Optional[str] = Field(
        default=None,
        description="Generated response from LLM"
    )

    # Metadata (optional)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (timestamps, costs, etc.)"
    )

    class Config:
        """Pydantic configuration for strict validation."""
        extra = "forbid"  # Raise error on unknown fields (catches typos)
        validate_assignment = True  # Validate on field assignment, not just initialization
        arbitrary_types_allowed = True  # Allow Any types for flexibility

    @validator('intent')
    def validate_intent(cls, v):
        """Ensure intent is one of the expected types."""
        if v is not None:
            valid_intents = ["skill_lookup", "job_search", "comparison", "explanation", "general"]
            if v not in valid_intents:
                raise ValueError(
                    f"Invalid intent: '{v}'. Must be one of {valid_intents}"
                )
        return v

    @validator('user_query')
    def validate_query_not_empty(cls, v):
        """Ensure query is not just whitespace."""
        if not v.strip():
            raise ValueError("user_query cannot be empty or whitespace")
        return v.strip()

def create_rag_workflow() -> StateGraph:
    """Create and compile the RAG StateGraph with type-safe state."""
    workflow = StateGraph(GraphRAGState)

    # Add nodes
    workflow.add_node("understand_query", query_understanding_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("graph_traversal", graph_traversal_node)
    workflow.add_node("construct_context", context_construction_node)
    workflow.add_node("generate_response", response_generation_node)

    # Define edges (linear flow for MVP)
    workflow.set_entry_point("understand_query")
    workflow.add_edge("understand_query", "vector_search")
    workflow.add_edge("vector_search", "graph_traversal")
    workflow.add_edge("graph_traversal", "construct_context")
    workflow.add_edge("construct_context", "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow.compile()
```

**Benefits of Pydantic over TypedDict**:

**Problem with TypedDict** (Previous Implementation):
```python
# ❌ TypedDict allows silent failures
class GraphRAGState(TypedDict):
    user_query: str
    intent: str

state = GraphRAGState(user_query="test", intnet="skill")  # Typo: 'intnet'
# Result: No error! Typo goes unnoticed, causes bugs later
print(state["intent"])  # KeyError at runtime (hard to debug)
```

**Solution with Pydantic** (Current Implementation):
```python
# ✅ Pydantic catches typos immediately
class GraphRAGState(BaseModel):
    user_query: str
    intent: Optional[str] = None

    class Config:
        extra = "forbid"  # Catch typos

try:
    state = GraphRAGState(user_query="test", intnet="skill")  # Typo: 'intnet'
except ValidationError as e:
    # Result: Immediate error with clear message!
    # pydantic.ValidationError: 1 validation error for GraphRAGState
    # intnet
    #   extra fields not permitted (type=value_error.extra)
    print(e)
```

**Runtime Type Safety Examples**:

**Example 1: Prevent Type Mismatches**
```python
# ❌ TypedDict: Wrong type accepted silently
state_dict = {"user_query": "test", "entities": "should be list"}  # Wrong type!
# No error until you try to iterate

# ✅ Pydantic: Immediate validation error
try:
    state = GraphRAGState(user_query="test", entities="should be list")
except ValidationError as e:
    # pydantic.ValidationError: entities
    #   value is not a valid list (type=type_error.list)
    print(e)
```

**Example 2: Intent Validation**
```python
# ❌ TypedDict: Invalid intent accepted
state_dict = {"user_query": "test", "intent": "invalid_intent"}
# Fails later in business logic with cryptic errors

# ✅ Pydantic: Custom validator catches invalid values
try:
    state = GraphRAGState(user_query="test", intent="invalid_intent")
except ValidationError as e:
    # pydantic.ValidationError: intent
    #   Invalid intent: 'invalid_intent'. Must be one of [...] (type=value_error)
    print(e)
```

**Example 3: Assignment Validation**
```python
# With validate_assignment=True, even field updates are validated
state = GraphRAGState(user_query="test query", user_id="user-123")

# ❌ TypedDict: Any assignment allowed
# state["entities"] = "not a list"  # No error until iteration

# ✅ Pydantic: Assignment validation
try:
    state.entities = "not a list"  # Wrong type!
except ValidationError as e:
    # pydantic.ValidationError: entities
    #   value is not a valid list (type=type_error.list)
    print(e)
```

**Node Return Value Pattern**:

**Pattern 1: Partial Updates** (Recommended for LangGraph)
```python
async def query_understanding_node(state: GraphRAGState) -> dict:
    """Return only the fields that changed."""
    # LangGraph merges the dict into the existing state
    return {
        "intent": "skill_lookup",
        "entities": ["Python", "FastAPI"],
        "metadata": {**state.metadata, "node": "query_understanding"}
    }
    # Pydantic validates these updates before merging
```

**Pattern 2: Full State Return** (Alternative)
```python
async def query_understanding_node(state: GraphRAGState) -> GraphRAGState:
    """Return updated full state object."""
    state.intent = "skill_lookup"
    state.entities = ["Python", "FastAPI"]
    state.metadata["node"] = "query_understanding"
    return state
    # Pydantic validates on each field assignment
```

**Error Handling in Nodes**:
```python
async def safe_node_wrapper(state: GraphRAGState) -> dict:
    """Wrapper to catch validation errors in node logic."""
    try:
        # Node logic that might have typos or type errors
        updates = {
            "intent": "skill_lookup",
            "entites": ["Python"]  # Typo: 'entites'
        }

        # Validate updates before returning
        temp_state = state.copy(update=updates)  # Pydantic validates here

        return updates

    except ValidationError as e:
        logger.error(f"State validation failed: {e}")
        return {
            "final_response": "Internal error: Invalid state update",
            "metadata": {"error": str(e), "node": "query_understanding"}
        }
```

**Testing Strategy**:

**Test 1: Typo Detection**
```python
# tests/agents/test_state_validation.py
import pytest
from pydantic import ValidationError
from app.agents.graph import GraphRAGState

def test_extra_fields_rejected():
    """Verify typos in field names are caught."""
    with pytest.raises(ValidationError) as exc_info:
        GraphRAGState(
            user_query="test",
            user_id="user-123",
            intnet="skill"  # Typo: should be 'intent'
        )

    assert "extra fields not permitted" in str(exc_info.value)
    assert "intnet" in str(exc_info.value)

def test_typo_in_assignment():
    """Verify typos in field assignment are caught."""
    state = GraphRAGState(user_query="test", user_id="user-123")

    with pytest.raises(AttributeError):
        state.intnet = "skill"  # Typo: no such attribute
```

**Test 2: Type Validation**
```python
def test_type_mismatches_rejected():
    """Verify wrong types are caught immediately."""
    # Test 1: entities must be list
    with pytest.raises(ValidationError) as exc_info:
        GraphRAGState(
            user_query="test",
            user_id="user-123",
            entities="should be list"  # Wrong type!
        )

    assert "value is not a valid list" in str(exc_info.value)

    # Test 2: vector_results must be list of dicts
    with pytest.raises(ValidationError):
        GraphRAGState(
            user_query="test",
            user_id="user-123",
            vector_results=["wrong", "type"]  # Should be list of dicts
        )
```

**Test 3: Intent Validation**
```python
def test_intent_validation():
    """Verify custom intent validator works."""
    valid_intents = ["skill_lookup", "job_search", "comparison", "explanation", "general"]

    # Valid intents should work
    for intent in valid_intents:
        state = GraphRAGState(user_query="test", user_id="user-123", intent=intent)
        assert state.intent == intent

    # Invalid intent should fail
    with pytest.raises(ValidationError) as exc_info:
        GraphRAGState(user_query="test", user_id="user-123", intent="invalid")

    assert "Invalid intent" in str(exc_info.value)
    assert valid_intents[0] in str(exc_info.value)  # Shows valid options
```

**Test 4: Required Fields**
```python
def test_required_fields_enforced():
    """Verify required fields cannot be omitted."""
    # Missing user_query
    with pytest.raises(ValidationError) as exc_info:
        GraphRAGState(user_id="user-123")

    assert "user_query" in str(exc_info.value)
    assert "field required" in str(exc_info.value).lower()

    # Missing user_id
    with pytest.raises(ValidationError):
        GraphRAGState(user_query="test")
```

**Test 5: Empty Query Validation**
```python
def test_empty_query_rejected():
    """Verify user_query cannot be empty or whitespace."""
    # Empty string
    with pytest.raises(ValidationError) as exc_info:
        GraphRAGState(user_query="", user_id="user-123")

    assert "at least 1 characters" in str(exc_info.value).lower()

    # Whitespace only
    with pytest.raises(ValidationError):
        GraphRAGState(user_query="   ", user_id="user-123")

    # Should be stripped and validated
```

**Test 6: Node Return Value Validation**
```python
@pytest.mark.asyncio
async def test_node_updates_validated():
    """Verify node return values are validated before merging."""
    state = GraphRAGState(user_query="test query", user_id="user-123")

    # Simulate node returning invalid update
    invalid_updates = {
        "intent": "invalid_intent",  # Will fail validator
        "entities": ["Python"]
    }

    with pytest.raises(ValidationError):
        # This would happen in LangGraph when merging updates
        updated_state = state.copy(update=invalid_updates)
```

**Migration Path from TypedDict**:

If you have existing code using TypedDict:

1. **Update imports**:
   ```python
   # Before
   from typing import TypedDict

   # After
   from pydantic import BaseModel, Field, validator
   ```

2. **Update class definition**:
   ```python
   # Before
   class GraphRAGState(TypedDict):
       user_query: str

   # After
   class GraphRAGState(BaseModel):
       user_query: str = Field(..., min_length=1)
       class Config:
           extra = "forbid"
   ```

3. **Update field access** (dict-style to attribute-style):
   ```python
   # Before (works with both)
   query = state["user_query"]

   # After (preferred with Pydantic)
   query = state.user_query
   ```

4. **Add validators** for business logic constraints:
   ```python
   @validator('intent')
   def validate_intent(cls, v):
       if v not in valid_intents:
           raise ValueError(f"Invalid intent: {v}")
       return v
   ```

**Summary**:
- ✅ Runtime type validation prevents silent failures
- ✅ Typo detection with `extra="forbid"` catches field name errors
- ✅ Custom validators enforce business logic constraints
- ✅ Clear error messages aid debugging
- ✅ Assignment validation with `validate_assignment=True`
- ✅ Comprehensive test coverage for validation logic

---

### **Node 1: Query Understanding**

**Purpose**: Parse user query to extract intent, entities, and query type.
**Module**: `app/agents/nodes/query_understanding.py`

**Logic**:
1. Use lightweight NLP to detect intent (skill_lookup, job_search, comparison, explanation)
2. Extract named entities (skill names, job titles, locations, companies)
3. Classify query complexity (simple, moderate, complex)
4. Set query parameters (k for vector search, depth for graph traversal)

**Example**:
```python
from pydantic import ValidationError
import re
from app.agents.graph import GraphRAGState

async def query_understanding_node(state: GraphRAGState) -> dict:
    """
    Analyze user query to extract intent and entities.

    Args:
        state: Type-safe GraphRAGState Pydantic model

    Returns:
        dict: Updates to apply to state (Pydantic will validate)

    Raises:
        ValidationError: If state updates violate schema constraints
    """
    user_query = state.user_query.lower()  # Type-safe field access

    # Intent detection (simple keyword-based for MVP)
    intent = "general"
    if any(kw in user_query for kw in ["what is", "explain", "tell me about"]):
        intent = "explanation"
    elif any(kw in user_query for kw in ["jobs", "openings", "positions"]):
        intent = "job_search"
    elif any(kw in user_query for kw in ["skills", "technologies", "tools"]):
        intent = "skill_lookup"
    elif any(kw in user_query for kw in ["compare", "difference", "vs"]):
        intent = "comparison"

    # Entity extraction (basic regex for MVP)
    entities = extract_entities(user_query)

    # Update state
    state["intent"] = intent
    state["entities"] = entities
    state["metadata"] = {
        "query_length": len(user_query),
        "intent_confidence": 0.8,  # Placeholder for future ML model
        "k_results": 10,  # Top-k for vector search
        "graph_depth": 2  # Traversal depth
    }

    return state

def extract_entities(query: str) -> List[str]:
    """Extract potential skill/job entities from query."""
    # Placeholder: Simple tokenization (replace with NER model in future)
    tokens = re.findall(r'\b[a-z]{3,}\b', query)
    return [t for t in tokens if t not in {"what", "the", "for", "with"}]
```

---

### **Node 2: Vector Search**

**Purpose**: Retrieve top-k most similar nodes from Neo4j using vector embeddings.
**Module**: `app/agents/nodes/vector_search.py`

**Logic**:
1. Generate embedding for user query using HuggingFace model
2. Perform vector similarity search in Neo4j (cosine similarity)
3. Retrieve top-k Skill and Job nodes
4. Return results with similarity scores

**Example**:
```python
from typing import Dict, Any, List
from app.repositories.neo4j_repository import Neo4jRepository
from app.services.embedding_service import EmbeddingService

async def vector_search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Perform vector similarity search in Neo4j."""
    user_query = state["user_query"]
    k = state["metadata"]["k_results"]

    # Generate query embedding
    embedding_service = EmbeddingService()
    query_embedding = await embedding_service.generate_embedding(user_query)

    # Search Neo4j
    neo4j_repo = Neo4jRepository()
    skill_results = await neo4j_repo.vector_search_skills(query_embedding, k=k)
    job_results = await neo4j_repo.vector_search_jobs(query_embedding, k=k//2)

    # Combine results
    state["vector_results"] = {
        "skills": skill_results,
        "jobs": job_results
    }

    return state
```

**Neo4j Cypher Query Example**:
```cypher
// Vector search for skills
CALL db.index.vector.queryNodes('skill_embedding_idx', $k, $query_embedding)
YIELD node, score
MATCH (node:Skill)
OPTIONAL MATCH (node)-[:BELONGS_TO_CATEGORY]->(cat:Category)
OPTIONAL MATCH (node)-[:BELONGS_TO_SUBCATEGORY]->(sub:Subcategory)
RETURN node.id AS skill_id, node.name AS skill_name,
       node.description AS description, score,
       cat.category_name AS category, sub.subcategory_name AS subcategory
ORDER BY score DESC
LIMIT $k
```

---

### **Node 3: Graph Traversal**

**Purpose**: Expand context by traversing relationships around retrieved nodes.
**Module**: `app/agents/nodes/graph_traversal.py`

**Logic**:
1. For each top-k result from vector search, traverse outgoing relationships
2. Retrieve connected nodes (Skills → Categories, Jobs → Skills, Jobs → Companies)
3. Apply depth limit (1-2 hops for MVP)
4. Return enriched context with relationship metadata

**Example**:
```python
from typing import Dict, Any, List

async def graph_traversal_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Traverse graph relationships to enrich context."""
    vector_results = state["vector_results"]
    depth = state["metadata"]["graph_depth"]

    neo4j_repo = Neo4jRepository()
    graph_context = []

    # Traverse from top skills
    for skill in vector_results["skills"][:5]:
        skill_context = await neo4j_repo.traverse_skill_context(
            skill_id=skill["skill_id"],
            depth=depth
        )
        graph_context.append(skill_context)

    # Traverse from top jobs
    for job in vector_results["jobs"][:3]:
        job_context = await neo4j_repo.traverse_job_context(
            job_id=job["job_id"],
            depth=depth
        )
        graph_context.append(job_context)

    state["graph_context"] = graph_context
    return state
```

**Neo4j Cypher Query Example**:
```cypher
// Traverse skill context
MATCH (s:Skill {id: $skill_id})
OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:Category)
OPTIONAL MATCH (s)-[:BELONGS_TO_SUBCATEGORY]->(sub:Subcategory)
OPTIONAL MATCH (s)-[:SIMILAR_TO]-(similar:Skill)
OPTIONAL MATCH (j:Job)-[req:REQUIRES]->(s)
RETURN s, cat, sub, collect(distinct similar)[0..5] as related_skills,
       collect(distinct {job: j, similarity: req.similarity_score})[0..3] as requiring_jobs
```

---

### **Node 4: Context Construction**

**Purpose**: Merge vector search results + graph context into LLM-optimized text.
**Module**: `app/agents/nodes/context_construction.py`

**Logic**:
1. Format vector search results as structured text
2. Merge graph traversal relationships
3. Apply token limits (max 3000 tokens for context)
4. Structure context with clear sections

**Example**:
```python
from typing import Dict, Any

async def context_construction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Construct LLM context from vector + graph results."""
    vector_results = state["vector_results"]
    graph_context = state["graph_context"]

    context_parts = []

    # Section 1: Top matching skills
    context_parts.append("## Relevant Skills\n")
    for skill in vector_results["skills"][:5]:
        context_parts.append(
            f"- **{skill['skill_name']}** (Match: {skill['score']:.2f})\n"
            f"  Category: {skill['category']}, Subcategory: {skill['subcategory']}\n"
            f"  Description: {skill['description'][:200]}...\n"
        )

    # Section 2: Related jobs
    context_parts.append("\n## Related Job Postings\n")
    for job in vector_results["jobs"][:3]:
        context_parts.append(
            f"- **{job['job_title']}** at {job['company_name']}\n"
            f"  Location: {job['location']}, Salary: {job['salary']}\n"
            f"  Description: {job['description'][:200]}...\n"
        )

    # Section 3: Graph relationships
    context_parts.append("\n## Connections & Relationships\n")
    for ctx in graph_context[:3]:
        context_parts.append(format_graph_context(ctx))

    constructed_context = "\n".join(context_parts)

    # Apply token limit (rough estimate: 4 chars = 1 token)
    if len(constructed_context) > 12000:  # ~3000 tokens
        constructed_context = constructed_context[:12000] + "\n... (context truncated)"

    state["constructed_context"] = constructed_context
    return state

def format_graph_context(ctx: Dict[str, Any]) -> str:
    """Format graph traversal results into readable text."""
    # Implementation depends on graph structure returned
    return f"Context: {ctx}\n"
```

---

### **Node 5: Response Generation**

**Purpose**: Generate final conversational response using OpenRouter LLM.
**Module**: `app/agents/nodes/response_generation.py`

**Logic**:
1. Build prompt with system instructions + constructed context + user query
2. Call OpenRouter API (meta-llama/llama-3.3-8b-instruct:free)
3. Parse LLM response
4. Return structured response with citations

**Example**:
```python
from typing import Dict, Any
from app.services.openrouter_service import OpenRouterService

async def response_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate final response using OpenRouter LLM."""
    user_query = state["user_query"]
    context = state["constructed_context"]

    # Build prompt
    system_prompt = (
        "You are a helpful AI assistant specialized in skills and job market analysis. "
        "Use the provided context to answer the user's question accurately and concisely. "
        "If the context doesn't contain enough information, say so clearly."
    )

    user_prompt = f"""Context:
{context}

User Question: {user_query}

Please provide a helpful, accurate answer based on the context above."""

    # Call OpenRouter
    openrouter_service = OpenRouterService()
    llm_response = await openrouter_service.generate_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=500,
        temperature=0.7
    )

    state["final_response"] = llm_response["text"]
    state["metadata"]["tokens_used"] = llm_response["usage"]["total_tokens"]
    state["metadata"]["model"] = "meta-llama/llama-3.3-8b-instruct:free"

    return state
```

---

## 5.3 Service Layer

The service layer contains business logic and orchestrates repository operations.

### **AuthService**

**Module**: `app/services/auth_service.py`

**Responsibilities**:
- User registration with password hashing (bcrypt)
- User login with JWT token generation
- Token validation and decoding

**Key Methods**:
```python
class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, user_data: UserCreate) -> UserResponse:
        """Register new user with hashed password."""
        # Check if user exists
        # Hash password with bcrypt
        # Create user in PostgreSQL
        # Return UserResponse
        pass

    async def login_user(self, credentials: UserLogin) -> TokenResponse:
        """Authenticate user and return JWT token."""
        # Verify credentials
        # Generate JWT with 24h expiry
        # Return TokenResponse
        pass

    async def verify_token(self, token: str) -> str:
        """Decode JWT and return user_id."""
        # Decode JWT
        # Validate expiry
        # Return user_id
        pass
```

---

### **IngestionService**

**Module**: `app/services/ingestion_service.py`

**Responsibilities**:
- CSV file validation and parsing
- Batch processing with progress tracking
- Neo4j graph creation
- PostgreSQL job tracking

**Key Methods**:
```python
class IngestionService:
    def __init__(
        self,
        neo4j_repo: Neo4jRepository,
        ingestion_repo: IngestionJobRepository,
        embedding_service: EmbeddingService
    ):
        self.neo4j_repo = neo4j_repo
        self.ingestion_repo = ingestion_repo
        self.embedding_service = embedding_service

    async def start_skills_ingestion(
        self, file: UploadFile, user_id: str
    ) -> IngestionJobResponse:
        """Start skills CSV ingestion job."""
        # Validate CSV format
        # Create IngestionJob in PostgreSQL
        # Process in batches (1000 rows)
        # Generate embeddings
        # Create Skill nodes + relationships in Neo4j
        # Update job progress
        pass

    async def start_jobs_ingestion(
        self, file: UploadFile, user_id: str
    ) -> IngestionJobResponse:
        """Start jobs CSV ingestion job."""
        # Similar to skills ingestion
        # Parse skill associations
        # Create Job, Company, Location nodes
        # Create REQUIRES relationships with similarity scores
        pass

    async def get_job_status(
        self, job_id: str, user_id: str
    ) -> IngestionStatusResponse:
        """Get ingestion job status and progress."""
        # Query IngestionJob from PostgreSQL
        # Return status, progress, batch info
        pass
```

---

### **LangGraphService**

**Module**: `app/services/langgraph_service.py`

**Responsibilities**:
- Execute RAG workflow via LangGraph StateGraph
- Log query history to PostgreSQL
- Return structured response

**Key Methods**:
```python
class LangGraphService:
    def __init__(
        self,
        query_repo: QueryHistoryRepository,
        rag_workflow: StateGraph
    ):
        self.query_repo = query_repo
        self.rag_workflow = rag_workflow

    async def execute_query(
        self, query_data: QueryRequest, user_id: str
    ) -> QueryResponse:
        """Execute RAG workflow and return response."""
        # Initialize state
        initial_state = {
            "user_query": query_data.query,
            "user_id": user_id,
            "metadata": {}
        }

        # Execute workflow
        final_state = await self.rag_workflow.ainvoke(initial_state)

        # Log to PostgreSQL
        await self.query_repo.create_query_history(
            user_id=user_id,
            query_text=query_data.query,
            response_text=final_state["final_response"],
            metadata=final_state["metadata"]
        )

        # Return response
        return QueryResponse(
            response=final_state["final_response"],
            metadata=final_state["metadata"]
        )
```

---

### **EmbeddingService**

**Module**: `app/services/embedding_service.py`

**Responsibilities**:
- Generate embeddings using HuggingFace Transformers
- Cache embeddings for performance (future enhancement)

**Key Methods**:
```python
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate 384-dimensional embedding for text."""
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        embeddings = self.model.encode(texts, convert_to_tensor=False, batch_size=32)
        return embeddings.tolist()
```

---

### **OpenRouterService**

**Module**: `app/services/openrouter_service.py`

**Responsibilities**:
- Call OpenRouter API for LLM completions
- Handle retries and rate limiting

**Key Methods**:
```python
import httpx
from typing import Dict, Any

class OpenRouterService:
    def __init__(self, api_key: str, model: str = "meta-llama/llama-3.3-8b-instruct:free"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Generate LLM completion via OpenRouter."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            response.raise_for_status()
            result = response.json()

            return {
                "text": result["choices"][0]["message"]["content"],
                "usage": result["usage"]
            }
```

---

## 5.4 Repository Layer

The repository layer handles direct database operations (PostgreSQL via Prisma, Neo4j via driver).

### **UserRepository**

**Module**: `app/repositories/user_repository.py`

**Responsibilities**: CRUD operations for User table in PostgreSQL

**Key Methods**:
```python
from prisma import Prisma
from prisma.models import User

class UserRepository:
    def __init__(self, prisma: Prisma):
        self.prisma = prisma

    async def create_user(self, email: str, password_hash: str) -> User:
        """Create new user in PostgreSQL."""
        return await self.prisma.user.create(
            data={"email": email, "password_hash": password_hash}
        )

    async def get_user_by_email(self, email: str) -> User | None:
        """Find user by email."""
        return await self.prisma.user.find_unique(where={"email": email})

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Find user by ID."""
        return await self.prisma.user.find_unique(where={"id": user_id})
```

---

### **IngestionJobRepository**

**Module**: `app/repositories/ingestion_job_repository.py`

**Responsibilities**: Track CSV ingestion jobs in PostgreSQL

**Key Methods**:
```python
from prisma.models import IngestionJob

class IngestionJobRepository:
    def __init__(self, prisma: Prisma):
        self.prisma = prisma

    async def create_job(
        self, user_id: str, file_type: str, total_records: int
    ) -> IngestionJob:
        """Create new ingestion job."""
        return await self.prisma.ingestionjob.create(
            data={
                "user_id": user_id,
                "file_type": file_type,
                "status": "pending",
                "total_records": total_records
            }
        )

    async def update_progress(
        self, job_id: str, processed_records: int, status: str
    ) -> IngestionJob:
        """Update job progress."""
        return await self.prisma.ingestionjob.update(
            where={"id": job_id},
            data={"processed_records": processed_records, "status": status}
        )

    async def get_job(self, job_id: str) -> IngestionJob | None:
        """Get job by ID."""
        return await self.prisma.ingestionjob.find_unique(where={"id": job_id})
```

---

### **QueryHistoryRepository**

**Module**: `app/repositories/query_history_repository.py`

**Responsibilities**: Log query history in PostgreSQL

**Key Methods**:
```python
from prisma.models import QueryHistory
import json

class QueryHistoryRepository:
    def __init__(self, prisma: Prisma):
        self.prisma = prisma

    async def create_query_history(
        self, user_id: str, query_text: str, response_text: str, metadata: dict
    ) -> QueryHistory:
        """Log query to history."""
        return await self.prisma.queryhistory.create(
            data={
                "user_id": user_id,
                "query_text": query_text,
                "response_text": response_text,
                "metadata": json.dumps(metadata)
            }
        )

    async def get_user_history(self, user_id: str, limit: int = 20) -> list[QueryHistory]:
        """Get user's query history."""
        return await self.prisma.queryhistory.find_many(
            where={"user_id": user_id},
            order={"created_at": "desc"},
            take=limit
        )
```

---

### **Neo4jRepository**

**Module**: `app/repositories/neo4j_repository.py`

**Responsibilities**: Neo4j graph operations (CRUD, vector search, traversal)

**Key Methods**:
```python
from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any

class Neo4jRepository:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def create_skill_node(self, skill_data: dict) -> None:
        """Create Skill node in Neo4j."""
        async with self.driver.session() as session:
            await session.run(
                """
                CREATE (s:Skill {
                    id: $id, name: $name, level: $level, type: $type,
                    is_software: $is_software, is_language: $is_language,
                    description: $description, description_source: $description_source,
                    version: $version, latest_version: $latest_version,
                    wiki_link: $wiki_link, wiki_extract: $wiki_extract,
                    embedding: $embedding, created_at: datetime()
                })
                """,
                **skill_data
            )

    async def vector_search_skills(
        self, query_embedding: List[float], k: int = 10
    ) -> List[Dict[str, Any]]:
        """Vector similarity search for skills."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                CALL db.index.vector.queryNodes('skill_embedding_idx', $k, $query_embedding)
                YIELD node, score
                MATCH (node:Skill)
                OPTIONAL MATCH (node)-[:BELONGS_TO_CATEGORY]->(cat:Category)
                OPTIONAL MATCH (node)-[:BELONGS_TO_SUBCATEGORY]->(sub:Subcategory)
                RETURN node.id AS skill_id, node.name AS skill_name,
                       node.description AS description, score,
                       cat.category_name AS category, sub.subcategory_name AS subcategory
                ORDER BY score DESC
                """,
                k=k, query_embedding=query_embedding
            )
            return [dict(record) async for record in result]

    async def traverse_skill_context(
        self, skill_id: str, depth: int = 2
    ) -> Dict[str, Any]:
        """Traverse skill relationships."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Skill {id: $skill_id})
                OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:Category)
                OPTIONAL MATCH (s)-[:BELONGS_TO_SUBCATEGORY]->(sub:Subcategory)
                OPTIONAL MATCH (s)-[:SIMILAR_TO]-(similar:Skill)
                OPTIONAL MATCH (j:Job)-[req:REQUIRES]->(s)
                RETURN s, cat, sub,
                       collect(distinct similar)[0..5] as related_skills,
                       collect(distinct {job: j, similarity: req.similarity_score})[0..3] as requiring_jobs
                """,
                skill_id=skill_id
            )
            return dict(await result.single())
```

---

## 5.5 Middleware Components

### **CORS Middleware**

**Module**: `app/middleware/cors.py`

```python
from fastapi.middleware.cors import CORSMiddleware

def add_cors_middleware(app):
    """Add CORS middleware for frontend communication."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # React dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
```

---

### **Authentication Middleware**

**Module**: `app/middleware/auth.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import AuthService

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends()
) -> str:
    """Validate JWT and return user_id."""
    token = credentials.credentials
    try:
        user_id = await auth_service.verify_token(token)
        return user_id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
```

---

### **Error Handling Middleware**

**Module**: `app/middleware/error_handler.py`

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": exc.errors()
        }
    )

async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": str(exc)
        }
    )
```

---
