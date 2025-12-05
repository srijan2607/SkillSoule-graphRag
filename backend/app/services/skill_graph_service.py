"""Service for creating skills taxonomy graph in Neo4j."""
from typing import List, Dict, Any, Optional
import logging
from app.services.embedding_service import EmbeddingService
from app.repositories.neo4j_repository import Neo4jRepository
from app.repositories.ingestion_repository import IngestionRepository
from app.utils.hash_utils import compute_row_hash

logger = logging.getLogger(__name__)


class SkillGraphService:
    """
    Service for constructing skills taxonomy graph in Neo4j.

    Creates:
    - Skill nodes with embeddings
    - Category and Subcategory nodes
    - Hierarchical relationships (BELONGS_TO_CATEGORY, BELONGS_TO_SUBCATEGORY, CONTAINS)

    Uses batch transactions (1000 nodes) for performance.
    """

    BATCH_SIZE = 1000  # Commit every 1000 nodes

    def __init__(
        self,
        embedding_service: EmbeddingService,
        neo4j_repo: Neo4jRepository,
        ingestion_repo: IngestionRepository
    ):
        self.embedding_service = embedding_service
        self.neo4j_repo = neo4j_repo
        self.ingestion_repo = ingestion_repo

    def _validate_required_fields(self, skills_data: List[dict]) -> None:
        """
        Validate that all required CSV fields are present.

        Args:
            skills_data: Parsed skills CSV rows

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["ID", "NAME"]

        for idx, skill_row in enumerate(skills_data):
            missing_fields = [field for field in required_fields if field not in skill_row]
            if missing_fields:
                raise ValueError(
                    f"Row {idx + 2}: Missing required fields {missing_fields}. "
                    f"Required fields are: {required_fields}"
                )

            # Also check that required fields are not empty
            for field in required_fields:
                if not skill_row.get(field) or str(skill_row.get(field)).strip() == "":
                    raise ValueError(
                        f"Row {idx + 2}: Field '{field}' is empty or whitespace. "
                        f"All required fields must have non-empty values."
                    )

    async def create_skill_graph(
        self,
        skills_data: List[dict],
        job_id: str
    ) -> Dict[str, Any]:
        """
        Create complete skills taxonomy graph from CSV data.

        Args:
            skills_data: Parsed skills CSV rows (list of dicts)
            job_id: Ingestion job ID for progress tracking

        Returns:
            dict: {
                "skills_created": int,
                "categories_created": int,
                "subcategories_created": int,
                "relationships_created": int,
                "errors": List[str]
            }

        Process:
        1. Validate required CSV fields (ID, NAME)
        2. Generate embeddings for all skills (batch processing)
        3. Create Skill, Category, Subcategory nodes (MERGE upsert)
        4. Create relationships (BELONGS_TO_CATEGORY, BELONGS_TO_SUBCATEGORY, CONTAINS)
        5. Track progress in PostgreSQL IngestionJob
        """
        # Validate required fields
        self._validate_required_fields(skills_data)

        total_skills = len(skills_data)
        logger.info(f"Creating skill graph: {total_skills} skills")

        stats = {
            "skills_created": 0,
            "skills_updated": 0,
            "skills_unchanged": 0,
            "categories_created": 0,
            "subcategories_created": 0,
            "relationships_created": 0,
            "errors": []
        }

        # Track unique category/subcategory IDs across all batches
        unique_categories = set()
        unique_subcategories = set()

        # Process in batches
        for batch_num in range(1, (total_skills // self.BATCH_SIZE) + 2):
            start_idx = (batch_num - 1) * self.BATCH_SIZE
            end_idx = min(start_idx + self.BATCH_SIZE, total_skills)
            batch = skills_data[start_idx:end_idx]

            if not batch:
                break

            # Process batch
            try:
                batch_stats = await self._process_skills_batch(
                    batch, job_id, batch_num, total_skills, unique_categories, unique_subcategories
                )

                # Update statistics
                stats["skills_created"] += batch_stats["skills_created"]
                stats["skills_updated"] += batch_stats["skills_updated"]
                stats["skills_unchanged"] += batch_stats["skills_unchanged"]
                stats["relationships_created"] += batch_stats["relationships_created"]
                stats["errors"].extend(batch_stats["errors"])

                # Update unique category/subcategory counts
                stats["categories_created"] = len(unique_categories)
                stats["subcategories_created"] = len(unique_subcategories)

                # Log progress every 5 batches
                if batch_num % 5 == 0:
                    logger.info(
                        f"Progress: {stats['skills_created']}/{total_skills} skill nodes created "
                        f"(batch {batch_num})"
                    )

            except Exception as e:
                error_msg = f"Batch {batch_num} failed: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        logger.info(
            f"Skill graph creation complete: "
            f"{stats['skills_created']} skills, "
            f"{stats['categories_created']} categories, "
            f"{stats['subcategories_created']} subcategories, "
            f"{stats['relationships_created']} relationships"
        )

        return stats

    async def _process_skills_batch(
        self,
        batch: List[dict],
        job_id: str,
        batch_number: int,
        total_skills: int,
        unique_categories: set,
        unique_subcategories: set
    ) -> Dict[str, Any]:
        """
        Process batch of skills within Neo4j transactions.

        Args:
            batch: List of skill dicts from CSV
            job_id: Ingestion job ID
            batch_number: Current batch number
            total_skills: Total number of skills to process
            unique_categories: Set to track unique category IDs
            unique_subcategories: Set to track unique subcategory IDs

        Returns:
            dict: Batch statistics (skills_created, relationships_created, errors)
        """
        batch_stats = {
            "skills_created": 0,
            "skills_updated": 0,
            "skills_unchanged": 0,
            "relationships_created": 0,
            "errors": []
        }

        # Step 1: Generate embeddings for entire batch
        embedding_texts = [self._get_embedding_text(skill) for skill in batch]
        embeddings = await self.embedding_service.generate_batch_embeddings(embedding_texts)

        # Step 2: Create nodes and relationships
        async with self.neo4j_repo.driver.session() as session:
            tx = await session.begin_transaction()
            try:
                for idx, skill_row in enumerate(batch):
                    try:
                        # Create Skill node and track action (created/updated/unchanged)
                        action = await self._create_skill_node(tx, skill_row, embeddings[idx])
                        if action == "created":
                            batch_stats["skills_created"] += 1
                        elif action == "updated":
                            batch_stats["skills_updated"] += 1
                        elif action == "unchanged":
                            batch_stats["skills_unchanged"] += 1

                        # Create Category node (if present) and track unique ID
                        if skill_row.get("CATEGORY"):
                            await self._create_category_node(
                                tx,
                                skill_row["CATEGORY"],
                                skill_row.get("CATEGORY_NAME", "")
                            )
                            unique_categories.add(skill_row["CATEGORY"])

                        # Create Subcategory node (if present) and track unique ID
                        if skill_row.get("SUBCATEGORY"):
                            await self._create_subcategory_node(
                                tx,
                                skill_row["SUBCATEGORY"],
                                skill_row.get("SUBCATEGORY_NAME", "")
                            )
                            unique_subcategories.add(skill_row["SUBCATEGORY"])

                        # Create relationships
                        rel_count = await self._create_skill_relationships(
                            tx,
                            skill_row["ID"],
                            skill_row.get("CATEGORY"),
                            skill_row.get("SUBCATEGORY")
                        )
                        batch_stats["relationships_created"] += rel_count

                    except Exception as e:
                        error_msg = f"Skill {skill_row.get('ID', 'unknown')}: {str(e)}"
                        logger.error(error_msg)
                        batch_stats["errors"].append(error_msg)

                # Commit transaction
                await tx.commit()
            except Exception as e:
                # Rollback on error
                await tx.rollback()
                raise

        # Step 3: Update IngestionJob progress
        processed_count = min(batch_number * self.BATCH_SIZE, total_skills)
        await self.ingestion_repo.update_progress(
            job_id=job_id,
            processed_records=processed_count,
            total_records=total_skills
        )

        return batch_stats

    def _get_embedding_text(self, skill_row: dict) -> str:
        """
        Select text for embedding generation.

        Priority:
        1. DESCRIPTION field (primary)
        2. WIKI_EXTRACT field (secondary)
        3. Empty string (will return zero vector)

        Args:
            skill_row: Skill CSV row dict

        Returns:
            str: Text to embed
        """
        description = skill_row.get("DESCRIPTION", "").strip()
        if description:
            return description

        wiki_extract = skill_row.get("WIKI_EXTRACT", "").strip()
        if wiki_extract:
            logger.debug(
                f"Skill {skill_row.get('ID')}: Using WIKI_EXTRACT (DESCRIPTION empty)"
            )
            return wiki_extract

        logger.warning(
            f"Skill {skill_row.get('ID')}: No DESCRIPTION or WIKI_EXTRACT, using zero vector"
        )
        return ""

    async def _create_skill_node(
        self,
        tx,
        skill_row: dict,
        embedding_data: dict
    ) -> str:
        """
        Create or update Skill node in Neo4j with hash-based change detection.

        Uses MERGE to upsert by skill ID (prevents duplicates on re-ingestion).

        Args:
            tx: Neo4j transaction
            skill_row: Skill CSV row dict
            embedding_data: Embedding dict from EmbeddingService

        Returns:
            str: "created" | "updated" | "unchanged"
        """
        # Compute row hash for change detection
        row_hash = compute_row_hash(skill_row)

        # Check if node exists with same hash (no changes)
        check_query = """
        MATCH (s:Skill {id: $id})
        RETURN s.row_hash as existing_hash
        """
        check_result = await tx.run(check_query, {"id": skill_row["ID"]})
        check_record = await check_result.single()

        if check_record and check_record["existing_hash"] == row_hash:
            # No changes detected, skip update
            return "unchanged"

        query = """
        MERGE (s:Skill {id: $id})
        ON CREATE SET
          s.name = toLower(trim($name)),
          s.level = $level,
          s.type = $type,
          s.is_software = $is_software,
          s.is_language = $is_language,
          s.description = $description,
          s.description_source = $description_source,
          s.version = $version,
          s.latest_version = $latest_version,
          s.wiki_link = $wiki_link,
          s.wiki_extract = $wiki_extract,
          s.embedding = $embedding,
          s.embedding_model_version = $embedding_model_version,
          s.embedding_generated_at = datetime(),
          s.row_hash = $row_hash,
          s.created_at = datetime()
        ON MATCH SET
          s.name = toLower(trim($name)),
          s.level = $level,
          s.type = $type,
          s.is_software = $is_software,
          s.is_language = $is_language,
          s.description = $description,
          s.description_source = $description_source,
          s.version = $version,
          s.latest_version = $latest_version,
          s.wiki_link = $wiki_link,
          s.wiki_extract = $wiki_extract,
          s.embedding = $embedding,
          s.embedding_model_version = $embedding_model_version,
          s.embedding_generated_at = datetime(),
          s.row_hash = $row_hash,
          s.updated_at = datetime()
        RETURN CASE
          WHEN s.created_at = datetime() THEN 'created'
          ELSE 'updated'
        END as action
        """

        # Determine description source for metadata
        description_source = None
        if skill_row.get("DESCRIPTION", "").strip():
            description_source = "csv_description"
        elif skill_row.get("WIKI_EXTRACT", "").strip():
            description_source = "wiki_extract"

        result = await tx.run(
            query,
            id=skill_row["ID"],
            name=skill_row["NAME"],
            level=skill_row.get("LEVEL"),
            type=skill_row.get("TYPE"),
            is_software=skill_row.get("IS_SOFTWARE", False),
            is_language=skill_row.get("IS_LANGUAGE", False),
            description=skill_row.get("DESCRIPTION"),
            description_source=description_source,
            version=skill_row.get("VERSION"),
            latest_version=skill_row.get("LATEST_VERSION"),
            wiki_link=skill_row.get("WIKI_LINK"),
            wiki_extract=skill_row.get("WIKI_EXTRACT"),
            embedding=embedding_data["embedding"],
            embedding_model_version=embedding_data["model_version"],
            row_hash=row_hash
        )

        record = await result.single()
        return record["action"] if record else "updated"

    async def _create_category_node(
        self,
        tx,
        category_id: str,
        category_name: str
    ) -> None:
        """
        Create or update Category node.

        Uses MERGE to prevent duplicates across multiple skill ingestions.

        Args:
            tx: Neo4j transaction
            category_id: Category ID from CSV (CATEGORY column)
            category_name: Category name from CSV (CATEGORY_NAME column)
        """
        query = """
        MERGE (cat:Category {category_id: $category_id})
        ON CREATE SET
          cat.category_name = $category_name,
          cat.created_at = datetime()
        ON MATCH SET
          cat.category_name = $category_name,
          cat.last_seen_at = datetime()
        """

        await tx.run(
            query,
            category_id=category_id,
            category_name=category_name
        )

    async def _create_subcategory_node(
        self,
        tx,
        subcategory_id: str,
        subcategory_name: str
    ) -> None:
        """
        Create or update Subcategory node.

        Uses MERGE to prevent duplicates across multiple skill ingestions.

        Args:
            tx: Neo4j transaction
            subcategory_id: Subcategory ID from CSV (SUBCATEGORY column)
            subcategory_name: Subcategory name from CSV (SUBCATEGORY_NAME column)
        """
        query = """
        MERGE (sub:Subcategory {subcategory_id: $subcategory_id})
        ON CREATE SET
          sub.subcategory_name = $subcategory_name,
          sub.created_at = datetime()
        ON MATCH SET
          sub.subcategory_name = $subcategory_name,
          sub.last_seen_at = datetime()
        """

        await tx.run(
            query,
            subcategory_id=subcategory_id,
            subcategory_name=subcategory_name
        )

    async def _create_skill_relationships(
        self,
        tx,
        skill_id: str,
        category_id: Optional[str],
        subcategory_id: Optional[str]
    ) -> int:
        """
        Create relationships for skill node.

        Creates:
        - Skill -[BELONGS_TO_CATEGORY]-> Category
        - Skill -[BELONGS_TO_SUBCATEGORY]-> Subcategory
        - Category -[CONTAINS]-> Subcategory

        Args:
            tx: Neo4j transaction
            skill_id: Skill ID
            category_id: Category ID (optional)
            subcategory_id: Subcategory ID (optional)

        Returns:
            int: Number of relationships created
        """
        relationships_created = 0

        # Skill -> Category
        if category_id:
            query = """
            MATCH (s:Skill {id: $skill_id})
            MATCH (cat:Category {category_id: $category_id})
            MERGE (s)-[r:BELONGS_TO_CATEGORY]->(cat)
            ON CREATE SET r.created_at = datetime()
            """
            await tx.run(query, skill_id=skill_id, category_id=category_id)
            relationships_created += 1

        # Skill -> Subcategory
        if subcategory_id:
            query = """
            MATCH (s:Skill {id: $skill_id})
            MATCH (sub:Subcategory {subcategory_id: $subcategory_id})
            MERGE (s)-[r:BELONGS_TO_SUBCATEGORY]->(sub)
            ON CREATE SET r.created_at = datetime()
            """
            await tx.run(query, skill_id=skill_id, subcategory_id=subcategory_id)
            relationships_created += 1

        # Category -> Subcategory (if both present)
        if category_id and subcategory_id:
            query = """
            MATCH (cat:Category {category_id: $category_id})
            MATCH (sub:Subcategory {subcategory_id: $subcategory_id})
            MERGE (cat)-[r:CONTAINS]->(sub)
            ON CREATE SET r.created_at = datetime()
            """
            await tx.run(query, category_id=category_id, subcategory_id=subcategory_id)
            relationships_created += 1

        return relationships_created
