"""Service for creating job market graph in Neo4j."""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from app.services.embedding_service import EmbeddingService
from app.repositories.neo4j_repository import Neo4jRepository
from app.repositories.ingestion_repository import IngestionRepository
from app.utils.hash_utils import compute_row_hash

logger = logging.getLogger(__name__)


class JobGraphService:
    """
    Service for constructing job market graph in Neo4j.

    Creates:
    - Job nodes with embeddings
    - Company nodes with embeddings
    - Location nodes
    - Relationships (POSTED_BY, LOCATED_IN)

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

    async def create_job_graph(
        self,
        jobs_data: List[dict],
        job_id: str
    ) -> Dict[str, Any]:
        """
        Create complete job market graph from CSV data.

        Args:
            jobs_data: Parsed jobs CSV rows (list of dicts)
            job_id: Ingestion job ID for progress tracking

        Returns:
            dict: {
                "jobs_created": int,
                "companies_created": int,
                "locations_created": int,
                "relationships_created": int,
                "errors": List[str]
            }

        Process:
        1. Generate embeddings for jobs (Job Description or Description fallback)
        2. Generate embeddings for companies (Company Description)
        3. Create Job, Company, Location nodes (MERGE upsert)
        4. Create relationships (POSTED_BY, LOCATED_IN)
        5. Track progress in PostgreSQL IngestionJob
        """
        total_jobs = len(jobs_data)
        logger.info(f"Creating job graph: {total_jobs} jobs")

        stats = {
            "jobs_created": 0,
            "jobs_updated": 0,
            "jobs_unchanged": 0,
            "companies_created": 0,
            "locations_created": 0,
            "relationships_created": 0,
            "errors": []
        }

        # Track unique companies and locations across all batches
        unique_companies = set()
        unique_locations = set()

        # Process in batches
        for batch_num in range(1, (total_jobs // self.BATCH_SIZE) + 2):
            start_idx = (batch_num - 1) * self.BATCH_SIZE
            end_idx = min(start_idx + self.BATCH_SIZE, total_jobs)
            batch = jobs_data[start_idx:end_idx]

            if not batch:
                break

            # Process batch
            try:
                batch_stats = await self._process_jobs_batch(
                    batch, job_id, batch_num, total_jobs, unique_companies, unique_locations
                )

                # Update statistics
                stats["jobs_created"] += batch_stats["jobs_created"]
                stats["jobs_updated"] += batch_stats["jobs_updated"]
                stats["jobs_unchanged"] += batch_stats["jobs_unchanged"]
                stats["relationships_created"] += batch_stats["relationships_created"]
                stats["errors"].extend(batch_stats["errors"])

                # Update unique counts
                stats["companies_created"] = len(unique_companies)
                stats["locations_created"] = len(unique_locations)

                # Log progress every 5 batches
                if batch_num % 5 == 0:
                    logger.info(
                        f"Progress: {stats['jobs_created']}/{total_jobs} job nodes created "
                        f"(batch {batch_num})"
                    )

            except Exception as e:
                error_msg = f"Batch {batch_num} failed: {str(e)}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        logger.info(
            f"Job graph creation complete: "
            f"{stats['jobs_created']} jobs, "
            f"{stats['companies_created']} companies, "
            f"{stats['locations_created']} locations, "
            f"{stats['relationships_created']} relationships"
        )

        return stats

    async def _process_jobs_batch(
        self,
        batch: List[dict],
        job_id: str,
        batch_number: int,
        total_jobs: int,
        unique_companies: set,
        unique_locations: set
    ) -> Dict[str, Any]:
        """
        Process batch of jobs within Neo4j transactions.

        Args:
            batch: List of job dicts from CSV
            job_id: Ingestion job ID
            batch_number: Current batch number
            total_jobs: Total number of jobs to process
            unique_companies: Set to track unique company names
            unique_locations: Set to track unique location names

        Returns:
            dict: Batch statistics (jobs_created, relationships_created, errors)
        """
        batch_stats = {
            "jobs_created": 0,
            "jobs_updated": 0,
            "jobs_unchanged": 0,
            "relationships_created": 0,
            "errors": []
        }

        # Step 1: Generate job embeddings for entire batch
        job_texts = [self._get_job_embedding_text(job) for job in batch]
        job_embeddings = await self.embedding_service.generate_batch_embeddings(job_texts)

        # Step 2: Generate company embeddings (batch unique companies)
        unique_companies_batch = {}
        for job_row in batch:
            company_name = job_row.get("Company Name")
            company_desc = job_row.get("Company Description", "")
            if company_name and company_name not in unique_companies_batch:
                unique_companies_batch[company_name] = company_desc

        company_texts = list(unique_companies_batch.values())
        company_embeddings = await self.embedding_service.generate_batch_embeddings(company_texts)
        company_embedding_map = dict(zip(unique_companies_batch.keys(), company_embeddings))

        # Step 3: Create nodes and relationships
        async with self.neo4j_repo.driver.session() as session:
            tx = await session.begin_transaction()
            try:
                for idx, job_row in enumerate(batch):
                    try:
                        # Create Job node and track action (created/updated/unchanged)
                        action = await self._create_job_node(tx, job_row, job_embeddings[idx])
                        if action == "created":
                            batch_stats["jobs_created"] += 1
                        elif action == "updated":
                            batch_stats["jobs_updated"] += 1
                        elif action == "unchanged":
                            batch_stats["jobs_unchanged"] += 1

                        # Create Company node (if present)
                        company_name = job_row.get("Company Name")
                        if company_name:
                            company_emb = company_embedding_map.get(company_name)
                            await self._create_company_node(tx, job_row, company_emb)
                            unique_companies.add(company_name)

                        # Create Location node (if present)
                        location = job_row.get("Location")
                        if location:
                            await self._create_location_node(
                                tx,
                                location,
                                job_row.get("District")
                            )
                            unique_locations.add(location)

                        # Create relationships
                        rel_count = await self._create_job_relationships(
                            tx,
                            job_row.get("Job ID"),
                            company_name,
                            location
                        )
                        batch_stats["relationships_created"] += rel_count

                    except Exception as e:
                        error_msg = f"Job {job_row.get('Job ID', 'unknown')}: {str(e)}"
                        logger.error(error_msg)
                        batch_stats["errors"].append(error_msg)

                # Commit transaction
                await tx.commit()
            except Exception:
                # Rollback on error
                await tx.rollback()
                raise

        # Step 4: Update IngestionJob progress
        processed_count = min(batch_number * self.BATCH_SIZE, total_jobs)
        await self.ingestion_repo.update_progress(
            job_id=job_id,
            processed_records=processed_count,
            total_records=total_jobs
        )

        return batch_stats

    def _get_job_embedding_text(self, job_row: dict) -> str:
        """
        Select text for job embedding generation.

        Priority:
        1. Job Description field (primary)
        2. Description field (fallback)
        3. Empty string (will return zero vector)

        Args:
            job_row: Job CSV row dict

        Returns:
            str: Text to embed
        """
        job_description = job_row.get("Job Description", "").strip()
        if job_description:
            return job_description

        description = job_row.get("Description", "").strip()
        if description:
            logger.debug(
                f"Job {job_row.get('Job ID')}: Using Description fallback "
                f"(Job Description empty)"
            )
            return description

        logger.warning(
            f"Job {job_row.get('Job ID')}: No description found, using zero vector"
        )
        return ""

    async def _create_job_node(
        self,
        tx,
        job_row: dict,
        embedding_data: dict
    ) -> str:
        """
        Create or update Job node in Neo4j with all 30 CSV fields and hash-based change detection.

        Uses MERGE to upsert by job_id (prevents duplicates on re-ingestion).

        Args:
            tx: Neo4j transaction
            job_row: Job CSV row dict
            embedding_data: Embedding dict from EmbeddingService

        Returns:
            str: "created" | "updated" | "unchanged"
        """
        # Compute row hash for change detection
        row_hash = compute_row_hash(job_row)

        # Check if node exists with same hash (no changes)
        check_query = """
        MATCH (j:Job {job_id: $job_id})
        RETURN j.row_hash as existing_hash
        """
        check_result = await tx.run(check_query, {"job_id": job_row.get("Job ID")})
        check_record = await check_result.single()

        if check_record and check_record["existing_hash"] == row_hash:
            # No changes detected, skip update
            return "unchanged"

        query = """
        MERGE (j:Job {job_id: $job_id})
        ON CREATE SET
          j.job_title = $job_title,
          j.location = $location,
          j.district = $district,
          j.via = $via,
          j.salary = $salary,
          j.min_salary = $min_salary,
          j.max_salary = $max_salary,
          j.mean_salary = $mean_salary,
          j.salary_unit = $salary_unit,
          j.schedule_type = $schedule_type,
          j.work_from_home = $work_from_home,
          j.posted_at = $posted_at,
          j.description = $description,
          j.job_description = $job_description,
          j.apply_options = $apply_options,
          j.exact_matched_company = $exact_matched_company,
          j.nco_code = $nco_code,
          j.description_token_count = $description_token_count,
          j.company_description_token_count = $company_description_token_count,
          j.job_description_token_count = $job_description_token_count,
          j.embedding = $embedding,
          j.embedding_model_version = $embedding_model_version,
          j.embedding_generated_at = datetime(),
          j.row_hash = $row_hash,
          j.created_at = datetime()
        ON MATCH SET
          j.job_title = $job_title,
          j.location = $location,
          j.district = $district,
          j.via = $via,
          j.salary = $salary,
          j.min_salary = $min_salary,
          j.max_salary = $max_salary,
          j.mean_salary = $mean_salary,
          j.salary_unit = $salary_unit,
          j.schedule_type = $schedule_type,
          j.work_from_home = $work_from_home,
          j.posted_at = $posted_at,
          j.description = $description,
          j.job_description = $job_description,
          j.apply_options = $apply_options,
          j.exact_matched_company = $exact_matched_company,
          j.nco_code = $nco_code,
          j.description_token_count = $description_token_count,
          j.company_description_token_count = $company_description_token_count,
          j.job_description_token_count = $job_description_token_count,
          j.embedding = $embedding,
          j.embedding_model_version = $embedding_model_version,
          j.embedding_generated_at = datetime(),
          j.row_hash = $row_hash,
          j.updated_at = datetime()
        RETURN CASE
          WHEN j.created_at = datetime() THEN 'created'
          ELSE 'updated'
        END as action
        """

        # Parse posted_at date
        posted_at = job_row.get("Posted At")
        if posted_at:
            try:
                # Try parsing as ISO format datetime
                posted_at_parsed = datetime.fromisoformat(str(posted_at).replace('Z', '+00:00'))
            except (ValueError, TypeError):
                logger.warning(f"Job {job_row.get('Job ID')}: Invalid Posted At date: {posted_at}")
                posted_at_parsed = None
        else:
            posted_at_parsed = None

        result = await tx.run(
            query,
            job_id=job_row.get("Job ID"),
            job_title=job_row.get("Job Title"),
            location=job_row.get("Location"),
            district=job_row.get("District"),
            via=job_row.get("Via"),
            salary=job_row.get("Salary"),
            min_salary=job_row.get("Minimum Salary"),
            max_salary=job_row.get("Maximum Salary"),
            mean_salary=job_row.get("Mean Salary"),
            salary_unit=job_row.get("Unit of Measure"),
            schedule_type=job_row.get("Schedule Type"),
            work_from_home=bool(job_row.get("Work From Home", 0)),
            posted_at=posted_at_parsed,
            description=job_row.get("Description"),
            job_description=job_row.get("Job Description"),
            apply_options=job_row.get("Apply Options"),
            exact_matched_company=bool(job_row.get("Exact Matched Company", 0)),
            nco_code=job_row.get("NCO_Code_algo"),
            description_token_count=job_row.get("Description Token Count"),
            company_description_token_count=job_row.get("Company Description Token Count"),
            job_description_token_count=job_row.get("Job Description Token Count"),
            embedding=embedding_data["embedding"],
            embedding_model_version=embedding_data["model_version"],
            row_hash=row_hash
        )

        record = await result.single()
        return record["action"] if record else "updated"

    async def _create_company_node(
        self,
        tx,
        job_row: dict,
        embedding_data: Optional[dict]
    ) -> None:
        """
        Create or update Company node with embedding.

        Uses MERGE to upsert by company_name (prevents duplicates).

        Args:
            tx: Neo4j transaction
            job_row: Job CSV row dict
            embedding_data: Embedding dict from EmbeddingService (optional if no description)
        """
        query = """
        MERGE (c:Company {company_name: $company_name})
        ON CREATE SET
          c.cin = $cin,
          c.company_description = $company_description,
          c.industry_classification = $industry_classification,
          c.nic_code = $nic_code,
          c.nic_code_2008 = $nic_code_2008,
          c.embedding = $embedding,
          c.embedding_model_version = $embedding_model_version,
          c.embedding_generated_at = datetime(),
          c.created_at = datetime()
        ON MATCH SET
          c.cin = $cin,
          c.company_description = $company_description,
          c.industry_classification = $industry_classification,
          c.nic_code = $nic_code,
          c.nic_code_2008 = $nic_code_2008,
          c.embedding = $embedding,
          c.embedding_model_version = $embedding_model_version,
          c.embedding_generated_at = datetime(),
          c.updated_at = datetime()
        """

        await tx.run(
            query,
            company_name=job_row.get("Company Name"),
            cin=job_row.get("CIN"),
            company_description=job_row.get("Company Description"),
            industry_classification=job_row.get("CompanyIndustrialClassification"),
            nic_code=job_row.get("NIC_Code_algo"),
            nic_code_2008=job_row.get("nic_code_2_2008"),
            embedding=embedding_data["embedding"] if embedding_data else None,
            embedding_model_version=embedding_data["model_version"] if embedding_data else None
        )

    async def _create_location_node(
        self,
        tx,
        location_name: str,
        district: Optional[str]
    ) -> None:
        """
        Create or update Location node.

        Uses MERGE to prevent duplicates across multiple job ingestions.

        Args:
            tx: Neo4j transaction
            location_name: Location name from CSV
            district: District from CSV (optional)
        """
        query = """
        MERGE (l:Location {location_name: $location_name})
        ON CREATE SET
          l.district = $district,
          l.created_at = datetime()
        ON MATCH SET
          l.last_seen_at = datetime()
        """

        await tx.run(query, location_name=location_name, district=district)

    async def _create_job_relationships(
        self,
        tx,
        job_id: str,
        company_name: Optional[str],
        location_name: Optional[str]
    ) -> int:
        """
        Create relationships for job node.

        Creates:
        - Job -[POSTED_BY]-> Company
        - Job -[LOCATED_IN]-> Location

        Args:
            tx: Neo4j transaction
            job_id: Job ID
            company_name: Company name (optional)
            location_name: Location name (optional)

        Returns:
            int: Number of relationships created
        """
        relationships_created = 0

        # Job -> Company
        if company_name:
            query = """
            MATCH (j:Job {job_id: $job_id})
            MATCH (c:Company {company_name: $company_name})
            MERGE (j)-[r:POSTED_BY]->(c)
            ON CREATE SET r.created_at = datetime()
            """
            await tx.run(query, job_id=job_id, company_name=company_name)
            relationships_created += 1

        # Job -> Location
        if location_name:
            query = """
            MATCH (j:Job {job_id: $job_id})
            MATCH (l:Location {location_name: $location_name})
            MERGE (j)-[r:LOCATED_IN]->(l)
            ON CREATE SET r.created_at = datetime()
            """
            await tx.run(query, job_id=job_id, location_name=location_name)
            relationships_created += 1

        return relationships_created
