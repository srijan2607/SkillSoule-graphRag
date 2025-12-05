# REST API Spec

```yaml
openapi: 3.0.0
info:
  title: Career Intelligence AI System API
  version: 2.0.0
  description: |
    GraphRAG-based career intelligence platform with network metrics.
    v2.0 adds skill-centric graph model, eigenvector centrality, shortest-path closeness.

servers:
  - url: http://localhost:8000
    description: Local development server
  - url: https://api.career-intelligence.example.com
    description: Production API (future)

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    QueryRequest:
      type: object
      required: [query]
      properties:
        query:
          type: string
          example: "Which skills transfer to UX Designer?"
        session_id:
          type: string
          format: uuid
          example: "550e8400-e29b-41d4-a716-446655440000"
        include_metrics:
          type: boolean
          default: true
          description: Include network metrics in response (v2.0)

    QueryResponse:
      type: object
      properties:
        query:
          type: string
        response:
          type: string
        sources:
          type: array
          items:
            type: object
            properties:
              node_type:
                type: string
                enum: [Skill, Job, Company]
              node_id:
                type: string
              properties:
                type: object
        processing_time_ms:
          type: number
        metadata:
          type: object
          properties:
            intent:
              type: string
              enum: [skill_requirement, career_path, salary_analysis, skill_transfer, learning_path, transition_difficulty, skill_bridge, high_leverage]
            intent_confidence:
              type: number
            vector_results_count:
              type: integer
            graph_nodes_count:
              type: integer
            graph_relationships_count:
              type: integer
            metrics:
              type: object
              properties:
                transition_index:
                  type: number
                  minimum: 0
                  maximum: 1
                skill_closeness_map:
                  type: object
                  additionalProperties:
                    type: number
                centrality_values:
                  type: object
                  additionalProperties:
                    type: number

    CentralityResponse:
      type: object
      properties:
        skill_id:
          type: string
        skill_name:
          type: string
        eigenvector_centrality:
          type: number
          minimum: 0
          maximum: 1
        rank:
          type: integer
        market_demand:
          type: integer

    ClosenessRequest:
      type: object
      required: [skill_a, skill_b]
      properties:
        skill_a:
          type: string
          example: "Python"
        skill_b:
          type: string
          example: "Django"

    ClosenessResponse:
      type: object
      properties:
        skill_a:
          type: string
        skill_b:
          type: string
        distance:
          type: number
        closeness:
          type: number
          minimum: 0
          maximum: 1
        shortest_path:
          type: array
          items:
            type: string
          example: ["Python", "Web Development", "Django"]
        path_length:
          type: integer

paths:
  /auth/register:
    post:
      summary: Register new user
      tags: [Authentication]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email, password, full_name]
              properties:
                email:
                  type: string
                  format: email
                password:
                  type: string
                  minLength: 8
                full_name:
                  type: string
      responses:
        '201':
          description: User created successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  user_id:
                    type: string
                    format: uuid

  /auth/login:
    post:
      summary: User login
      tags: [Authentication]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email, password]
              properties:
                email:
                  type: string
                password:
                  type: string
      responses:
        '200':
          description: Login successful
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  token_type:
                    type: string
                    example: bearer

  /query:
    post:
      summary: Execute RAG query
      tags: [Query]
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/QueryRequest'
      responses:
        '200':
          description: Query executed successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/QueryResponse'
        '429':
          description: Rate limit exceeded (10 requests/min)

  /api/metrics/centrality:
    get:
      summary: Get skill centrality rankings (v2.0 NEW)
      tags: [Metrics]
      security:
        - BearerAuth: []
      parameters:
        - in: query
          name: skill_id
          schema:
            type: string
          description: Optional skill ID (returns specific skill centrality)
        - in: query
          name: top_n
          schema:
            type: integer
            default: 20
          description: Number of top skills to return (if skill_id not provided)
      responses:
        '200':
          description: Centrality data retrieved
          content:
            application/json:
              schema:
                oneOf:
                  - $ref: '#/components/schemas/CentralityResponse'
                  - type: array
                    items:
                      $ref: '#/components/schemas/CentralityResponse'

  /api/metrics/closeness:
    post:
      summary: Calculate skill-to-skill closeness (v2.0 NEW)
      tags: [Metrics]
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ClosenessRequest'
      responses:
        '200':
          description: Closeness calculated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ClosenessResponse'

  /ingest/skills:
    post:
      summary: Ingest skills CSV (v1.1, enhanced in v2.0)
      tags: [Ingestion]
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
      responses:
        '200':
          description: Skills ingested, centrality recalculation triggered
          content:
            application/json:
              schema:
                type: object
                properties:
                  skills_processed:
                    type: integer
                  centrality_recalculation_status:
                    type: string
                    enum: [queued, in_progress, completed]

  /health:
    get:
      summary: Health check
      tags: [Health]
      responses:
        '200':
          description: Service healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: healthy
                  neo4j_connected:
                    type: boolean
                  postgres_connected:
                    type: boolean
                  neo4j_gds_available:
                    type: boolean
```

---
