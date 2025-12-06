"""
Context Construction Node - Combines vector and graph results into structured LLM context.
"""
from typing import Dict, Any, List
from app.agents.graph import GraphRAGState
from app.utils.logger import logger
from app.utils.token_counter import count_tokens
from app.utils.metrics import QueryMetrics
from app.services.pipeline_monitoring_service import (
    get_pipeline_monitoring_service,
    StageStatus
)


async def context_construction_node(state: GraphRAGState) -> Dict[str, Any]:
    """
    Construct context string for LLM from vector and graph results.

    Formats context with sections:
    - User Query: Original question
    - Top Matching Nodes: Vector search results with scores
    - Related Information: Graph traversal results
    - Graph Structure: Key relationship insights

    Args:
        state: Current graph state with vector_results, graph_context, user_query

    Returns:
        Dict with constructed_context field
    """
    # Start timing
    metrics = state.metadata.get("metrics")
    if isinstance(metrics, QueryMetrics):
        metrics.start_timer("context_construction")

    # Get pipeline monitoring
    pipeline_monitor = get_pipeline_monitoring_service()
    session_id = state.metadata.get("session_id", "unknown")
    user_id = state.metadata.get("user_id", "unknown")

    # Emit stage started
    await pipeline_monitor.emit_context_construction(
        session_id=session_id,
        user_id=user_id,
        query=state.user_query,
        status=StageStatus.STARTED
    )

    try:
        # Extract data from state
        user_query = state.user_query
        vector_results = state.vector_results or []
        graph_context = state.graph_context or []
        # Support both multi-intent (new) and single-intent (backward compatibility)
        intents = state.intents or [state.intent] if state.intent else ["general"]
        entities = state.entities or []

        logger.info(
            f"[ContextConstruction] Building multi-intent context: "
            f"query='{user_query[:50]}...', "
            f"intents={intents}, "
            f"vector_results={len(vector_results)}, "
            f"graph_nodes={len(graph_context)}"
        )

        # Build context sections
        sections = []

        # Section 0: GRAPH STATISTICS HEADER (if graph traversal occurred)
        if graph_context and len(graph_context) > 0:
            sections.append(_format_graph_statistics_header(graph_context, vector_results))

        # Section 1: User Query (with ALL detected intents)
        sections.append(_format_user_query_section(user_query, intents, entities))

        # Section 2: Top Matching Nodes (vector results)
        if vector_results:
            sections.append(_format_top_matching_nodes_section(vector_results))

        # Section 3: Related Information (graph context)
        if graph_context:
            sections.append(_format_related_information_section(graph_context))

        # Section 4: Skill Gap Analysis (if career_path + skill_requirement detected)
        if "career_path" in intents and "skill_requirement" in intents:
            skill_gap_section = _format_skill_gap_analysis(vector_results, graph_context, entities)
            if skill_gap_section:
                sections.append(skill_gap_section)

        # Section 5: Transition Path Analysis (Phase 4 - if transition_path intent detected)
        if "transition_path" in intents:
            transition_section = _format_transition_context(state, vector_results, graph_context, entities)
            if transition_section:
                sections.append(transition_section)

        # Section 6: Graph Structure (insights)
        if graph_context or vector_results:
            sections.append(_format_graph_structure_section(graph_context, vector_results, intents))

        # Combine sections
        full_context = "\n\n".join(sections)

        # Token counting (no truncation - let LLM handle context window naturally)
        token_count = count_tokens(full_context)
        was_truncated = False  # No longer truncating contexts

        logger.info(
            f"[ContextConstruction] Context constructed: "
            f"{token_count} tokens, {len(full_context)} chars (no truncation applied)"
        )

        # End timing
        duration_ms = 0.0
        if isinstance(metrics, QueryMetrics):
            duration_ms = metrics.end_timer("context_construction")
            logger.info(f"[ContextConstruction] Completed in {duration_ms:.2f}ms")

        # Emit stage completed
        await pipeline_monitor.emit_context_construction(
            session_id=session_id,
            user_id=user_id,
            query=state.user_query,
            status=StageStatus.COMPLETED,
            duration_ms=duration_ms,
            tokens_used=token_count,
            context_length=len(full_context),
            truncated=was_truncated
        )

        return {
            "constructed_context": full_context,
            "metadata": {
                **state.metadata,
                "context_construction_completed": True,
                "context_token_count": token_count,
                "context_char_count": len(full_context),
                "context_truncated": was_truncated,
                "vector_results_count": len(vector_results),
                "graph_nodes_count": len(graph_context),
            },
        }

    except Exception as e:
        logger.error(f"[ContextConstruction] Failed: {str(e)}", exc_info=True)

        # End timing even on error
        duration_ms = 0.0
        if isinstance(metrics, QueryMetrics):
            duration_ms = metrics.end_timer("context_construction")

        # Emit stage failed
        await pipeline_monitor.emit_context_construction(
            session_id=session_id,
            user_id=user_id,
            query=state.user_query,
            status=StageStatus.FAILED,
            duration_ms=duration_ms,
            error=str(e)
        )

        return {
            "constructed_context": f"## User Query\n{state.user_query}\n\n*Error constructing context*",
            "metadata": {**state.metadata, "context_construction_error": str(e)},
        }


def _format_graph_statistics_header(
    graph_context: List[Dict[str, Any]], vector_results: List[Dict[str, Any]]
) -> str:
    """
    Format prominent graph statistics header - FIRST thing LLM sees.

    This ensures the LLM always knows graph traversal was performed.
    """
    # Separate nodes and relationships
    nodes = [item for item in graph_context if item.get("node_type")]
    relationships = [item for item in graph_context if item.get("type") and not item.get("node_type")]

    # Count relationship types
    rel_types = {}
    for rel in relationships:
        rel_type = rel.get("type", "UNKNOWN")
        rel_types[rel_type] = rel_types.get(rel_type, 0) + 1

    # Safety check for vector_results
    vector_count = len(vector_results) if vector_results else 0

    # Format header
    header = [
        "=" * 70,
        "🔍 KNOWLEDGE GRAPH ANALYSIS RESULTS",
        "=" * 70,
        "",
        f"**Vector Search:** {vector_count} initial matches found",
        f"**Graph Traversal:** Explored {len(nodes)} nodes and {len(relationships)} relationships",
        ""
    ]

    if rel_types:
        header.append("**Relationship Types Discovered:**")
        for rel_type, count in sorted(rel_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            natural_name = rel_type.replace("_", " ").title()
            header.append(f"  • {count}× {natural_name}")
        header.append("")

    header.extend([
        "⚠️  IMPORTANT: You MUST reference these graph statistics in your response.",
        "=" * 70,
        ""
    ])

    return "\n".join(header)


def _format_user_query_section(
    user_query: str, intents: List[str], entities: List[Dict[str, Any]]
) -> str:
    """Format User Query section with natural language context."""
    section = ["## User's Question", user_query]

    # Describe what the user is looking for naturally
    if intents and not all(i == "general" for i in intents):
        relevant_intents = [i for i in intents if i != "general"]
        if relevant_intents:
            # Create natural description of what user wants
            intent_descriptions = {
                "skill_requirement": "exploring skill requirements",
                "career_path": "planning career transition",
                "salary_analysis": "researching salary expectations",
                "company_query": "finding companies and opportunities",
                "skill_relationship": "comparing related skills",
                "transition_path": "analyzing career transition path"
            }

            descriptions = [intent_descriptions.get(i, i.replace("_", " ")) for i in relevant_intents]
            if len(descriptions) == 1:
                section.append(f"\n**Focus Area:** {descriptions[0].capitalize()}")
            else:
                section.append(f"\n**Focus Areas:** {', '.join(descriptions).capitalize()}")

    # Extract key entities mentioned (skills, roles, companies)
    if entities:
        skills = [e["value"] for e in entities if e.get("type") == "skill"]
        companies = [e["value"] for e in entities if e.get("type") == "company"]
        roles = [e["value"] for e in entities if e.get("type") in ["role", "job"]]

        if skills:
            section.append(f"**Skills Mentioned:** {', '.join(skills[:5])}")
        if roles:
            section.append(f"**Roles of Interest:** {', '.join(roles[:3])}")
        if companies:
            section.append(f"**Companies Mentioned:** {', '.join(companies[:3])}")

    return "\n".join(section)


def _format_top_matching_nodes_section(vector_results: List[Dict[str, Any]]) -> str:
    """Format relevant opportunities and information from search results."""
    section = ["## Relevant Opportunities & Information\n"]

    # Take top 10 results
    top_results = vector_results[:10]

    # Group by type for better organization
    jobs = []
    skills = []
    companies = []
    other = []

    for result in top_results:
        node_type = result.get("node_type", result.get("type", "Unknown")).lower()
        if node_type in ["job", "jobrole"]:
            jobs.append(result)
        elif node_type in ["skill", "skills"]:
            skills.append(result)
        elif node_type in ["company", "employer"]:
            companies.append(result)
        else:
            other.append(result)

    # Format jobs naturally
    if jobs:
        section.append("**Job Opportunities:**")
        for job in jobs[:5]:  # Top 5 jobs
            name = job.get("name", "Position")
            company = job.get("company_name", job.get("company", ""))
            salary_min = job.get("salary_min")
            salary_max = job.get("salary_max")

            job_line = f"• {name}"
            if company:
                job_line += f" at {company}"
            if salary_min and salary_max:
                # Format in lakhs if Indian market (assume rupees)
                if salary_min > 100000:  # Likely in rupees
                    min_lpa = salary_min / 100000
                    max_lpa = salary_max / 100000
                    job_line += f" (₹{min_lpa:.1f}-{max_lpa:.1f} LPA)"
                else:
                    job_line += f" (${salary_min:,}-${salary_max:,})"

            section.append(job_line)
        section.append("")

    # Format skills naturally
    if skills:
        section.append("**Relevant Skills:**")
        for skill in skills[:8]:  # Top 8 skills
            name = skill.get("name", "Skill")
            description = skill.get("description", "")
            category = skill.get("category", "")

            skill_line = f"• {name}"
            if category:
                skill_line += f" ({category})"
            section.append(skill_line)

            if description:
                # Add brief description if available
                desc_text = description[:100] + "..." if len(description) > 100 else description
                section.append(f"  → {desc_text}")

        section.append("")

    # Format companies naturally
    if companies:
        section.append("**Companies:**")
        company_names = [c.get("name", "Company") for c in companies[:5]]
        section.append(f"• {', '.join(company_names)}")
        section.append("")

    # Format other items
    if other and not (jobs or skills or companies):
        # Only show if no other categories
        for item in other[:5]:
            name = item.get("name", "Item")
            node_type = item.get("node_type", "Information")
            section.append(f"• {name} ({node_type})")

    return "\n".join(section)


def _format_related_information_section(graph_context: List[Dict[str, Any]]) -> str:
    """Format related information and connections from knowledge graph."""
    section = ["## Graph Relationships & Insights\n"]

    # Separate nodes and relationships
    nodes = [item for item in graph_context if item.get("node_type")]
    relationships = [item for item in graph_context if item.get("type") and not item.get("node_type")]

    # Mapping of technical relationship names to natural language
    relationship_names = {
        "REQUIRES": "Skills Required",
        "REQUIRED_BY": "Required For",
        "POSTED_BY": "Hiring Companies",
        "OFFERS": "Companies Offering",
        "SIMILAR_TO": "Similar Skills",
        "RELATED_TO": "Related To",
        "LEADS_TO": "Career Progression",
        "BELONGS_TO_CATEGORY": "Skill Categories",
        "BELONGS_TO_SUBCATEGORY": "Skill Subcategories"
    }

    # Group nodes by type
    jobs_found = [n for n in nodes if n.get("node_type") in ["Job", "job"]]
    skills_found = [n for n in nodes if n.get("node_type") in ["Skill", "skill", "Specialized Skill"]]
    companies_found = [n for n in nodes if n.get("node_type") in ["Company", "company"]]
    categories_found = [n for n in nodes if n.get("node_type") in ["Category", "Subcategory"]]

    # Show discovered entities with details
    if skills_found:
        section.append(f"**Skills from Graph ({len(skills_found)} found):**")
        for skill in skills_found[:8]:
            name = skill.get("name", "Unknown Skill")
            section.append(f"- {name}")
        if len(skills_found) > 8:
            section.append(f"  _(+{len(skills_found) - 8} more skills)_")
        section.append("")

    if jobs_found:
        section.append(f"**Jobs from Graph ({len(jobs_found)} positions):**")
        for job in jobs_found[:5]:
            name = job.get("name", "Unknown Position")
            section.append(f"- {name}")
        if len(jobs_found) > 5:
            section.append(f"  _(+{len(jobs_found) - 5} more jobs)_")
        section.append("")

    if categories_found:
        category_names = [c.get("name", "Unknown") for c in categories_found[:5]]
        section.append(f"**Skill Categories:** {', '.join(category_names)}")
        section.append("")

    # Group relationships by type
    relationship_groups: Dict[str, int] = {}
    for rel in relationships[:50]:
        rel_type = rel.get("type", "RELATED_TO")
        natural_rel_type = relationship_names.get(rel_type, rel_type.replace("_", " ").title())
        relationship_groups[natural_rel_type] = relationship_groups.get(natural_rel_type, 0) + 1

    # Show relationship statistics
    if relationship_groups:
        section.append("**Graph Connections Found:**")
        for rel_type, count in sorted(relationship_groups.items(), key=lambda x: x[1], reverse=True)[:5]:
            section.append(f"- {count} {rel_type} relationships")
        section.append("")

    # Add insight about graph traversal
    total_items = len(nodes) + len(relationships)
    if total_items > 0:
        section.append(f"*Graph traversal discovered {len(nodes)} nodes and {len(relationships)} relationships across the knowledge graph.*")
    else:
        section.append("*No graph relationship data available*")

    return "\n".join(section)


def _format_skill_gap_analysis(
    vector_results: List[Dict[str, Any]],
    graph_context: List[Dict[str, Any]],
    entities: List[Dict[str, Any]],
) -> str:
    """
    Format skill development roadmap for career transitions.

    Shown when both career_path and skill_requirement intents are detected.
    """
    section = ["## Your Skill Development Roadmap\n"]

    # Extract current skills from entities (what the user knows)
    current_skills = [e["value"] for e in entities if e.get("type") == "skill"]

    # Extract target skills from vector/graph results (what jobs require)
    target_skills = set()
    for result in vector_results[:15]:
        if result.get("node_type") in ["Skill", "skill"]:
            skill_name = result.get("name", "")
            if skill_name and skill_name.lower() not in [s.lower() for s in current_skills]:
                target_skills.add(skill_name)

    for ctx in graph_context[:15]:
        if ctx.get("node_type") == "Skill":
            skill_name = ctx.get("name", "")
            if skill_name and skill_name.lower() not in [s.lower() for s in current_skills]:
                target_skills.add(skill_name)

    if current_skills:
        section.append(f"**Your Foundation:** {', '.join(current_skills)}")
        section.append("")

    if target_skills:
        skills_list = sorted(list(target_skills))[:10]
        section.append(f"**Skills to Develop:** {', '.join(skills_list)}")
        section.append("")

        # Add actionable insight
        if current_skills and target_skills:
            gap_count = len(target_skills)
            if gap_count <= 5:
                section.append(f"💡 **Focus on {gap_count} key skills** to transition successfully")
            elif gap_count <= 10:
                section.append(f"💡 **Prioritize the top 5 skills** from the {gap_count} identified - start with the most in-demand")
            else:
                section.append(f"💡 **Start with 3-5 core skills** from the {gap_count} identified - don't try to learn everything at once")
    elif current_skills:
        section.append("💡 **You're on the right track!** Keep building on your foundation.")
    else:
        return ""  # Skip section if no useful data

    return "\n".join(section)


def _format_transition_context(
    state: "GraphRAGState",
    vector_results: List[Dict[str, Any]],
    graph_context: List[Dict[str, Any]],
    entities: List[Dict[str, Any]],
) -> str:
    """
    Format transition path analysis results for career transitions.

    Phase 4: Displays transition metrics including closeness score,
    transition index, source/target skills, and gap analysis.
    """
    section = ["## Career Transition Analysis\n"]

    # Extract transition-specific fields from state
    transition_path = getattr(state, 'transition_path', None) if state else None
    source_skills = getattr(state, 'source_skills', None) if state else None
    target_skills = getattr(state, 'target_skills', None) if state else None
    closeness_score = getattr(state, 'closeness_score', None) if state else None
    transition_index = getattr(state, 'transition_index', None) if state else None

    # Show transition metrics if available (from transition_metrics node)
    if transition_index is not None:
        # Format transition index as percentage
        index_pct = transition_index * 100
        if index_pct >= 75:
            emoji = "🟢"
            assessment = "Highly compatible transition"
        elif index_pct >= 50:
            emoji = "🟡"
            assessment = "Moderate transition effort required"
        else:
            emoji = "🔴"
            assessment = "Significant skill development needed"

        section.append(f"**Transition Index:** {emoji} {index_pct:.1f}% - {assessment}")
        section.append("")

    if closeness_score is not None:
        closeness_pct = closeness_score * 100
        section.append(f"**Skill Closeness:** {closeness_pct:.1f}% (higher = more transferable skills)")
        section.append("")

    # Show source skills (current skills)
    if source_skills:
        section.append(f"**Your Current Skills ({len(source_skills)}):**")
        for skill in source_skills[:8]:
            section.append(f"  • {skill}")
        if len(source_skills) > 8:
            section.append(f"  _(+{len(source_skills) - 8} more)_")
        section.append("")

    # Show target skills (required for target role)
    if target_skills:
        section.append(f"**Target Role Skills ({len(target_skills)}):**")
        for skill in target_skills[:8]:
            section.append(f"  • {skill}")
        if len(target_skills) > 8:
            section.append(f"  _(+{len(target_skills) - 8} more)_")
        section.append("")

    # Calculate and show skill gap
    if source_skills and target_skills:
        source_set = set(s.lower() for s in source_skills)
        target_set = set(s.lower() for s in target_skills)
        overlap = source_set & target_set
        gap = target_set - source_set

        if overlap:
            overlap_pct = (len(overlap) / len(target_set)) * 100
            section.append(f"**Skill Overlap:** {len(overlap)}/{len(target_set)} ({overlap_pct:.0f}%) - you already have these!")

        if gap:
            section.append(f"\n**Skills to Develop ({len(gap)}):**")
            # Get original case from target_skills
            gap_skills = [s for s in target_skills if s.lower() in gap][:10]
            for skill in gap_skills:
                section.append(f"  📚 {skill}")
            section.append("")

    # Show transition path details if available
    if transition_path:
        path_steps = transition_path.get('path', [])
        if path_steps:
            section.append("**Recommended Learning Path:**")
            for i, step in enumerate(path_steps[:5], 1):
                section.append(f"  {i}. {step}")
            section.append("")

    # Extract related skills from graph context (CO_OCCURS_WITH relationships)
    co_occurs_skills = []
    for ctx in graph_context:
        if ctx.get("type") == "CO_OCCURS_WITH":
            weight = ctx.get("properties", {}).get("weight", 0)
            if weight > 0:
                co_occurs_skills.append(ctx)

    if co_occurs_skills:
        section.append(f"**Skill Relationships Found:** {len(co_occurs_skills)} co-occurrence patterns")
        section.append("_These skills frequently appear together in job postings._")
        section.append("")

    # If no transition data available yet, provide context from entities
    if not any([source_skills, target_skills, closeness_score, transition_index]):
        # Extract from entities
        skill_entities = [e["value"] for e in entities if e.get("type") == "skill"]
        role_entities = [e["value"] for e in entities if e.get("type") in ["role", "job"]]

        if skill_entities:
            section.append(f"**Skills Mentioned:** {', '.join(skill_entities[:5])}")
        if role_entities:
            section.append(f"**Target Roles:** {', '.join(role_entities[:3])}")

        if skill_entities or role_entities:
            section.append("\n💡 *Transition metrics will be calculated based on graph analysis.*")

    return "\n".join(section)


def _format_graph_structure_section(
    graph_context: List[Dict[str, Any]], vector_results: List[Dict[str, Any]], intents: List[str]
) -> str:
    """Format market summary with actionable insights based on detected intents."""
    section = ["## Market Summary\n"]

    insights = []

    # Count total opportunities found
    total_jobs = sum(1 for r in vector_results if r.get("node_type", "").lower() in ["job", "jobrole"])
    if total_jobs > 0:
        insights.append(f"• Found **{total_jobs} job opportunities** matching your interests")

    # Salary insights if salary_analysis intent detected
    if "salary_analysis" in intents:
        salaries = []
        for result in vector_results:
            salary_min = result.get("salary_min")
            salary_max = result.get("salary_max")
            if salary_min and salary_max:
                salaries.append((salary_min, salary_max))

        if salaries:
            avg_min = sum(s[0] for s in salaries) // len(salaries)
            avg_max = sum(s[1] for s in salaries) // len(salaries)

            # Format appropriately for currency (Indian rupees vs others)
            if avg_min > 100000:  # Likely Indian rupees
                min_lpa = avg_min / 100000
                max_lpa = avg_max / 100000
                insights.append(
                    f"• Typical salary range: **₹{min_lpa:.1f}-{max_lpa:.1f} LPA** (based on {len(salaries)} positions)"
                )
            else:
                insights.append(
                    f"• Typical salary range: **${avg_min:,}-${avg_max:,}** (based on {len(salaries)} positions)"
                )

    # Company insights if company_query intent detected
    if "company_query" in intents:
        companies = set()
        for result in vector_results[:15]:
            company = result.get("company_name", result.get("company"))
            if company:
                companies.add(company)
        if companies:
            company_list = ', '.join(sorted(list(companies))[:5])
            if len(companies) > 5:
                company_list += f" and {len(companies) - 5} others"
            insights.append(f"• Top hiring companies: {company_list}")

    # Skill demand insights
    skill_count = sum(1 for r in vector_results if r.get("node_type", "").lower() in ["skill", "skills"])
    if skill_count > 0:
        insights.append(f"• Identified **{skill_count} relevant skills** in high demand")

    # Add insights or placeholder
    if insights:
        section.extend(insights)
    else:
        section.append("*Insufficient data for analysis*")

    return "\n".join(section)


