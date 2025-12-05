"""Unit tests for file_cache utility (Story 2.3)."""

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from app.utils.file_cache import (
    store_temp_file,
    retrieve_temp_file,
    delete_temp_file,
    cleanup_expired_files,
    get_cache_stats,
    _file_cache
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the file cache before each test."""
    _file_cache.clear()
    yield
    _file_cache.clear()


@pytest.mark.unit
def test_store_temp_file_basic():
    """Test basic file storage with SHA-256 hash."""
    content = b"ID,NAME\n1,Python\n2,Java"
    file_type = "skills"
    filename = "skills.csv"

    file_hash = store_temp_file(content, file_type, filename, ttl_hours=1)

    # Verify hash is SHA-256 (64 hex characters)
    assert len(file_hash) == 64
    assert all(c in "0123456789abcdef" for c in file_hash)

    # Verify file is in cache
    assert file_hash in _file_cache


@pytest.mark.unit
def test_store_temp_file_metadata():
    """Test that file metadata is stored correctly."""
    content = b"ID,NAME\n1,Python"
    file_type = "jobs"
    filename = "jobs.csv"

    file_hash = store_temp_file(content, file_type, filename, ttl_hours=2)

    cached_data = _file_cache[file_hash]
    assert cached_data["content"] == content
    assert cached_data["file_type"] == file_type
    assert cached_data["filename"] == filename
    assert cached_data["file_size_mb"] == len(content) / (1024 * 1024)
    assert "expires_at" in cached_data


@pytest.mark.unit
def test_store_temp_file_ttl():
    """Test that TTL is set correctly."""
    content = b"test"

    with patch('app.utils.file_cache.datetime') as mock_datetime:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = now

        file_hash = store_temp_file(content, "skills", "test.csv", ttl_hours=3)

        cached_data = _file_cache[file_hash]
        expected_expiry = now + timedelta(hours=3)
        assert cached_data["expires_at"] == expected_expiry


@pytest.mark.unit
def test_store_temp_file_default_ttl():
    """Test default TTL of 1 hour."""
    content = b"test"

    with patch('app.utils.file_cache.datetime') as mock_datetime:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = now

        file_hash = store_temp_file(content, "skills", "test.csv")  # No TTL specified

        cached_data = _file_cache[file_hash]
        expected_expiry = now + timedelta(hours=1)
        assert cached_data["expires_at"] == expected_expiry


@pytest.mark.unit
def test_retrieve_temp_file_success():
    """Test successful file retrieval."""
    content = b"ID,NAME\n1,Python"
    file_hash = store_temp_file(content, "skills", "skills.csv", ttl_hours=1)

    result = retrieve_temp_file(file_hash)

    assert result is not None
    assert result["content"] == content
    assert result["file_type"] == "skills"
    assert result["filename"] == "skills.csv"
    assert "file_size_mb" in result
    # expires_at should NOT be in result (internal detail)
    assert "expires_at" not in result


@pytest.mark.unit
def test_retrieve_temp_file_not_found():
    """Test retrieval of non-existent file."""
    result = retrieve_temp_file("nonexistent_hash_12345")

    assert result is None


@pytest.mark.unit
def test_retrieve_temp_file_expired():
    """Test that expired files are not retrieved."""
    content = b"test"

    with patch('app.utils.file_cache.datetime') as mock_datetime:
        # Store file at time T
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = now
        file_hash = store_temp_file(content, "skills", "test.csv", ttl_hours=1)

        # Try to retrieve at time T+2 (after expiry)
        later = now + timedelta(hours=2)
        mock_datetime.utcnow.return_value = later
        result = retrieve_temp_file(file_hash)

        assert result is None
        # Expired file should be removed from cache
        assert file_hash not in _file_cache


@pytest.mark.unit
def test_retrieve_temp_file_not_expired():
    """Test that non-expired files are retrieved successfully."""
    content = b"test"

    with patch('app.utils.file_cache.datetime') as mock_datetime:
        # Store file at time T
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = now
        file_hash = store_temp_file(content, "skills", "test.csv", ttl_hours=1)

        # Try to retrieve at time T+0.5 (before expiry)
        later = now + timedelta(minutes=30)
        mock_datetime.utcnow.return_value = later
        result = retrieve_temp_file(file_hash)

        assert result is not None
        assert result["content"] == content


@pytest.mark.unit
def test_delete_temp_file_success():
    """Test successful file deletion."""
    content = b"test"
    file_hash = store_temp_file(content, "skills", "test.csv", ttl_hours=1)

    # Verify file exists
    assert file_hash in _file_cache

    # Delete file
    result = delete_temp_file(file_hash)

    assert result is True
    assert file_hash not in _file_cache


@pytest.mark.unit
def test_delete_temp_file_not_found():
    """Test deletion of non-existent file."""
    result = delete_temp_file("nonexistent_hash_12345")

    assert result is False


@pytest.mark.unit
def test_cleanup_expired_files_none_expired():
    """Test cleanup when no files are expired."""
    # Use unique content to generate different hashes
    content1 = b"test_file_1"
    content2 = b"test_file_2"
    content3 = b"test_file_3"

    with patch('app.utils.file_cache.datetime') as mock_datetime:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = now

        # Store 3 files with unique content
        hash1 = store_temp_file(content1, "skills", "file1.csv", ttl_hours=1)
        hash2 = store_temp_file(content2, "skills", "file2.csv", ttl_hours=1)
        hash3 = store_temp_file(content3, "jobs", "file3.csv", ttl_hours=1)

        # Run cleanup immediately (no files expired)
        cleaned = cleanup_expired_files()

        assert cleaned == 0
        assert len(_file_cache) == 3
        assert hash1 in _file_cache
        assert hash2 in _file_cache
        assert hash3 in _file_cache


@pytest.mark.unit
def test_cleanup_expired_files_some_expired():
    """Test cleanup when some files are expired."""
    # Use unique content to generate different hashes
    content1 = b"test_file_1"
    content2 = b"test_file_2"
    content3 = b"test_file_3"

    with patch('app.utils.file_cache.datetime') as mock_datetime:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = now

        # Store 3 files with different TTLs and unique content
        hash1 = store_temp_file(content1, "skills", "file1.csv", ttl_hours=1)
        hash2 = store_temp_file(content2, "skills", "file2.csv", ttl_hours=2)
        hash3 = store_temp_file(content3, "jobs", "file3.csv", ttl_hours=3)

        # Run cleanup at T+1.5 (hash1 expired, hash2 and hash3 not expired)
        later = now + timedelta(hours=1, minutes=30)
        mock_datetime.utcnow.return_value = later
        cleaned = cleanup_expired_files()

        assert cleaned == 1
        assert len(_file_cache) == 2
        assert hash1 not in _file_cache
        assert hash2 in _file_cache
        assert hash3 in _file_cache


@pytest.mark.unit
def test_cleanup_expired_files_all_expired():
    """Test cleanup when all files are expired."""
    # Use unique content to generate different hashes
    content1 = b"test_file_1"
    content2 = b"test_file_2"
    content3 = b"test_file_3"

    with patch('app.utils.file_cache.datetime') as mock_datetime:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = now

        # Store 3 files with unique content
        hash1 = store_temp_file(content1, "skills", "file1.csv", ttl_hours=1)
        hash2 = store_temp_file(content2, "skills", "file2.csv", ttl_hours=1)
        hash3 = store_temp_file(content3, "jobs", "file3.csv", ttl_hours=1)

        # Run cleanup at T+2 (all expired)
        later = now + timedelta(hours=2)
        mock_datetime.utcnow.return_value = later
        cleaned = cleanup_expired_files()

        assert cleaned == 3
        assert len(_file_cache) == 0


@pytest.mark.unit
def test_get_cache_stats_empty():
    """Test cache stats when cache is empty."""
    stats = get_cache_stats()

    assert stats["total_files"] == 0
    assert stats["total_size_mb"] == 0.0
    assert stats["oldest_expires_at"] is None
    assert stats["newest_expires_at"] is None


@pytest.mark.unit
def test_get_cache_stats_with_files():
    """Test cache stats with multiple files."""
    with patch('app.utils.file_cache.datetime') as mock_datetime:
        now = datetime(2025, 1, 1, 12, 0, 0)
        mock_datetime.utcnow.return_value = now

        # Store 3 files with different sizes and TTLs
        content1 = b"a" * 1024 * 1024  # 1 MB
        content2 = b"b" * 2 * 1024 * 1024  # 2 MB
        content3 = b"c" * 512 * 1024  # 0.5 MB

        store_temp_file(content1, "skills", "file1.csv", ttl_hours=1)
        store_temp_file(content2, "skills", "file2.csv", ttl_hours=2)
        store_temp_file(content3, "jobs", "file3.csv", ttl_hours=3)

        stats = get_cache_stats()

        assert stats["total_files"] == 3
        assert stats["total_size_mb"] == 3.5
        assert stats["oldest_expires_at"] == now + timedelta(hours=1)
        assert stats["newest_expires_at"] == now + timedelta(hours=3)


@pytest.mark.unit
def test_store_temp_file_sha256_deterministic():
    """Test that same content produces same hash."""
    content = b"ID,NAME\n1,Python\n2,Java"

    hash1 = store_temp_file(content, "skills", "file1.csv", ttl_hours=1)

    # Clear cache and store again
    _file_cache.clear()

    hash2 = store_temp_file(content, "skills", "file2.csv", ttl_hours=1)

    # Same content should produce same hash
    assert hash1 == hash2


@pytest.mark.unit
def test_store_temp_file_different_content():
    """Test that different content produces different hashes."""
    content1 = b"ID,NAME\n1,Python"
    content2 = b"ID,NAME\n1,Java"

    hash1 = store_temp_file(content1, "skills", "file1.csv", ttl_hours=1)
    hash2 = store_temp_file(content2, "skills", "file2.csv", ttl_hours=1)

    # Different content should produce different hashes
    assert hash1 != hash2
    assert len(_file_cache) == 2


@pytest.mark.unit
def test_file_size_calculation():
    """Test that file size is calculated correctly."""
    content = b"a" * 1024 * 1024  # Exactly 1 MB

    file_hash = store_temp_file(content, "skills", "test.csv", ttl_hours=1)

    cached_data = _file_cache[file_hash]
    assert cached_data["file_size_mb"] == 1.0
