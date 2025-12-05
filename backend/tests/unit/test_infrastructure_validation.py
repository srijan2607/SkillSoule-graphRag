"""
Unit tests for Infrastructure Validation (INFRA-001).

Tests the automated Neo4j vector index validation that runs on startup.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import validate_neo4j_indexes


class TestNeo4jIndexValidation:
    """Test suite for Neo4j vector index validation (INFRA-001)."""

    @pytest.mark.asyncio
    async def test_validate_all_indexes_present_and_online(self):
        """
        INFRA-001: Verify validation passes when all indexes are ONLINE.

        Tests the happy path where all 3 required vector indexes exist
        and are in ONLINE state.
        """
        # Mock Neo4j driver
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Mock SHOW INDEXES response with all required indexes ONLINE
        mock_result.data.return_value = [
            {"name": "skill_embedding_idx", "state": "ONLINE"},
            {"name": "job_embedding_idx", "state": "ONLINE"},
            {"name": "company_embedding_idx", "state": "ONLINE"},
            {"name": "other_index", "state": "ONLINE"},  # Extra index is OK
        ]

        mock_session.run.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = AsyncMock(return_value=None)

        # session() should return a context manager, not a coroutine
        mock_driver.session = MagicMock(return_value=mock_session)

        # Patch global neo4j_driver
        with patch("app.main.neo4j_driver", mock_driver):
            # Should not raise exception
            await validate_neo4j_indexes()

        # Verify SHOW INDEXES was called
        mock_session.run.assert_called_once_with("SHOW INDEXES")

    @pytest.mark.asyncio
    async def test_validate_fails_when_index_missing(self):
        """
        INFRA-001: Verify validation fails when required index is missing.

        Tests that startup fails fast if any of the 3 required vector
        indexes is missing from Neo4j.
        """
        # Mock Neo4j driver
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Mock SHOW INDEXES response with missing job_embedding_idx
        mock_result.data.return_value = [
            {"name": "skill_embedding_idx", "state": "ONLINE"},
            # job_embedding_idx is MISSING
            {"name": "company_embedding_idx", "state": "ONLINE"},
        ]

        mock_session.run.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = AsyncMock(return_value=None)

        # session() should return a context manager, not a coroutine
        mock_driver.session = MagicMock(return_value=mock_session)

        # Patch global neo4j_driver
        with patch("app.main.neo4j_driver", mock_driver):
            # Should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                await validate_neo4j_indexes()

            # Verify error message mentions missing index
            assert "Missing Neo4j vector indexes" in str(exc_info.value)
            assert "job_embedding_idx" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_fails_when_index_not_online(self):
        """
        INFRA-001: Verify validation fails when index is not ONLINE.

        Tests that startup fails if any required index is in a non-ONLINE
        state (e.g., POPULATING, FAILED).
        """
        # Mock Neo4j driver
        mock_driver = AsyncMock()
        mock_session = AsyncMock()
        mock_result = AsyncMock()

        # Mock SHOW INDEXES response with company_embedding_idx in POPULATING state
        mock_result.data.return_value = [
            {"name": "skill_embedding_idx", "state": "ONLINE"},
            {"name": "job_embedding_idx", "state": "ONLINE"},
            {"name": "company_embedding_idx", "state": "POPULATING"},  # Not ONLINE
        ]

        mock_session.run.return_value = mock_result
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = AsyncMock(return_value=None)

        # session() should return a context manager, not a coroutine
        mock_driver.session = MagicMock(return_value=mock_session)

        # Patch global neo4j_driver
        with patch("app.main.neo4j_driver", mock_driver):
            # Should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                await validate_neo4j_indexes()

            # Verify error message mentions offline index
            assert "not ONLINE" in str(exc_info.value)
            assert "company_embedding_idx" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_fails_when_driver_not_initialized(self):
        """
        INFRA-001: Verify validation fails gracefully if driver is None.

        Tests defensive error handling when validation is called
        before Neo4j driver initialization.
        """
        # Patch global neo4j_driver to None
        with patch("app.main.neo4j_driver", None):
            # Should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                await validate_neo4j_indexes()

            assert "Neo4j driver not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_fails_on_neo4j_connection_error(self):
        """
        INFRA-001: Verify validation fails gracefully on connection errors.

        Tests that Neo4j connection failures during index validation
        result in clear error messages.
        """
        # Mock Neo4j driver that raises connection error
        mock_driver = AsyncMock()
        mock_session = AsyncMock()

        mock_session.run.side_effect = Exception("Connection refused")
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        mock_driver.session.return_value = mock_session

        # Patch global neo4j_driver
        with patch("app.main.neo4j_driver", mock_driver):
            # Should raise RuntimeError with descriptive message
            with pytest.raises(RuntimeError) as exc_info:
                await validate_neo4j_indexes()

            assert "Failed to validate Neo4j indexes" in str(exc_info.value)
