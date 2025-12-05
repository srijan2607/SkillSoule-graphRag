# Data Models

## Skill (Primary Node - Skill-Centric Model)

**Purpose:** Represent individual skills (programming languages, frameworks, soft skills, tools) as primary infrastructure nodes in the career graph. Skills are the fundamental building blocks; jobs are combinations of required skills.

**Key Attributes:**
- `skill_id`: String (UUID) - Unique identifier
- `name`: String - Skill name (e.g., "Python", "Django", "Communication")
- `description`: String - Detailed description of skill
- `category`: String - High-level category (e.g., "Programming Language", "Framework", "Soft Skill")
- `subcategory`: String - Optional granular classification
- `level`: String - Skill complexity level (BEGINNER | INTERMEDIATE | ADVANCED | EXPERT)
- `embedding`: List[Float] (768-dim) - Vector representation for semantic search
- `eigenvector_centrality`: Float (0-1) - **NEW v2.0:** Importance score based on connections to other important skills (FR31)
- `market_demand`: Integer - **NEW v2.0:** Number of jobs requiring this skill (FR29)
- `avg_salary_impact`: Float - **NEW v2.0:** Average salary premium for this skill (FR29)

**Relationships:**
- `(Skill)-[:REQUIRES]->(Skill)` - Prerequisite relationship (HTML → React)
- `(Skill)-[:PREREQUISITE_OF]->(Skill)` - **NEW v2.0:** Inverse of REQUIRES, explicit prerequisite order (FR30)
- `(Skill)-[:COMPLEMENTS]->(Skill)` - **NEW v2.0:** Co-occurring skills (Python ↔ PostgreSQL) (FR30)
- `(Skill)-[:SUBSTITUTES]->(Skill)` - **NEW v2.0:** Competing alternatives (Django ↔ Flask) (FR30)
- `(Skill)-[:TRANSITIONS_TO]->(Skill)` - **NEW v2.0:** Common career transition paths (FR30, FR37)
- `(Skill)-[:SIMILAR_TO]->(Skill)` - Semantic similarity (top 5, cosine >0.7) [v1.1 preserved]
- `(Skill)-[:BELONGS_TO_CATEGORY]->(Category)` - Category classification [v1.1 preserved]

**Design Decision:**
- Centrality stored as property (not computed per-query) for <200ms TransitionIndex calculation (NFR13)
- Embedding dimension increased to 768 for better career domain coverage (FR47)

## Job (Derived Cluster - Skill Combination)

**Purpose:** Represent job postings as combinations of required skills. Jobs are no longer primary nodes but clusters defined by their skill requirements.

**Key Attributes:**
- `job_id`: String (UUID) - Unique identifier [v1.1 preserved]
- `job_title`: String - Job title (e.g., "Backend Developer", "UX Designer") [v1.1 preserved]
- `company_name`: String - Hiring company [v1.1 preserved]
- `salary_min`: Integer - Minimum salary (INR) [v1.1 preserved]
- `salary_max`: Integer - Maximum salary (INR) [v1.1 preserved]
- `location`: String - Job location [v1.1 preserved]
- `description`: String - Job description text [v1.1 preserved]
- `embedding`: List[Float] (768-dim) - Vector representation [v1.1 preserved, upgraded to 768-dim]
- `creation_index`: Float (0-1) - **NEW v2.0:** Novel skill combination score (FR36)
- `reuse_index`: Float (0-1) - **NEW v2.0:** Established skill combination score (FR36)
- `classification`: String - **NEW v2.0:** CUTTING_EDGE | EMERGING | ESTABLISHED (FR36)

**Relationships:**
- `(Job)-[:REQUIRES]->(Skill)` - Required skills for job [v1.1 preserved]
- `(Job)-[:POSTED_BY]->(Company)` - Hiring company [v1.1 preserved]
- `(Job)-[:LOCATED_IN]->(Location)` - Job location [v1.1 preserved]

**Design Decision:**
- Recombinant innovation indices (creation_index, reuse_index) classify jobs by novelty of skill combinations
- Hypothesis: CUTTING_EDGE jobs correlate with salary premium (to be validated in Epic 4)

## Company

**Purpose:** Represent hiring companies for job posting attribution.

**Key Attributes:**
- `company_name`: String (Primary Key) - Company name [v1.1 preserved]
- `industry`: String - Industry classification (optional) [v1.1 preserved]
- `embedding`: List[Float] (768-dim) - Vector representation [v1.1 preserved, upgraded to 768-dim]

**Relationships:**
- `(Company)<-[:POSTED_BY]-(Job)` - Jobs posted by company [v1.1 preserved]

## Category / Subcategory

**Purpose:** Hierarchical classification of skills for taxonomy navigation.

**Key Attributes:**
- `category_id`: String - Category identifier [v1.1 preserved]
- `name`: String - Category name (e.g., "Programming Languages", "Frameworks") [v1.1 preserved]

**Relationships:**
- `(Category)<-[:BELONGS_TO_CATEGORY]-(Skill)` - Skill categorization [v1.1 preserved]
- `(Subcategory)<-[:BELONGS_TO_SUBCATEGORY]-(Skill)` - Granular classification [v1.1 preserved]

## User (PostgreSQL)

**Purpose:** User account management for authentication and query history.

**Key Attributes:**
- `id`: UUID (Primary Key) - User identifier [v1.1 preserved]
- `email`: String (Unique) - User email [v1.1 preserved]
- `password_hash`: String - Bcrypt hashed password [v1.1 preserved]
- `full_name`: String - User's full name [v1.1 preserved]
- `created_at`: Timestamp - Account creation timestamp [v1.1 preserved]

**Relationships (PostgreSQL Foreign Keys):**
- `User` (1) → (N) `QueryHistory` - User's query history [v1.1 preserved]

## QueryHistory (PostgreSQL)

**Purpose:** Log user queries and responses for conversation context and analytics.

**Key Attributes:**
- `id`: UUID (Primary Key) - Query record identifier [v1.1 preserved]
- `user_id`: UUID (Foreign Key → User) - User who submitted query [v1.1 preserved]
- `session_id`: UUID - Conversation session identifier [v1.1 preserved]
- `query_text`: String - User's query [v1.1 preserved]
- `response_text`: String - System's response [v1.1 preserved]
- `metadata`: JSON - Intent, sources, processing time, **NEW: metric values** [v1.1 + v2.0 extension]
- `created_at`: Timestamp - Query timestamp [v1.1 preserved]

**Design Decision:**
- `metadata` JSON field extended in v2.0 to include centrality values, closeness scores, TransitionIndex breakdown
- Enables research validation analysis (correlation checks in Epic 4)

## Network Metrics (Computed, Not Stored as Entities)

**TransitionIndex:**
- **Formula:** `0.50 * AvgCloseness + 0.30 * CoreSkillOverlap + 0.20 * MarketDemand` (FR35)
- **Range:** [0, 1]
- **Interpretation:** >0.7 = High feasibility, 0.4-0.7 = Moderate, <0.4 = Major pivot
- **Computed:** Per-query, not stored (too dynamic)

**Closeness:**
- **Formula:** `Closeness(A, B) = 1 / (1 + Distance(A, B))` where Distance = shortest path via Dijkstra (FR33)
- **Range:** [0, 1] where 1 = direct connection, 0 = very distant/no path
- **Computed:** On-demand or cached for common skill pairs

**User-to-Job Closeness:**
- **Formula:** `JobCloseness = (1/m) * Σ closeness_j` where m = number of required skills (FR34)
- **Enhancement:** Weight core skills 2.0x in average
- **Use Case:** Rank jobs by transition feasibility from user's current skill set

---
