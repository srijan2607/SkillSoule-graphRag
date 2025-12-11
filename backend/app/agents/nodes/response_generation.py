"""
Response Generation Node - Generates LLM response using constructed context.

Uses OpenRouter LLM API to generate natural language responses based on
knowledge graph context retrieved from previous nodes.
"""

from typing import Dict, Any
from app.agents.graph import GraphRAGState
from app.services.openrouter_service import OpenRouterService
from app.utils.logger import logger
from app.utils.metrics import QueryMetrics
from app.services.pipeline_monitoring_service import (
    get_pipeline_monitoring_service,
    StageStatus
)


# NEW: Conversational career advisor system prompt
SYSTEM_PROMPT = """You are a helpful career advisor with expertise in the Indian tech job market. You have access to a KNOWLEDGE GRAPH of real job postings, skills, and companies with relationship connections.

## YOUR ROLE:
Help users understand career opportunities, skill requirements, and market trends through friendly, conversational responses backed by GRAPH-BASED ANALYSIS.

## CRITICAL REQUIREMENT:
**ALWAYS mention graph traversal statistics** from the context provided:
- Number of nodes discovered (jobs/skills/companies)
- Number of relationships traversed (REQUIRES, SIMILAR_TO, etc.)
- Relationship types found (e.g., "50 REQUIRES relationships connecting jobs to skills")
- When Network Insights are present, EXPLICITLY reference them: "Based on analyzing 35 nodes and 58 relationships from the knowledge graph..."

## RESPONSE STRUCTURE:

### 1. DIRECT ANSWER (2-4 sentences)
Answer the user's question naturally and directly. Be conversational but informative.

### 2. KEY INSIGHTS (Bullet points)
Provide 3-5 actionable insights based on the data:
- Skills or roles mentioned frequently
- Salary ranges if available
- Companies hiring for these roles
- Career progression paths
- Learning recommendations

### 3. GRAPH INSIGHTS (REQUIRED if graph data present)
**You MUST include this section when graph relationship data is available:**
- "Graph analysis revealed [X] nodes across [Y] relationships"
- "Found [N] skill-requirement connections"
- "Discovered [N] similar skill relationships"
- "Traversed [N] career progression paths"
- **When Network Insights section is present in context:**
  - Reference skill bridge paths: "Skill path analysis shows Python → Data Analysis → Machine Learning"
  - Mention top skills by centrality: "Top skills by importance: Python (centrality: 0.92)"
  - Note similar job opportunities: "Found similar positions with 78% skill match"

### 3.5. TRANSITION ANALYSIS (For transition_path queries)
**When the user asks about career transitions (e.g., "How do I transition from X to Y?"):**
- Include the **Transition Index** score (percentage showing transition feasibility)
- Show **Skill Closeness** metric (how transferable current skills are)
- List **Skills to Develop** (gap between current and target skills)
- Mention **CO_OCCURS_WITH relationships** (skills that frequently appear together)
- Provide a **Learning Path** recommendation based on skill proximity
- Use emojis for transition assessments: 🟢 (easy), 🟡 (moderate), 🔴 (challenging)

Example for transition queries:
"Based on our graph analysis, transitioning from **Backend Developer to ML Engineer** has a **Transition Index of 62%** 🟡 (moderate effort).

**Your Transferable Skills:**
- Python (directly applicable)
- SQL (useful for data work)
- API development (helpful for ML deployment)

**Skills to Develop:**
📚 Machine Learning fundamentals → TensorFlow/PyTorch → Deep Learning → MLOps

Our graph found 24 CO_OCCURS_WITH relationships showing Python and TensorFlow frequently appear together in ML roles."

### 4. SUPPORTING DATA
Include specific examples or numbers to back up your insights:
- "Most positions (85%) require Python"
- "Typical salary range: ₹8-15 LPA"
- "Top companies: Google, Amazon, Microsoft, etc."
- **Graph statistics: "[X] nodes, [Y] relationships explored"**

### 5. NEXT STEPS (Optional)
Suggest what the user should focus on or explore next.

### 6. TECHNICAL DETAILS (Collapsible at end)
<details>
<summary>📊 Technical Details (click to expand)</summary>

- Query executed: [intent type]
- Graph traversal: [X nodes, Y relationships]
- Results found: [number of jobs/skills/companies]
- Confidence: [score if available]
</details>

## STYLE GUIDE:
✅ DO be friendly and conversational
✅ DO use natural language ("most jobs", "typically", "around")
✅ DO include specific numbers when helpful
✅ DO make recommendations based on data
✅ DO acknowledge limitations ("limited data", "based on current dataset")
✅ DO use emojis sparingly for emphasis (💡, 📈, 🎯)

❌ DON'T be overly technical unless asked
❌ DON'T show raw query execution details in main response
❌ DON'T use tables unless comparing multiple items
❌ DON'T make claims without data backing
❌ DON'T be too formal or robotic

## EXAMPLE RESPONSE:

Based on the job market data, **data science roles in India typically require 5-7 core skills**. Here's what you should focus on:

**Essential Skills:**
- Python is required by almost all positions (95%)
- SQL and data manipulation (pandas, NumPy) are must-haves
- Machine learning frameworks (TensorFlow or PyTorch)
- Data visualization tools (Matplotlib, Tableau)

**Competitive Edge:**
- Cloud platforms (AWS/Azure) - increasingly in demand
- Big data tools (Spark, Hadoop) for senior roles
- Deep learning expertise for specialized positions

**Salary Expectations:**
Entry-level positions typically offer ₹6-10 LPA, while experienced data scientists can expect ₹15-30 LPA depending on skills and company.

**Next Steps:**
Start with Python and SQL if you're new. If you have these, focus on a machine learning framework and build portfolio projects.

<details>
<summary>📊 Technical Details</summary>

- Analyzed 127 data science job postings
- Vector search completed in 45ms
- Query confidence: 94%
- Coverage: Indian tech market, last updated Q4 2024
</details>

You are a HELPFUL CAREER ADVISOR, not a data analyst. Prioritize clarity, actionability, and encouragement over precision.
"""


def _build_user_prompt(
    context: str, query: str, state_metadata: Dict[str, Any] = None
) -> str:
    """
    Build user prompt with context and query for conversational response.

    Args:
        context: Constructed context from knowledge graph
        query: Original user query
        state_metadata: State metadata for technical details and conversation history

    Returns:
        Formatted user prompt string optimized for conversational response
    """
    # Check for conversation history
    history_context = ""
    if state_metadata:
        history_context = state_metadata.get("history_context", "")

    # Build prompt with optional conversation history
    if history_context:
        prompt = f"""CONVERSATION HISTORY:
{history_context}

---

CURRENT CONTEXT (Knowledge Graph Data):
{context}

---

User's Current Question: {query}

IMPORTANT: This is a follow-up question in an ongoing conversation. Consider the conversation history above when crafting your response. If the user is asking a follow-up (e.g., "what about salaries?", "tell me more", "which companies?"), refer back to the previous discussion context.

Please provide a helpful, conversational response following your system prompt guidelines. Include specific data from the context above to support your insights."""
    else:
        prompt = f"""Here's the relevant information from our job market database:

{context}

---

User's Question: {query}

Please provide a helpful, conversational response following your system prompt guidelines. Include specific data from the context above to support your insights."""

    # Add technical metadata for the details section if available
    if state_metadata:
        intent_analysis = state_metadata.get("intent_analysis", {})
        if intent_analysis:
            primary_intent = intent_analysis.get("primary_intent", "unknown")
            primary_confidence = intent_analysis.get("primary_confidence", 0.0)

            prompt += f"""

For the technical details section, include:
- Query type: {primary_intent}
- Confidence: {primary_confidence:.0%}
"""

    return prompt


async def response_generation_node(state: GraphRAGState) -> Dict[str, Any]:
    """
    Generate LLM response using constructed context.

    Calls OpenRouter API with retry logic to generate natural language
    responses based on knowledge graph context.

    Args:
        state: Current graph state with constructed_context and user_query

    Returns:
        Dict with final_response and updated metadata
    """
    # Start timing
    metrics = state.metadata.get("metrics")
    if isinstance(metrics, QueryMetrics):
        metrics.start_timer("response_generation")

    # Get pipeline monitoring
    pipeline_monitor = get_pipeline_monitoring_service()
    session_id = state.metadata.get("session_id", "unknown")
    user_id = state.metadata.get("user_id", "unknown")

    # Emit stage started
    await pipeline_monitor.emit_response_generation(
        session_id=session_id,
        user_id=user_id,
        query=state.user_query,
        status=StageStatus.STARTED
    )

    try:
        user_query = state.user_query
        context = state.constructed_context or ""

        # CHECK FOR PIPELINE ERRORS - Don't generate response if pipeline failed
        pipeline_errors = []
        if state.metadata.get("intent_analysis_error"):
            pipeline_errors.append(f"Intent Analysis: {state.metadata['intent_analysis_error']}")
        if state.metadata.get("vector_search_error"):
            pipeline_errors.append(f"Vector Search: {state.metadata['vector_search_error']}")
        if state.metadata.get("graph_traversal_error"):
            pipeline_errors.append(f"Graph Traversal: {state.metadata['graph_traversal_error']}")
        if state.metadata.get("context_construction_error"):
            pipeline_errors.append(f"Context Construction: {state.metadata['context_construction_error']}")

        if pipeline_errors:
            error_details = "\n".join([f"  - {err}" for err in pipeline_errors])
            error_message = (
                "⚠️ PIPELINE ERROR DETECTED\n\n"
                "The query processing pipeline encountered errors in the following stages:\n\n"
                f"{error_details}\n\n"
                "❌ Unable to generate response due to pipeline failures.\n\n"
                "🔧 DEBUG INSTRUCTIONS:\n"
                "1. Check server logs: tail -100 server.log\n"
                "2. Copy the error details above\n"
                "3. Paste them to your AI agent to diagnose and fix the issue\n\n"
                "The system will not attempt to generate a fallback response when the pipeline fails."
            )

            logger.error(f"[ResponseGeneration] Pipeline errors detected, refusing to generate response: {pipeline_errors}")

            # End timing
            duration_ms = 0.0
            if isinstance(metrics, QueryMetrics):
                duration_ms = metrics.end_timer("response_generation")

            # Emit stage failed
            await pipeline_monitor.emit_response_generation(
                session_id=session_id,
                user_id=user_id,
                query=state.user_query,
                status=StageStatus.FAILED,
                duration_ms=duration_ms,
                error="Pipeline stage failures detected"
            )

            return {
                "final_response": error_message,
                "metadata": {
                    **state.metadata,
                    "response_generation_skipped": True,
                    "pipeline_errors_detected": pipeline_errors,
                },
            }

        logger.info(
            f"[ResponseGeneration] Generating response for query: {user_query[:50]}..."
        )
        logger.info(
            f"[ResponseGeneration] Context length: {len(context)} chars"
        )

        # Build prompts (include state metadata for intent analysis)
        system_prompt = SYSTEM_PROMPT
        user_prompt = _build_user_prompt(context, user_query, state.metadata)

        logger.info(
            f"[ResponseGeneration] Prompt lengths - system: {len(system_prompt)}, "
            f"user: {len(user_prompt)}"
        )

        # Initialize OpenRouter service
        openrouter_service = OpenRouterService()

        # Call LLM with retry logic (built into service)
        # LOW temperature (0.3) for factual, precise, query-driven responses
        # High max_tokens (1200) for comprehensive structured analysis with metadata
        try:
            result = await openrouter_service.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=1200,  # Allow detailed structured analysis with tables
                temperature=0.3,  # REDUCED for factual precision over creativity
                max_retries=3,
            )

            final_response = result["text"]

            logger.info(
                f"[ResponseGeneration] Response generated successfully: "
                f"length={len(final_response)} chars, "
                f"tokens_used={result['usage']['total_tokens']}, "
                f"latency_ms={result['latency_ms']}, "
                f"retry_count={result['retry_count']}"
            )

            # End timing
            duration_ms = 0.0
            if isinstance(metrics, QueryMetrics):
                duration_ms = metrics.end_timer("response_generation")
                logger.info(f"[ResponseGeneration] Completed in {duration_ms:.2f}ms")

            # Emit stage completed
            await pipeline_monitor.emit_response_generation(
                session_id=session_id,
                user_id=user_id,
                query=state.user_query,
                status=StageStatus.COMPLETED,
                duration_ms=duration_ms,
                llm_model=result["model"],
                tokens_used=result["usage"]["total_tokens"],
                response_length=len(final_response)
            )

            return {
                "final_response": final_response,
                "metadata": {
                    **state.metadata,
                    "response_generation_completed": True,
                    "response_length": len(final_response),
                    "llm_model": result["model"],
                    "llm_tokens_used": result["usage"]["total_tokens"],
                    "llm_prompt_tokens": result["usage"]["prompt_tokens"],
                    "llm_completion_tokens": result["usage"]["completion_tokens"],
                    "llm_latency_ms": result["latency_ms"],
                    "llm_retry_count": result["retry_count"],
                },
            }

        except Exception as llm_error:
            # All retries failed - provide detailed error message
            logger.error(
                f"[ResponseGeneration] LLM generation failed after all retries: {llm_error}",
                exc_info=True
            )

            error_message = (
                "⚠️ LLM GENERATION ERROR\n\n"
                "The response generation stage failed after multiple retry attempts.\n\n"
                f"Error Details: {str(llm_error)}\n\n"
                "❌ Unable to generate response due to LLM API failure.\n\n"
                "🔧 DEBUG INSTRUCTIONS:\n"
                "1. Check server logs: tail -100 server.log | grep -A 20 'ResponseGeneration'\n"
                "2. Verify OpenRouter API key and credits\n"
                "3. Copy the error details above\n"
                "4. Paste them to your AI agent to diagnose and fix the issue\n\n"
                "Common causes:\n"
                "  - OpenRouter API rate limits or quota exceeded\n"
                "  - Network connectivity issues\n"
                "  - Invalid API key or configuration\n"
                "  - Model unavailability or timeout"
            )

            # End timing even on LLM error
            duration_ms = 0.0
            if isinstance(metrics, QueryMetrics):
                duration_ms = metrics.end_timer("response_generation")

            # Emit stage failed
            await pipeline_monitor.emit_response_generation(
                session_id=session_id,
                user_id=user_id,
                query=state.user_query,
                status=StageStatus.FAILED,
                duration_ms=duration_ms,
                error=str(llm_error)
            )

            return {
                "final_response": error_message,
                "metadata": {
                    **state.metadata,
                    "response_generation_error": str(llm_error),
                    "response_generation_failed": True,
                },
            }

    except Exception as e:
        logger.error(f"[ResponseGeneration] Unexpected error: {str(e)}", exc_info=True)

        error_message = (
            "⚠️ UNEXPECTED ERROR IN RESPONSE GENERATION\n\n"
            "An unexpected error occurred during response generation.\n\n"
            f"Error Details: {str(e)}\n\n"
            "❌ Unable to generate response due to internal error.\n\n"
            "🔧 DEBUG INSTRUCTIONS:\n"
            "1. Check server logs: tail -100 server.log | grep -A 30 'Traceback'\n"
            "2. Copy the full error traceback\n"
            "3. Paste it to your AI agent to diagnose and fix the issue\n\n"
            "This is a critical error that requires immediate attention."
        )

        # End timing even on unexpected error
        duration_ms = 0.0
        if isinstance(metrics, QueryMetrics):
            duration_ms = metrics.end_timer("response_generation")

        # Emit stage failed
        await pipeline_monitor.emit_response_generation(
            session_id=session_id,
            user_id=user_id,
            query=state.user_query,
            status=StageStatus.FAILED,
            duration_ms=duration_ms,
            error=str(e)
        )

        return {
            "final_response": error_message,
            "metadata": {
                **state.metadata,
                "response_generation_error": str(e),
                "response_generation_failed": True,
            },
        }
