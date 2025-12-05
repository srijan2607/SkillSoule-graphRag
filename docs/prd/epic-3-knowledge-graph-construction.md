# Epic 3: Knowledge Graph Construction

**Epic Goal**: Transform ingested CSV data into a rich Neo4j knowledge graph with semantic embeddings, node relationships, and vector indexes. By the end of this epic, the system has a fully populated graph database with Job, Skill, Company, Location, Category, and Subcategory nodes, all relationships established, and vector indexes ready for similarity search.

## Story 3.1: Embedding Generation Service

**As a** system
**I want** to generate embeddings for text fields using Hugging Face model
**so that** I can perform semantic similarity search

### Acceptance Criteria

1. Embedding service created using `sentence-transformers` library with `all-MiniLM-L6-v2` model
2. Service loads model once on startup (singleton pattern)
3. Method `generate_embeddings(texts: List[str]) -> List[List[float]]` created
4. Batch processing: accepts 32-64 texts per call
5. Returns 384-dimensional embeddings (one vector per text)
6. Empty or None texts return zero vector [0.0] * 384
7. Embedding generation retries on failure (max 3 retries, exponential backoff: 1s, 2s, 4s)
8. Unit tests written (single text, batch texts, empty text, retry logic)

## Story 3.2: Skills Graph Construction

**As a** system
**I want** to create Skill, Category, and Subcategory nodes in Neo4j from skills CSV
**so that** the skills taxonomy is represented in the graph

### Acceptance Criteria

1. For each skill row: Generate embedding from DESCRIPTION field (primary) or WIKI_EXTRACT (secondary if DESCRIPTION empty)
2. Create `Skill` node with properties: ID, NAME, LEVEL, TYPE, IS_SOFTWARE, IS_LANGUAGE, DESCRIPTION, WIKI_LINK, WIKI_EXTRACT, embedding
3. Create `Category` node with properties: CATEGORY (ID), CATEGORY_NAME (upsert by CATEGORY ID)
4. Create `Subcategory` node with properties: SUBCATEGORY (ID), SUBCATEGORY_NAME (upsert by SUBCATEGORY ID)
5. Create relationship: `Skill -[BELONGS_TO_CATEGORY]-> Category`
6. Create relationship: `Skill -[BELONGS_TO_SUBCATEGORY]-> Subcategory`
7. Create relationship: `Category -[CONTAINS]-> Subcategory`
8. Use batch transactions (commit every 1000 nodes)
9. Node creation uses MERGE (upsert) to avoid duplicates on re-ingestion

## Story 3.3: Skill Similarity Relationships

**As a** system
**I want** to compute and store skill-to-skill similarity relationships
**so that** users can discover related skills

### Acceptance Criteria

1. For each Skill node: compute cosine similarity with all other Skill embeddings
2. Keep top 5 most similar skills with similarity > 0.7 threshold
3. Create relationship: `Skill -[SIMILAR_TO {similarity_score}]-> Skill`
4. Similarity score stored as relationship property (float 0.0-1.0)
5. Similarity computation batched (process 100 skills at a time to avoid memory issues)
6. Skip self-similarity (Skill should not link to itself)
7. Bidirectional relationships: If Skill A similar to Skill B, create both A->B and B->A
8. Progress logged: "Computing similarities for skills 1000/10523"

## Story 3.4: Jobs Graph Construction

**As a** system
**I want** to create Job, Company, and Location nodes from jobs CSV
**so that** job market data is represented in the graph

### Acceptance Criteria

1. For each job row: Generate embedding from Job Description field (primary) or Description (fallback if Job Description empty)
2. Create `Job` node with ALL 30 CSV fields as properties (Job Title, Salary, Posted At, Description, Job ID, CIN, NCO_Code_algo, Minimum Salary, Maximum Salary, Mean Salary, etc.)
3. Create `Company` node with properties: Company Name, CIN, CompanyIndustrialClassification, NIC codes, Company Description, company_embedding (upsert by Company Name)
4. Company embedding generated from Company Description field
5. Create `Location` node with properties: Location name, District (upsert by Location name)
6. Create relationship: `Job -[POSTED_BY]-> Company`
7. Create relationship: `Job -[LOCATED_IN]-> Location`
8. Use batch transactions (commit every 1000 nodes)
9. Handle missing fields gracefully (store as NULL in Neo4j)

## Story 3.5: Job-Skill Relationships

**As a** system
**I want** to link jobs to required skills using standardized_skills field
**so that** I can query which skills are needed for specific jobs

### Acceptance Criteria

1. Parse `standardized_skills` field from jobs CSV (comma-separated list or JSON array)
2. For each skill name in list: normalize (lowercase, trim whitespace)
3. Match against existing Skill nodes using: `WHERE toLower(s.NAME) = normalized_skill_name`
4. Create relationship: `Job -[REQUIRES {similarity_score}]-> Skill`
5. If `similarity_scores` field exists in CSV and aligns with standardized_skills (same length/order), store as relationship property
6. Log unmatched skills: "Skill 'Machine Lerning' from Job 12345 not found in Skills taxonomy"
7. For unmatched skills: Create orphan Skill node with only NAME property (no metadata, no embedding)
8. Orphan skills logged to separate table for data quality review
9. Batch relationship creation (commit every 1000 relationships)

## Story 3.6: Neo4j Vector Indexes

**As a** system
**I want** vector indexes created on embedding properties
**so that** similarity search queries are fast

### Acceptance Criteria

1. Create vector index on `Skill.embedding` with cosine similarity metric
2. Create vector index on `Job.embedding` with cosine similarity metric
3. Create vector index on `Company.embedding` with cosine similarity metric
4. Index creation query: `CREATE VECTOR INDEX skill_embedding_index FOR (s:Skill) ON (s.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}`
5. Indexes created during initial setup (before first ingestion) or on-demand if missing
6. Index status verification: Query `SHOW INDEXES` to confirm indexes exist
7. Document index names in README for reference

## Story 3.7: Incremental Update & Upsert Logic

**As a** system
**I want** to handle weekly CSV re-uploads without duplicating data
**so that** users can update the graph with new data

### Acceptance Criteria

1. Node creation uses MERGE instead of CREATE (upsert by unique ID: Job ID, Skill ID, Company Name)
2. On match: Update all node properties with new CSV values
3. Relationship handling: Delete existing relationships for updated nodes, create new ones from CSV
4. Example: If Job 123 previously required [Python, Java], new CSV says [Python, React], result is [Python, React]
5. Orphan relationship cleanup: Relationships to deleted nodes are automatically removed
6. Ingestion mode flag: "full" (delete all, recreate) vs "incremental" (upsert only)
7. Default mode: incremental (safer for production)
8. Full mode requires explicit confirmation to prevent accidental data loss

---
