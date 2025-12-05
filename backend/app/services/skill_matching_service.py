"""
Fuzzy skill matching service with deduplication.

Prevents skill taxonomy pollution by:
1. Exact case-insensitive matching (primary)
2. Fuzzy matching with Levenshtein distance (typo correction)
3. Orphan flagging for manual review (unknown skills)
"""

from typing import Optional, List, Dict, Any
from Levenshtein import distance as levenshtein_distance
import logging

logger = logging.getLogger(__name__)


class SkillMatchingService:
    """
    Match skill names to existing taxonomy using 3-tier strategy.

    Tier 1: Exact Match (case-insensitive)
    Tier 2: Fuzzy Match (Levenshtein distance ≤ 2)
    Tier 3: Orphan Creation (no match, requires manual review)
    """

    FUZZY_MATCH_THRESHOLD = 2  # Maximum Levenshtein distance
    MIN_SKILL_NAME_LENGTH = 2  # Minimum characters for fuzzy matching

    def __init__(self, neo4j_repo, ingestion_repo):
        self.neo4j_repo = neo4j_repo
        self.ingestion_repo = ingestion_repo
        self._skill_cache: Optional[List[dict]] = None

    async def match_skill(self, skill_name: str, job_id: str) -> dict:
        """
        Match skill name to existing taxonomy or create orphan.

        Args:
            skill_name: Raw skill name from CSV (e.g., "Python", "Pyton", "FastAPI")
            job_id: Job ID for logging and relationship creation

        Returns:
            dict: {
                "skill_id": "uuid-or-orphan-id",
                "matched_name": "python",  # Canonical name from taxonomy
                "match_type": "exact" | "fuzzy" | "orphan",
                "confidence": float,  # 1.0 (exact), 0.5-0.9 (fuzzy), 0.0 (orphan)
                "requires_manual_review": bool,
                "fuzzy_candidates": List[str]  # If multiple fuzzy matches
            }
        """
        # Normalize input
        normalized_name = skill_name.lower().strip()

        if len(normalized_name) < self.MIN_SKILL_NAME_LENGTH:
            logger.warning(f"Skill name too short: '{skill_name}' (job: {job_id})")
            return await self._create_orphan(normalized_name, job_id, "too_short")

        # Tier 1: Exact match (fast path)
        exact_match = await self._find_exact_match(normalized_name)
        if exact_match:
            logger.info(f"✅ Exact match: '{skill_name}' → {exact_match['name']}")
            return {
                "skill_id": exact_match["id"],
                "matched_name": exact_match["name"],
                "match_type": "exact",
                "confidence": 1.0,
                "requires_manual_review": False,
                "fuzzy_candidates": []
            }

        # Tier 2: Fuzzy match (typo correction)
        fuzzy_result = await self._find_fuzzy_match(normalized_name)

        if fuzzy_result["match_type"] == "fuzzy_single":
            # Single candidate within threshold
            logger.info(
                f"🔍 Fuzzy match: '{skill_name}' → {fuzzy_result['matched_name']} "
                f"(distance: {fuzzy_result['distance']})"
            )
            return {
                "skill_id": fuzzy_result["skill_id"],
                "matched_name": fuzzy_result["matched_name"],
                "match_type": "fuzzy",
                "confidence": 1.0 - (fuzzy_result["distance"] / 10),  # 0.8-0.9
                "requires_manual_review": False,
                "fuzzy_candidates": []
            }

        elif fuzzy_result["match_type"] == "fuzzy_multiple":
            # Ambiguous: multiple candidates within threshold
            logger.warning(
                f"⚠️  Ambiguous fuzzy match: '{skill_name}' → "
                f"{fuzzy_result['candidates']} (creating orphan for review)"
            )
            return await self._create_orphan(
                normalized_name,
                job_id,
                "ambiguous_fuzzy_match",
                fuzzy_candidates=fuzzy_result["candidates"]
            )

        # Tier 3: No match - create orphan
        logger.warning(f"⚠️  No match found: '{skill_name}' (creating orphan)")
        return await self._create_orphan(normalized_name, job_id, "no_match")

    async def _find_exact_match(self, normalized_name: str) -> Optional[dict]:
        """Find exact case-insensitive match in skill taxonomy."""
        query = """
        MATCH (s:Skill)
        WHERE toLower(s.name) = $normalized_name
        RETURN s.id as id, s.name as name
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {"normalized_name": normalized_name}
        )

        return dict(result[0]) if result else None

    async def _find_fuzzy_match(self, normalized_name: str) -> dict:
        """
        Find fuzzy matches using Levenshtein distance.

        Returns:
            dict with match_type: "fuzzy_single", "fuzzy_multiple", or "no_fuzzy_match"
        """
        # Refresh skill cache if needed
        if self._skill_cache is None:
            await self._refresh_skill_cache()

        # Calculate Levenshtein distance for all skills
        candidates = []
        for taxonomy_skill in self._skill_cache:
            distance = levenshtein_distance(normalized_name, taxonomy_skill["name_lower"])

            if distance <= self.FUZZY_MATCH_THRESHOLD:
                candidates.append({
                    "skill_id": taxonomy_skill["id"],
                    "name": taxonomy_skill["name"],
                    "distance": distance
                })

        # Sort by distance (closest first)
        candidates.sort(key=lambda x: x["distance"])

        if len(candidates) == 0:
            return {"match_type": "no_fuzzy_match"}

        elif len(candidates) == 1:
            # Unambiguous fuzzy match
            return {
                "match_type": "fuzzy_single",
                "skill_id": candidates[0]["skill_id"],
                "matched_name": candidates[0]["name"],
                "distance": candidates[0]["distance"]
            }

        else:
            # Multiple candidates - ambiguous
            return {
                "match_type": "fuzzy_multiple",
                "candidates": [c["name"] for c in candidates]
            }

    async def _refresh_skill_cache(self) -> None:
        """Load all skill names from Neo4j for fuzzy matching."""
        query = """
        MATCH (s:Skill)
        RETURN s.id as id, s.name as name, toLower(s.name) as name_lower
        """

        result = await self.neo4j_repo.execute_query(query)
        self._skill_cache = [dict(record) for record in result]

        logger.info(f"Skill cache refreshed: {len(self._skill_cache)} skills loaded")

    async def _create_orphan(
        self,
        normalized_name: str,
        job_id: str,
        reason: str,
        fuzzy_candidates: Optional[List[str]] = None
    ) -> dict:
        """
        Create orphan skill node for manual review.

        Orphan Node Properties:
        - name: Normalized skill name
        - requires_manual_review: true (admin must validate)
        - created_from_job: true (auto-generated from job CSV)
        - orphan_reason: Why no match was found
        - fuzzy_candidates: Ambiguous matches (if any)
        - created_at: Timestamp
        """
        query = """
        MERGE (s:Skill {name: $normalized_name})
        ON CREATE SET
          s.id = randomUUID(),
          s.requires_manual_review = true,
          s.created_from_job = true,
          s.orphan_reason = $reason,
          s.fuzzy_candidates = $fuzzy_candidates,
          s.created_at = datetime()
        RETURN s.id as id, s.name as name
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {
                "normalized_name": normalized_name,
                "reason": reason,
                "fuzzy_candidates": fuzzy_candidates or []
            }
        )

        orphan = dict(result[0])

        # Log for manual review dashboard
        await self._log_orphan_creation(orphan["id"], normalized_name, job_id, reason, fuzzy_candidates)

        return {
            "skill_id": orphan["id"],
            "matched_name": orphan["name"],
            "match_type": "orphan",
            "confidence": 0.0,
            "requires_manual_review": True,
            "fuzzy_candidates": fuzzy_candidates or []
        }

    async def _log_orphan_creation(
        self,
        skill_id: str,
        skill_name: str,
        job_id: str,
        reason: str,
        fuzzy_candidates: Optional[List[str]] = None
    ) -> None:
        """Log orphan creation for admin review dashboard."""
        # Store in PostgreSQL for admin review interface
        await self.ingestion_repo.create_orphan_log(
            skill_id=skill_id,
            skill_name=skill_name,
            job_id=job_id,
            orphan_reason=reason,
            fuzzy_candidates=fuzzy_candidates or [],
            status="pending_review"
        )
