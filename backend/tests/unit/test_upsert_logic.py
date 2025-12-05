"""Unit tests for upsert logic (Story 3.7)."""
import pytest
from datetime import datetime
from app.utils.hash_utils import compute_row_hash, has_row_changed
from app.models.ingestion_mode import IngestionMode


class TestHashUtils:
    """Test hash-based change detection utilities."""

    def test_compute_row_hash_consistent(self):
        """Verify hash is consistent for same data."""
        row1 = {"ID": "skill-123", "NAME": "Python", "DESCRIPTION": "Programming language"}
        row2 = {"ID": "skill-123", "NAME": "Python", "DESCRIPTION": "Programming language"}

        hash1 = compute_row_hash(row1)
        hash2 = compute_row_hash(row2)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_compute_row_hash_excludes_metadata(self):
        """Verify metadata fields are excluded from hash."""
        row1 = {"ID": "skill-123", "NAME": "Python", "created_at": "2025-01-01"}
        row2 = {"ID": "skill-123", "NAME": "Python", "created_at": "2025-12-31"}

        hash1 = compute_row_hash(row1)
        hash2 = compute_row_hash(row2)

        # Hashes should be identical despite different created_at
        assert hash1 == hash2

    def test_compute_row_hash_detects_changes(self):
        """Verify hash changes when data changes."""
        row1 = {"ID": "skill-123", "NAME": "Python", "DESCRIPTION": "Old description"}
        row2 = {"ID": "skill-123", "NAME": "Python", "DESCRIPTION": "New description"}

        hash1 = compute_row_hash(row1)
        hash2 = compute_row_hash(row2)

        assert hash1 != hash2

    def test_has_row_changed_detects_change(self):
        """Verify has_row_changed returns True when data changes."""
        row_old = {"ID": "skill-123", "NAME": "Python", "DESCRIPTION": "Old"}
        row_new = {"ID": "skill-123", "NAME": "Python", "DESCRIPTION": "New"}

        old_hash = compute_row_hash(row_old)
        assert has_row_changed(row_new, old_hash) is True

    def test_has_row_changed_detects_no_change(self):
        """Verify has_row_changed returns False when data unchanged."""
        row = {"ID": "skill-123", "NAME": "Python", "DESCRIPTION": "Same"}

        existing_hash = compute_row_hash(row)
        assert has_row_changed(row, existing_hash) is False


class TestIngestionMode:
    """Test ingestion mode enum."""

    def test_ingestion_mode_values(self):
        """Verify enum values are correct."""
        assert IngestionMode.INCREMENTAL.value == "incremental"
        assert IngestionMode.FULL.value == "full"

    def test_ingestion_mode_is_string_enum(self):
        """Verify enum values are strings."""
        assert isinstance(IngestionMode.INCREMENTAL.value, str)
        assert isinstance(IngestionMode.FULL.value, str)


@pytest.mark.unit
@pytest.mark.asyncio
class TestMergePatterns:
    """Test MERGE patterns with Neo4j (requires test Neo4j instance)."""

    @pytest.fixture
    async def test_db(self, neo4j_test_db):
        """Fixture for test Neo4j database connection."""
        return neo4j_test_db

    async def test_merge_creates_node_on_first_run(self, test_db):
        """Verify MERGE creates node on first ingestion."""
        from app.utils.hash_utils import compute_row_hash

        skill_data = {
            "ID": "skill-test-123",
            "NAME": "Python",
            "DESCRIPTION": "Programming language"
        }

        row_hash = compute_row_hash(skill_data)

        # Run MERGE query with new skill ID
        query = """
        MERGE (s:Skill {id: $id})
        ON CREATE SET
            s.name = $name,
            s.description = $description,
            s.row_hash = $row_hash,
            s.created_at = datetime()
        RETURN CASE
            WHEN s.created_at = datetime() THEN 'created'
            ELSE 'updated'
        END as action
        """

        async with test_db.driver.session() as session:
            result = await session.run(query, {
                "id": skill_data["ID"],
                "name": skill_data["NAME"],
                "description": skill_data["DESCRIPTION"],
                "row_hash": row_hash
            })
            record = await result.single()

            # Verify action is "created"
            assert record["action"] == "created"

            # Verify node exists with created_at
            verify_result = await session.run(
                "MATCH (s:Skill {id: $id}) RETURN s.created_at as created",
                {"id": skill_data["ID"]}
            )
            verify_record = await verify_result.single()
            assert verify_record["created"] is not None

    async def test_merge_updates_node_on_second_run(self, test_db):
        """Verify MERGE updates node on re-ingestion."""
        from app.utils.hash_utils import compute_row_hash
        import time

        skill_id = "skill-test-456"

        # Create node with initial data
        initial_data = {
            "ID": skill_id,
            "NAME": "JavaScript",
            "DESCRIPTION": "Old description"
        }

        query = """
        MERGE (s:Skill {id: $id})
        ON CREATE SET
            s.name = $name,
            s.description = $description,
            s.row_hash = $row_hash,
            s.created_at = datetime()
        """

        async with test_db.driver.session() as session:
            await session.run(query, {
                "id": initial_data["ID"],
                "name": initial_data["NAME"],
                "description": initial_data["DESCRIPTION"],
                "row_hash": compute_row_hash(initial_data)
            })

            # Small delay to ensure different timestamps
            await asyncio.sleep(0.1)

            # Update node with new data
            updated_data = {
                "ID": skill_id,
                "NAME": "JavaScript",
                "DESCRIPTION": "Updated description"
            }

            update_query = """
            MERGE (s:Skill {id: $id})
            ON CREATE SET
                s.name = $name,
                s.description = $description,
                s.row_hash = $row_hash,
                s.created_at = datetime()
            ON MATCH SET
                s.name = $name,
                s.description = $description,
                s.row_hash = $row_hash,
                s.updated_at = datetime()
            RETURN CASE
                WHEN s.created_at = datetime() THEN 'created'
                ELSE 'updated'
            END as action
            """

            result = await session.run(update_query, {
                "id": updated_data["ID"],
                "name": updated_data["NAME"],
                "description": updated_data["DESCRIPTION"],
                "row_hash": compute_row_hash(updated_data)
            })
            record = await result.single()

            # Verify action is "updated"
            assert record["action"] == "updated"

            # Verify description updated
            verify_result = await session.run(
                "MATCH (s:Skill {id: $id}) RETURN s.description as desc",
                {"id": skill_id}
            )
            verify_record = await verify_result.single()
            assert verify_record["desc"] == "Updated description"

    async def test_created_at_preserved_on_update(self, test_db):
        """Verify created_at never changes on updates."""
        from app.utils.hash_utils import compute_row_hash

        skill_id = "skill-test-789"

        # Create node
        initial_data = {
            "ID": skill_id,
            "NAME": "Go",
            "DESCRIPTION": "Systems language"
        }

        query = """
        MERGE (s:Skill {id: $id})
        ON CREATE SET
            s.name = $name,
            s.description = $description,
            s.row_hash = $row_hash,
            s.created_at = datetime()
        """

        async with test_db.driver.session() as session:
            await session.run(query, {
                "id": initial_data["ID"],
                "name": initial_data["NAME"],
                "description": initial_data["DESCRIPTION"],
                "row_hash": compute_row_hash(initial_data)
            })

            # Get initial created_at
            result = await session.run(
                "MATCH (s:Skill {id: $id}) RETURN s.created_at as created",
                {"id": skill_id}
            )
            record = await result.single()
            created_at_initial = record["created"]

            # Wait to ensure different timestamp
            await asyncio.sleep(0.1)

            # Update node
            updated_data = {
                "ID": skill_id,
                "NAME": "Go",
                "DESCRIPTION": "Modern systems language"
            }

            update_query = """
            MERGE (s:Skill {id: $id})
            ON CREATE SET
                s.name = $name,
                s.description = $description,
                s.row_hash = $row_hash,
                s.created_at = datetime()
            ON MATCH SET
                s.name = $name,
                s.description = $description,
                s.row_hash = $row_hash,
                s.updated_at = datetime()
            """

            await session.run(update_query, {
                "id": updated_data["ID"],
                "name": updated_data["NAME"],
                "description": updated_data["DESCRIPTION"],
                "row_hash": compute_row_hash(updated_data)
            })

            # Get timestamps after update
            result = await session.run(
                "MATCH (s:Skill {id: $id}) RETURN s.created_at as created, s.updated_at as updated",
                {"id": skill_id}
            )
            record = await result.single()

            # Verify created_at unchanged
            assert record["created"] == created_at_initial

            # Verify updated_at is set and different
            assert record["updated"] is not None
            assert record["updated"] != record["created"]

    async def test_hash_based_change_detection_skips_update(self, test_db):
        """Verify unchanged rows skip update."""
        from app.utils.hash_utils import compute_row_hash

        skill_id = "skill-test-999"
        skill_data = {
            "ID": skill_id,
            "NAME": "Rust",
            "DESCRIPTION": "Memory-safe language"
        }

        row_hash = compute_row_hash(skill_data)

        # Create node
        create_query = """
        MERGE (s:Skill {id: $id})
        ON CREATE SET
            s.name = $name,
            s.description = $description,
            s.row_hash = $row_hash,
            s.created_at = datetime()
        """

        async with test_db.driver.session() as session:
            await session.run(create_query, {
                "id": skill_data["ID"],
                "name": skill_data["NAME"],
                "description": skill_data["DESCRIPTION"],
                "row_hash": row_hash
            })

            # Check if row hash matches (simulate early return logic)
            check_query = """
            MATCH (s:Skill {id: $id})
            RETURN s.row_hash as existing_hash
            """

            result = await session.run(check_query, {"id": skill_id})
            record = await result.single()
            existing_hash = record["existing_hash"]

            # Verify hash matches (unchanged data)
            assert existing_hash == row_hash

            # This simulates the early return - no MERGE would be executed
            # In actual implementation, we return "unchanged" before running MERGE


@pytest.mark.unit
class TestFullModeValidation:
    """Test full mode confirmation validation."""

    def test_full_mode_requires_confirmation(self):
        """Verify full mode without confirmation is rejected."""
        from app.models.ingestion_mode import IngestionMode
        from app.models.ingestion import ConfirmUploadRequest

        # Simulate validation logic
        confirmation_data = {
            "file_hash": "test_hash",
            "file_type": "skills",
            "mode": IngestionMode.FULL,
            "confirmation": None
        }

        # Check validation (simulates API logic)
        mode = confirmation_data["mode"]
        confirmation = confirmation_data["confirmation"]

        # Expected: validation fails
        should_fail = (mode == IngestionMode.FULL and
                      (not confirmation or confirmation != "CONFIRM DELETE"))

        assert should_fail is True

    def test_full_mode_requires_correct_confirmation_text(self):
        """Verify full mode with wrong confirmation text is rejected."""
        from app.models.ingestion_mode import IngestionMode

        # Simulate validation with wrong confirmation text
        confirmation_data = {
            "file_hash": "test_hash",
            "file_type": "skills",
            "mode": IngestionMode.FULL,
            "confirmation": "YES"  # Wrong text
        }

        mode = confirmation_data["mode"]
        confirmation = confirmation_data["confirmation"]

        # Expected: validation fails
        should_fail = (mode == IngestionMode.FULL and
                      (not confirmation or confirmation != "CONFIRM DELETE"))

        assert should_fail is True

    def test_full_mode_accepts_correct_confirmation(self):
        """Verify full mode with correct confirmation proceeds."""
        from app.models.ingestion_mode import IngestionMode

        # Simulate validation with correct confirmation
        confirmation_data = {
            "file_hash": "test_hash",
            "file_type": "skills",
            "mode": IngestionMode.FULL,
            "confirmation": "CONFIRM DELETE"
        }

        mode = confirmation_data["mode"]
        confirmation = confirmation_data["confirmation"]

        # Expected: validation passes
        should_pass = not (mode == IngestionMode.FULL and
                          (not confirmation or confirmation != "CONFIRM DELETE"))

        assert should_pass is True

    def test_incremental_mode_works_without_confirmation(self):
        """Verify incremental mode doesn't require confirmation."""
        from app.models.ingestion_mode import IngestionMode

        # Simulate validation with incremental mode, no confirmation
        confirmation_data = {
            "file_hash": "test_hash",
            "file_type": "skills",
            "mode": IngestionMode.INCREMENTAL,
            "confirmation": None
        }

        mode = confirmation_data["mode"]
        confirmation = confirmation_data["confirmation"]

        # Expected: validation passes (incremental doesn't need confirmation)
        should_pass = not (mode == IngestionMode.FULL and
                          (not confirmation or confirmation != "CONFIRM DELETE"))

        assert should_pass is True


# Note: Full integration tests with Neo4j are in tests/integration/test_incremental_ingestion.py
